"""Catalog storage. SQLAlchemy 2.0 — SQLite locally, Postgres via DATABASE_URL.

docker compose (Postgres) lands with Docker Desktop; DATABASE_URL switch is all it takes.
"""

import json
import datetime as dt

from sqlalchemy import String, Text, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class FeatureCache(Base):
    """Analyzed features, keyed by whichever identifier resolved first."""

    __tablename__ = "feature_cache"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # spotify_id or itunes/deezer id
    isrc: Mapped[str | None] = mapped_column(String(12), index=True, nullable=True)
    spotify_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    track_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    artist: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzer: Mapped[str | None] = mapped_column(String(32), nullable=True)
    features_json: Mapped[str] = mapped_column(Text)
    analyzed_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)


Base.metadata.create_all(engine)


def get_features(identifier: str) -> dict | None:
    with SessionLocal() as session:
        row = session.get(FeatureCache, identifier)
        if row is None:
            return None
        return {
            **json.loads(row.features_json),
            "isrc": row.isrc,
            "track_name": row.track_name,
            "artist": row.artist,
            "analyzer": row.analyzer,
            "analyzed_at": row.analyzed_at.isoformat(),
        }


def get_by_isrc(isrc: str) -> dict | None:
    with SessionLocal() as session:
        row = (
            session.query(FeatureCache)
            .filter(FeatureCache.isrc == isrc)
            .first()
        )
        if row is None:
            return None
        return json.loads(row.features_json)


def put_features(
    *,
    id: str,
    isrc: str | None,
    spotify_id: str | None,
    track_name: str | None,
    artist: str | None,
    analyzer: str,
    features: dict,
) -> None:
    with SessionLocal() as session:
        row = session.get(FeatureCache, id)
        if row is None:
            row = FeatureCache(id=id)
        row.isrc, row.spotify_id = isrc, spotify_id
        row.track_name, row.artist = track_name, artist
        row.analyzer = analyzer
        row.features_json = json.dumps(features)
        session.merge(row)
        session.commit()
