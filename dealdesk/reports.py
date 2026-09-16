"""Baseline and report generation.

The baseline is the one number the entire report rests on:

    median of this creator's last N organic posts, same account, same format,
    published before the sponsored post.

No models. Make it correct and defensible; a brand's media buyer will ask.
"""
from datetime import datetime
from statistics import median

from flask import Blueprint, abort, current_app, g, redirect, render_template, url_for

from .auth import login_required
from .db import db
from .models import Deal, Deliverable, Post, PostMetric, Report, track, utcnow

bp = Blueprint("reports", __name__)


# --------------------------------------------------------------------------- baseline


def baseline(account_id: int, fmt: str, as_of: datetime, window: int | None = None) -> dict:
    """Returns {"views": median, "engagements": median, "n": int, "window": int}.
    Organic = not attached to any deliverable. Values are None when n == 0."""
    window = window or current_app.config["BASELINE_WINDOW"]
    sponsored = db.select(Deliverable.post_id).where(Deliverable.post_id.is_not(None))
    posts = db.session.scalars(
        db.select(Post)
        .where(
            Post.account_id == account_id,
            Post.format == fmt,
            Post.published_at < as_of,
            Post.id.not_in(sponsored),
        )
        .order_by(Post.published_at.desc())
        .limit(window)
    ).all()

    views = [p.latest_metrics.views for p in posts if p.latest_metrics and p.latest_metrics.views is not None]
    eng = [p.latest_metrics.engagements for p in posts if p.latest_metrics]
    return {
        "views": median(views) if views else None,
        "engagements": median(eng) if eng else None,
        "n": len(posts),
        "window": window,
    }


def _lift(actual, base) -> float | None:
    if actual is None or not base:
        return None
    return round((actual - base) / base * 100, 1)


# --------------------------------------------------------------------------- snapshot


def build_snapshot(deal: Deal) -> dict:
    """Everything the report page renders, frozen. The page never queries
    live tables."""
    posts_out = []
    total_views = 0
    total_eng = 0
    for d in deal.deliverables:
        p = d.post
        if p is None:
            posts_out.append({"deliverable": d.description, "status": "pending", "post": None})
            continue
        m: PostMetric | None = p.latest_metrics
        b = baseline(p.account_id, p.format, p.published_at)
        views = m.views if m else None
        eng = m.engagements if m else 0
        total_views += views or 0
        total_eng += eng
        posts_out.append(
            {
                "deliverable": d.description,
                "status": "delivered",
                "post": {
                    "platform": p.platform,
                    "format": p.format,
                    "title": p.title,
                    "permalink": p.permalink,
                    "thumbnail_url": p.thumbnail_url,
                    "published_at": p.published_at.isoformat(),
                    "views": views,
                    "likes": m.likes if m else None,
                    "comments": m.comments if m else None,
                    "shares": m.shares if m else None,
                    "saves": m.saves if m else None,
                    "engagements": eng,
                    "engagement_rate": round(eng / views * 100, 2) if views else None,
                    "metrics_as_of": m.captured_at.isoformat() if m else None,
                },
                "baseline": b,
                "lift": {
                    "views_pct": _lift(views, b["views"]),
                    "engagements_pct": _lift(eng, b["engagements"]),
                },
            }
        )

    delivered = sum(1 for x in posts_out if x["status"] == "delivered")
    cpm = round(deal.fee / total_views * 1000, 2) if total_views else None
    creator = deal.user
    accounts = [
        {
            "platform": a.platform,
            "handle": a.handle or a.display_name,
            "display_name": a.display_name,
            "avatar_url": a.avatar_url,
            "follower_count": a.follower_count,
        }
        for a in creator.accounts
    ]
    return {
        "version": 1,
        "generated_at": utcnow().isoformat(),
        "creator": {"name": creator.name, "accounts": accounts},
        "deal": {
            "brand_name": deal.brand_name,
            "fee": deal.fee,
            "currency": deal.currency,
            "start_date": deal.start_date.isoformat() if deal.start_date else None,
            "end_date": deal.end_date.isoformat() if deal.end_date else None,
            "usage_terms": deal.usage_terms,
        },
        "summary": {
            "deliverables_total": len(posts_out),
            "deliverables_delivered": delivered,
            "total_views": total_views,
            "total_engagements": total_eng,
            "cpm": cpm,
            "cost_per_engagement": round(deal.fee / total_eng, 2) if total_eng else None,
        },
        "deliverables": posts_out,
        "methodology": (
            "Baseline is the median of the creator's most recent organic posts of the same "
            "format on the same platform (up to {w}), published before the sponsored post. "
            "Organic means not attached to any brand deal in Deal Desk. Metrics are read "
            "from the platform's official API and frozen at report generation."
        ).format(w=current_app.config["BASELINE_WINDOW"]),
    }


# --------------------------------------------------------------------------- routes


@bp.post("/deals/<int:deal_id>/reports")
@login_required
def generate(deal_id: int):
    deal = db.session.get(Deal, deal_id)
    if deal is None or deal.user_id != g.user.id:
        abort(404)
    report = Report(deal_id=deal.id, snapshot_json=build_snapshot(deal))
    db.session.add(report)
    db.session.flush()
    track("report_generated", g.user.id, deal_id=deal.id, report_id=report.id)
    db.session.commit()
    return redirect(url_for("reports.share", token=report.share_token))


@bp.get("/r/<token>")
def share(token: str):
    """Public. This is what the brand opens."""
    report = db.session.scalar(db.select(Report).where(Report.share_token == token))
    if report is None:
        abort(404)
    is_owner = g.user is not None and report.deal.user_id == g.user.id
    if not is_owner:
        report.view_count += 1
        track("report_viewed", None, report_id=report.id)
        db.session.commit()
    return render_template("report.html", r=report.snapshot_json, report=report, is_owner=is_owner)


@bp.get("/r/<token>.pdf")
def share_pdf(token: str):
    report = db.session.scalar(db.select(Report).where(Report.share_token == token))
    if report is None:
        abort(404)
    try:
        from weasyprint import HTML  # heavy import; optional at runtime
    except Exception:  # noqa: BLE001
        abort(503, "PDF export is not available on this server.")
    html = render_template("report.html", r=report.snapshot_json, report=report, is_owner=False, pdf=True)
    pdf = HTML(string=html, base_url=url_for("main.index", _external=True)).write_pdf()
    return current_app.response_class(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{report.deal.brand_name}-report.pdf"'},
    )
