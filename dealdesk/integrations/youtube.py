"""YouTube: OAuth connect, channel + video ingest, metrics snapshots.

Data API v3 gives views/likes/comments per video. Analytics API gives watch
time; it's best-effort here and never blocks a sync.
"""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import requests
from flask import Blueprint, current_app, flash, g, redirect, url_for

from ..auth import login_required, oauth
from ..crypto import decrypt, encrypt
from ..db import db
from ..models import Account, Post, PostMetric, track, utcnow

bp = Blueprint("youtube", __name__, url_prefix="/connect/youtube")

DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"

MAX_VIDEOS = 200  # recent uploads to backfill on connect
SHORT_MAX_SECONDS = 60


# --------------------------------------------------------------------------- OAuth


@bp.route("/")
@login_required
def connect():
    redirect_uri = url_for("youtube.callback", _external=True)
    return oauth.google_youtube.authorize_redirect(redirect_uri)


@bp.route("/callback")
@login_required
def callback():
    token = oauth.google_youtube.authorize_access_token()
    access = token["access_token"]
    channel = _get(access, f"{DATA_API}/channels", part="snippet,statistics,contentDetails", mine="true")
    items = channel.get("items") or []
    if not items:
        flash("No YouTube channel found on that Google account.", "error")
        return redirect(url_for("main.dashboard"))
    ch = items[0]

    account = db.session.scalar(
        db.select(Account).where(Account.platform == "youtube", Account.platform_account_id == ch["id"])
    )
    if account is None:
        account = Account(platform="youtube", platform_account_id=ch["id"], user_id=g.user.id)
        db.session.add(account)
    elif account.user_id != g.user.id:
        flash("That channel is already connected to a different Deal Desk account.", "error")
        return redirect(url_for("main.dashboard"))

    snip = ch["snippet"]
    account.handle = snip.get("customUrl")
    account.display_name = snip.get("title")
    account.avatar_url = (snip.get("thumbnails") or {}).get("default", {}).get("url")
    account.follower_count = int(ch.get("statistics", {}).get("subscriberCount") or 0)
    account.access_token_enc = encrypt(access)
    if token.get("refresh_token"):  # only returned on first consent
        account.refresh_token_enc = encrypt(token["refresh_token"])
    account.token_expires_at = utcnow() + timedelta(seconds=int(token.get("expires_in", 3600)))
    db.session.flush()
    track("account_connected", g.user.id, platform="youtube", account_id=account.id)
    db.session.commit()

    try:
        n = sync_account(account)
        flash(f"Connected {account.display_name}. Imported {n} videos.", "success")
    except Exception as exc:  # noqa: BLE001 — surface, don't crash onboarding
        current_app.logger.exception("initial youtube sync failed")
        flash(f"Connected, but the first import failed: {exc}", "error")
    return redirect(url_for("main.dashboard"))


# --------------------------------------------------------------------------- tokens


def _fresh_access_token(account: Account) -> str:
    if account.token_expires_at and account.token_expires_at > utcnow() + timedelta(minutes=2):
        return decrypt(account.access_token_enc)
    refresh = decrypt(account.refresh_token_enc)
    if not refresh:
        raise RuntimeError("No refresh token; the creator needs to reconnect YouTube.")
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": current_app.config["GOOGLE_CLIENT_ID"],
            "client_secret": current_app.config["GOOGLE_CLIENT_SECRET"],
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    account.access_token_enc = encrypt(data["access_token"])
    account.token_expires_at = utcnow() + timedelta(seconds=int(data.get("expires_in", 3600)))
    db.session.commit()
    return data["access_token"]


