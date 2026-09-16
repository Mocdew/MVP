from flask import Blueprint, abort, current_app, g, jsonify, redirect, render_template, request, url_for

from .auth import login_required
from .db import db
from .integrations import youtube
from .models import Account, Deal, Post

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    if g.user:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.get("/dashboard")
@login_required
def dashboard():
    accounts = g.user.accounts
    deals = db.session.scalars(
        db.select(Deal).where(Deal.user_id == g.user.id).order_by(Deal.created_at.desc()).limit(5)
    ).all()
    recent_posts = db.session.scalars(
        db.select(Post)
        .join(Account)
        .where(Account.user_id == g.user.id)
        .order_by(Post.published_at.desc())
        .limit(10)
    ).all()
    return render_template("dashboard.html", accounts=accounts, deals=deals, recent_posts=recent_posts)


@bp.post("/accounts/<int:account_id>/sync")
@login_required
def sync_now(account_id: int):
    account = db.session.get(Account, account_id)
    if account is None or account.user_id != g.user.id:
        abort(404)
    _sync(account)
    return redirect(url_for("main.dashboard"))


@bp.post("/internal/refresh")
def internal_refresh():
    """Cron target. Refreshes every connected account. Protected by a shared
    secret in the Authorization header."""
    expected = current_app.config["INTERNAL_REFRESH_TOKEN"]
    if not expected or request.headers.get("Authorization") != f"Bearer {expected}":
        abort(401)
    results = []
    for account in db.session.scalars(db.select(Account)):
        ok, msg = _sync(account)
        results.append({"account_id": account.id, "platform": account.platform, "ok": ok, "detail": msg})
    return jsonify(results)


def _sync(account: Account) -> tuple[bool, str]:
    try:
        if account.platform == "youtube":
            n = youtube.sync_account(account)
            return True, f"{n} posts"
        return False, f"no sync for platform {account.platform}"
    except Exception as exc:  # noqa: BLE001 — one bad account must not stop the batch
        current_app.logger.exception("sync failed for account %s", account.id)
        return False, str(exc)[:300]
