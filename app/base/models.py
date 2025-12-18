# app/db/models.py

from sqlalchemy import BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.base.database import Base


class Video(Base):
    __tablename__ = "videos"

    video_created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )

    views_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    likes_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reports_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comments_count: Mapped[int] = mapped_column(BigInteger, nullable=False)

    creator_id: Mapped[str] = mapped_column(String(64), nullable=False)


class VideoSnapshot(Base):
    __tablename__ = "video_snapshots"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.id"),
        nullable=False,
    )

    views_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    likes_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reports_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    comments_count: Mapped[int] = mapped_column(BigInteger, nullable=False)

    delta_views_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delta_likes_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delta_reports_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    delta_comments_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
