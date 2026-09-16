from dealdesk.db import db
from dealdesk.models import Deal, Event
from tests.conftest import make_post


def test_requires_login(client):
    assert client.get("/deals/").status_code == 302
    assert client.get("/dashboard").status_code == 302


def test_create_deal_with_deliverables_and_attach(client, logged_in, channel):
    make_post(channel, "dQw4w9WgXcQ", days_ago=3, views=5000)

    resp = client.post(
        "/deals/new",
        data={
            "brand_name": "Acme", "fee": "1,500.50", "currency": "usd",
            "start_date": "2026-09-01", "deliverables": "1x YouTube integration\n\n2x reels\n",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    deal = db.session.scalar(db.select(Deal))
    assert deal.fee_cents == 150_050
    assert deal.currency == "USD"
    assert [d.description for d in deal.deliverables] == ["1x YouTube integration", "2x reels"]
    assert db.session.scalar(db.select(Event).where(Event.name == "deal_logged")) is not None

    d = deal.deliverables[0]
    resp = client.post(
        f"/deals/{deal.id}/deliverables/{d.id}/attach",
        data={"url": "https://youtu.be/dQw4w9WgXcQ?si=x"},
        follow_redirects=True,
    )
    assert b"Attached" in resp.data
    db.session.refresh(d)
    assert d.status == "delivered"
    assert d.post.platform_post_id == "dQw4w9WgXcQ"

    # unknown link is a friendly failure, not a 500
    d2 = deal.deliverables[1]
    resp = client.post(f"/deals/{deal.id}/deliverables/{d2.id}/attach", data={"url": "https://youtu.be/AAAAAAAAAAA"}, follow_redirects=True)
    assert b"Couldn" in resp.data
    db.session.refresh(d2)
    assert d2.status == "pending"


def test_internal_refresh_requires_secret(app, client):
    app.config["INTERNAL_REFRESH_TOKEN"] = "s3cret"
    assert client.post("/internal/refresh").status_code == 401
    assert client.post("/internal/refresh", headers={"Authorization": "Bearer wrong"}).status_code == 401
    resp = client.post("/internal/refresh", headers={"Authorization": "Bearer s3cret"})
    assert resp.status_code == 200
    assert resp.get_json() == []
