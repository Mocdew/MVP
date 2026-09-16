"""The whole data model. Seven tables.

Design notes (see brand-deal-infrastructure.md and the build plan):
- post_metrics is a wide snapshot table, appended on every refresh. Not EAV.
- reports.snapshot_json freezes numbers at generation time. A report sent to a
  brand must never silently change afterwards.
- The deal is the primitive, not the post.
"""
import secrets
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    accounts: Mapped[list["Account"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    deals: Mapped[list["Deal"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Account(db.Model):
    """A connected platform account (one YouTube channel, one Instagram account)."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("platform", "platform_account_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)  # 'youtube' | 'instagram'
    platform_account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    follower_count: Mapped[int | None] = mapped_column(BigInteger)

    # Encrypted with crypto.encrypt; never read directly.
    access_token_enc: Mapped[str | None] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="accounts")
    posts: Mapped[list["Post"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Post(db.Model):
    """One piece of published content. Format is normalised across platforms."""

    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("account_id", "platform_post_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False, index=True)
    platform_post_id: Mapped[str] = mapped_column(String(128), nullable=False)
    permalink: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # 'video' | 'short' | 'reel' | 'image' | 'carousel' | 'story'
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    account: Mapped["Account"] = relationship(back_populates="posts")
    metrics: Mapped[list["PostMetric"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="PostMetric.captured_at"
    )
    deliverables: Mapped[list["Deliverable"]] = relationship(back_populates="post")

    @property
    def latest_metrics(self) -> "PostMetric | None":
        return self.metrics[-1] if self.metrics else None

    @property
    def platform(self) -> str:
        return self.account.platform


class PostMetric(db.Model):
    """A snapshot of a post's numbers at a point in time. Append-only."""

    __tablename__ = "post_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    views: Mapped[int | None] = mapped_column(BigInteger)
    reach: Mapped[int | None] = mapped_column(BigInteger)
    likes: Mapped[int | None] = mapped_column(BigInteger)
    comments: Mapped[int | None] = mapped_column(BigInteger)
    shares: Mapped[int | None] = mapped_column(BigInteger)
    saves: Mapped[int | None] = mapped_column(BigInteger)
    watch_time_sec: Mapped[int | None] = mapped_column(BigInteger)

    post: Mapped["Post"] = relationship(back_populates="metrics")

    @property
    def engagements(self) -> int:
        return sum(v or 0 for v in (self.likes, self.comments, self.shares, self.saves))


class Deal(db.Model):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fee_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # 'draft' | 'active' | 'delivered' | 'paid'
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    usage_terms: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship(back_populates="deals")
    deliverables: Mapped[list["Deliverable"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", order_by="Deliverable.id"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="deal", cascade="all, delete-orphan", order_by="Report.generated_at.desc()"
    )

    @property
    def fee(self) -> float:
        return self.fee_cents / 100

    @property
    def attached_posts(self) -> list["Post"]:
        return [d.post for d in self.deliverables if d.post is not None]


class Deliverable(db.Model):
    """Something the creator promised. Fulfilled by attaching a post."""

    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("posts.id"), index=True)
    # 'pending' | 'delivered'
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    deal: Mapped["Deal"] = relationship(back_populates="deliverables")
    post: Mapped["Post | None"] = relationship(back_populates="deliverables")


class Report(db.Model):
    """A frozen, shareable ROI report for one deal."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    share_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(24)
    )
    snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    deal: Mapped["Deal"] = relationship(back_populates="reports")


class Event(db.Model):
    """Product instrumentation. Three events matter: account_connected,
    deal_logged, report_shared. The last one is activation."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    properties: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


def track(name: str, user_id: int | None = None, **properties) -> None:
    db.session.add(Event(name=name, user_id=user_id, properties=properties or None))
