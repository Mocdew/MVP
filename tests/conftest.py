from datetime import datetime, timedelta, timezone

import pytest

from dealdesk import create_app
from dealdesk.config import TestConfig
from dealdesk.db import db
from dealdesk.models import Account, Post, PostMetric, User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(email="creator@example.com", name="Test Creator")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def logged_in(client, user):
    with client.session_transaction() as s:
        s["user_id"] = user.id
    return user


@pytest.fixture
def channel(app, user):
    a = Account(
        user_id=user.id, platform="youtube", platform_account_id="UC123",
        display_name="Test Channel", handle="@test", follower_count=50_000,
    )
    db.session.add(a)
    db.session.commit()
    return a


def make_post(account, vid, days_ago, views, likes=0, comments=0, fmt="video"):
    p = Post(
        account_id=account.id, platform_post_id=vid,
        permalink=f"https://www.youtube.com/watch?v={vid}",
        published_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        format=fmt, title=f"Video {vid}",
    )
    p.metrics.append(PostMetric(views=views, likes=likes, comments=comments))
    db.session.add(p)
    db.session.commit()
    return p
