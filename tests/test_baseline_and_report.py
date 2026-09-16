from datetime import datetime, timezone

from dealdesk.db import db
from dealdesk.models import Deal, Deliverable, Report
from dealdesk.reports import baseline, build_snapshot
from tests.conftest import make_post


def test_baseline_is_median_of_organic_same_format(app, user, channel):
    for i, v in enumerate([100, 200, 300, 400, 1000]):
        make_post(channel, f"vid{i:08d}", days_ago=30 - i, views=v)
    make_post(channel, "short000001", days_ago=10, views=99_999, fmt="short")  # other format, ignored

    b = baseline(channel.id, "video", datetime.now(timezone.utc))
    assert b["n"] == 5
    assert b["views"] == 300


def test_baseline_excludes_sponsored_and_future_posts(app, user, channel):
    posts = [make_post(channel, f"vid{i:08d}", days_ago=30 - i, views=v) for i, v in enumerate([100, 200, 300])]
    sponsored = make_post(channel, "sponsored01", days_ago=5, views=10_000)
    deal = Deal(user_id=user.id, brand_name="Acme", fee_cents=300_000)
    deal.deliverables.append(Deliverable(description="1x video", post=sponsored, status="delivered"))
    db.session.add(deal)
    db.session.commit()

    # as_of = the sponsored post's publish time: only the 3 earlier organic posts count
    b = baseline(channel.id, "video", sponsored.published_at)
    assert b["n"] == 3
    assert b["views"] == 200

    # a later organic post must not leak into an earlier post's baseline
    make_post(channel, "later000001", days_ago=1, views=50_000)
    assert baseline(channel.id, "video", sponsored.published_at)["n"] == 3


def test_baseline_empty(app, user, channel):
    b = baseline(channel.id, "video", datetime.now(timezone.utc))
    assert b == {"views": None, "engagements": None, "n": 0, "window": 20}


def test_snapshot_math(app, user, channel):
    for i, v in enumerate([1000, 1000, 1000]):
        make_post(channel, f"vid{i:08d}", days_ago=30 - i, views=v, likes=10)
    sponsored = make_post(channel, "sponsored01", days_ago=5, views=2000, likes=40, comments=10)
    deal = Deal(user_id=user.id, brand_name="Acme", fee_cents=100_000)  # $1,000
    deal.deliverables.append(Deliverable(description="1x video", post=sponsored, status="delivered"))
    deal.deliverables.append(Deliverable(description="1x short"))  # pending
    db.session.add(deal)
    db.session.commit()

    s = build_snapshot(deal)
    assert s["summary"]["deliverables_total"] == 2
    assert s["summary"]["deliverables_delivered"] == 1
    assert s["summary"]["total_views"] == 2000
    assert s["summary"]["total_engagements"] == 50
    assert s["summary"]["cpm"] == 500.0  # $1000 / 2000 views * 1000
    assert s["summary"]["cost_per_engagement"] == 20.0
    d = s["deliverables"][0]
    assert d["lift"]["views_pct"] == 100.0
    assert d["lift"]["engagements_pct"] == 400.0
    assert d["post"]["engagement_rate"] == 2.5
    assert s["deliverables"][1]["status"] == "pending"


def test_report_is_frozen_after_metrics_change(app, client, logged_in, channel):
    make_post(channel, "vid00000001", days_ago=20, views=1000)
    sponsored = make_post(channel, "sponsored01", days_ago=5, views=2000)
    deal = Deal(user_id=logged_in.id, brand_name="Acme", fee_cents=100_000)
    deal.deliverables.append(Deliverable(description="1x video", post=sponsored, status="delivered"))
    db.session.add(deal)
    db.session.commit()

    resp = client.post(f"/deals/{deal.id}/reports", follow_redirects=False)
    assert resp.status_code == 302
    report = db.session.scalar(db.select(Report))
    assert report.snapshot_json["summary"]["total_views"] == 2000

    # metrics move on; the report does not
    from dealdesk.models import PostMetric
    sponsored.metrics.append(PostMetric(views=9000))
    db.session.commit()
    page = client.get(f"/r/{report.share_token}")
    assert page.status_code == 200
    assert b"2,000" in page.data
    assert b"9,000" not in page.data


def test_public_report_and_ownership(app, client, logged_in, channel):
    sponsored = make_post(channel, "sponsored01", days_ago=5, views=2000)
    deal = Deal(user_id=logged_in.id, brand_name="Acme", fee_cents=100_000)
    deal.deliverables.append(Deliverable(description="1x video", post=sponsored, status="delivered"))
    db.session.add(deal)
    db.session.commit()
    client.post(f"/deals/{deal.id}/reports")
    report = db.session.scalar(db.select(Report))

    anon = app.test_client()
    assert anon.get(f"/r/{report.share_token}").status_code == 200
    assert anon.get("/r/doesnotexist").status_code == 404
    db.session.refresh(report)
    assert report.view_count == 1  # owner views don't count

    # another user cannot generate reports on my deal
    other = app.test_client()
    from dealdesk.models import User
    u2 = User(email="other@example.com"); db.session.add(u2); db.session.commit()
    with other.session_transaction() as s:
        s["user_id"] = u2.id
    assert other.post(f"/deals/{deal.id}/reports").status_code == 404
