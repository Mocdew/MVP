"""Google sign-in. One identity provider, because the YouTube connection is
Google OAuth anyway."""
from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, g, redirect, session, url_for

from .db import db
from .models import User, track

oauth = OAuth()

GOOGLE_META = "https://accounts.google.com/.well-known/openid-configuration"

bp = Blueprint("auth", __name__, url_prefix="/auth")


def init_oauth(app):
    oauth.init_app(app)
    # Sign-in: identity only.
    oauth.register(
        name="google",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=GOOGLE_META,
        client_kwargs={"scope": "openid email profile"},
    )
    # YouTube connection: same provider, data scopes, offline access for refresh tokens.
    oauth.register(
        name="google_youtube",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        server_metadata_url=GOOGLE_META,
        client_kwargs={
            "scope": (
                "openid email "
                "https://www.googleapis.com/auth/youtube.readonly "
                "https://www.googleapis.com/auth/yt-analytics.readonly"
            ),
        },
        authorize_params={"access_type": "offline", "prompt": "consent"},
    )


def load_current_user():
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = db.session.get(User, uid)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login")
def login():
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@bp.route("/google/callback")
def google_callback():
    token = oauth.google.authorize_access_token()
    info = token.get("userinfo") or oauth.google.userinfo()
    email = info["email"].lower()

    user = db.session.scalar(db.select(User).where(User.email == email))
    if user is None:
        user = User(email=email, name=info.get("name"))
        db.session.add(user)
        db.session.flush()
        track("user_signed_up", user.id)
    db.session.commit()

    session["user_id"] = user.id
    return redirect(url_for("main.dashboard"))


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))