def _get(access_token: str, url: str, **params) -> dict:
    resp = requests.get(url, params=params, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


# --------------------------------------------------------------------------- ingest


def sync_account(account: Account) -> int:
    """Pull recent uploads and append a metrics snapshot for each. Returns
    the number of videos touched."""
    try:
        access = _fresh_access_token(account)
        video_ids = _list_upload_ids(access, account)
        n = 0
        for chunk in _chunks(video_ids, 50):
            data = _get(access, f"{DATA_API}/videos", part="snippet,statistics,contentDetails", id=",".join(chunk))
            for item in data.get("items", []):
                _upsert_video(account, item)
                n += 1
        db.session.flush()
        _attach_watch_time(access, account, video_ids)
        account.last_synced_at = utcnow()
        account.last_sync_error = None
        db.session.commit()
        return n
    except Exception as exc:
        db.session.rollback()
        account.last_sync_error = str(exc)[:1000]
        db.session.commit()
        raise


def _list_upload_ids(access: str, account: Account) -> list[str]:
    ch = _get(access, f"{DATA_API}/channels", part="contentDetails", id=account.platform_account_id)
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids: list[str] = []
    page = None
    while len(ids) < MAX_VIDEOS:
        params = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if page:
            params["pageToken"] = page
        data = _get(access, f"{DATA_API}/playlistItems", **params)
        ids.extend(i["contentDetails"]["videoId"] for i in data.get("items", []))
        page = data.get("nextPageToken")
        if not page:
            break
    return ids[:MAX_VIDEOS]


def _upsert_video(account: Account, item: dict) -> Post:
    vid = item["id"]
    snip = item["snippet"]
    stats = item.get("statistics", {})
    seconds = _parse_duration(item.get("contentDetails", {}).get("duration", ""))
    fmt = "short" if 0 < seconds <= SHORT_MAX_SECONDS else "video"

    post = db.session.scalar(db.select(Post).where(Post.account_id == account.id, Post.platform_post_id == vid))
    if post is None:
        post = Post(
            account_id=account.id,
            platform_post_id=vid,
            permalink=f"https://www.youtube.com/watch?v={vid}",
            published_at=datetime.fromisoformat(snip["publishedAt"].replace("Z", "+00:00")),
            format=fmt,
        )
        db.session.add(post)
    post.title = snip.get("title")
    post.caption = snip.get("description")
    post.thumbnail_url = (snip.get("thumbnails") or {}).get("medium", {}).get("url")
    post.format = fmt

    post.metrics.append(
        PostMetric(
            views=_int(stats.get("viewCount")),
            likes=_int(stats.get("likeCount")),
            comments=_int(stats.get("commentCount")),
        )
    )
    return post


def _attach_watch_time(access: str, account: Account, video_ids: list[str]) -> None:
    """Best-effort: fill watch_time_sec on the snapshots we just wrote."""
    if not video_ids:
        return
    try:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=365 * 3)
        data = _get(
            access,
            ANALYTICS_API,
            ids=f"channel=={account.platform_account_id}",
            startDate=start.isoformat(),
            endDate=end.isoformat(),
            metrics="estimatedMinutesWatched",
            dimensions="video",
            filters="video==" + ",".join(video_ids[:200]),
            maxResults=200,
        )
    except requests.HTTPError as exc:
        current_app.logger.warning("youtube analytics unavailable: %s", exc)
        return
    minutes_by_id = {row[0]: row[1] for row in data.get("rows", [])}
    if not minutes_by_id:
        return
    posts = db.session.scalars(
        db.select(Post).where(Post.account_id == account.id, Post.platform_post_id.in_(minutes_by_id))
    )
    for post in posts:
        if post.metrics:
            post.metrics[-1].watch_time_sec = int(minutes_by_id[post.platform_post_id] * 60)


# --------------------------------------------------------------------------- helpers

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def video_id_from_url(url: str) -> str | None:
    """youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID, /live/ID, /embed/ID."""
    url = url.strip()
    if _YT_ID.match(url):
        return url
    try:
        u = urlparse(url if "://" in url else "https://" + url)
    except ValueError:
        return None
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        cand = u.path.strip("/").split("/")[0]
    elif host in ("youtube.com", "music.youtube.com"):
        if u.path == "/watch":
            cand = (parse_qs(u.query).get("v") or [""])[0]
        else:
            parts = u.path.strip("/").split("/")
            cand = parts[1] if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v") else ""
    else:
        return None
    return cand if _YT_ID.match(cand) else None


_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_duration(iso: str) -> int:
    m = _DUR.fullmatch(iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _int(v) -> int | None:
    return int(v) if v is not None else None


def _chunks(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]
