"""Deal CRUD, deliverables, and attach-a-post-by-URL.

Attaching is deliberately manual: the creator pastes the link. Auto-matching
is a week of fiddly work and a support burden when it's wrong.
"""
from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .auth import login_required
from .db import db
from .integrations.youtube import video_id_from_url
from .models import Account, Deal, Deliverable, Post, track

bp = Blueprint("deals", __name__, url_prefix="/deals")


def _own_deal(deal_id: int) -> Deal:
    deal = db.session.get(Deal, deal_id)
    if deal is None or deal.user_id != g.user.id:
        abort(404)
    return deal


def _date(v: str | None) -> date | None:
    return date.fromisoformat(v) if v else None


def _cents(v: str | None) -> int:
    v = (v or "0").replace(",", "").strip()
    return int(round(float(v) * 100)) if v else 0


@bp.get("/")
@login_required
def index():
    deals = db.session.scalars(
        db.select(Deal).where(Deal.user_id == g.user.id).order_by(Deal.created_at.desc())
    ).all()
    return render_template("deals/index.html", deals=deals)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        f = request.form
        deal = Deal(
            user_id=g.user.id,
            brand_name=f["brand_name"].strip(),
            fee_cents=_cents(f.get("fee")),
            currency=(f.get("currency") or "USD").upper()[:3],
            start_date=_date(f.get("start_date")),
            end_date=_date(f.get("end_date")),
            usage_terms=f.get("usage_terms") or None,
            notes=f.get("notes") or None,
        )
        for line in (f.get("deliverables") or "").splitlines():
            if line.strip():
                deal.deliverables.append(Deliverable(description=line.strip()[:255]))
        db.session.add(deal)
        db.session.flush()
        track("deal_logged", g.user.id, deal_id=deal.id, fee_cents=deal.fee_cents, currency=deal.currency)
        db.session.commit()
        return redirect(url_for("deals.show", deal_id=deal.id))
    return render_template("deals/form.html", deal=None)


@bp.get("/<int:deal_id>")
@login_required
def show(deal_id: int):
    deal = _own_deal(deal_id)
    return render_template("deals/show.html", deal=deal)


@bp.route("/<int:deal_id>/edit", methods=["GET", "POST"])
@login_required
def edit(deal_id: int):
    deal = _own_deal(deal_id)
    if request.method == "POST":
        f = request.form
        deal.brand_name = f["brand_name"].strip()
        deal.fee_cents = _cents(f.get("fee"))
        deal.currency = (f.get("currency") or "USD").upper()[:3]
        deal.status = f.get("status") or deal.status
        deal.start_date = _date(f.get("start_date"))
        deal.end_date = _date(f.get("end_date"))
        deal.usage_terms = f.get("usage_terms") or None
        deal.notes = f.get("notes") or None
        db.session.commit()
        return redirect(url_for("deals.show", deal_id=deal.id))
    return render_template("deals/form.html", deal=deal)


@bp.post("/<int:deal_id>/delete")
@login_required
def delete(deal_id: int):
    deal = _own_deal(deal_id)
    db.session.delete(deal)
    db.session.commit()
    flash("Deal deleted.", "success")
    return redirect(url_for("deals.index"))


@bp.post("/<int:deal_id>/deliverables")
@login_required
def add_deliverable(deal_id: int):
    deal = _own_deal(deal_id)
    desc = (request.form.get("description") or "").strip()
    if desc:
        deal.deliverables.append(Deliverable(description=desc[:255], due_date=_date(request.form.get("due_date"))))
        db.session.commit()
    return redirect(url_for("deals.show", deal_id=deal.id))


@bp.post("/<int:deal_id>/deliverables/<int:d_id>/attach")
@login_required
def attach(deal_id: int, d_id: int):
    deal = _own_deal(deal_id)
    d = db.session.get(Deliverable, d_id)
    if d is None or d.deal_id != deal.id:
        abort(404)
    url = (request.form.get("url") or "").strip()
    post = resolve_post_url(g.user.id, url)
    if post is None:
        flash("Couldn't match that link to a post on your connected accounts. "
              "Is the account connected, and has it synced since you published?", "error")
    else:
        d.post_id = post.id
        d.status = "delivered"
        track("deliverable_attached", g.user.id, deal_id=deal.id, post_id=post.id)
        db.session.commit()
        flash(f"Attached: {post.title or post.permalink}", "success")
    return redirect(url_for("deals.show", deal_id=deal.id))


@bp.post("/<int:deal_id>/deliverables/<int:d_id>/detach")
@login_required
def detach(deal_id: int, d_id: int):
    deal = _own_deal(deal_id)
    d = db.session.get(Deliverable, d_id)
    if d is None or d.deal_id != deal.id:
        abort(404)
    d.post_id = None
    d.status = "pending"
    db.session.commit()
    return redirect(url_for("deals.show", deal_id=deal.id))


def resolve_post_url(user_id: int, url: str) -> Post | None:
    """Turn a pasted link into one of this user's ingested posts."""
    account_ids = db.select(Account.id).where(Account.user_id == user_id)
    yt = video_id_from_url(url)
    if yt:
        return db.session.scalar(
            db.select(Post).where(Post.platform_post_id == yt, Post.account_id.in_(account_ids))
        )
    # Instagram resolver lands in week 4; until then, exact permalink match.
    return db.session.scalar(
        db.select(Post).where(Post.permalink == url.rstrip("/"), Post.account_id.in_(account_ids))
    )
