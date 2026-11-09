"""Response schemas — Spotify-compatible where applicable."""

from typing import Literal

from pydantic import BaseModel, Field


class AudioFeatures(BaseModel):
    """Field names mirror Spotify's /v1/audio-features for drop-in use.
    Values are computed from real audio, so thresholds may need recalibration."""

    id: str  # spotify id, isrc or internal id
    isrc: str | None = None
    danceability: float = Field(ge=0.0, le=1.0)
    energy: float = Field(ge=0.0, le=1.0)
    key: int = Field(ge=0, le=11)
    mode: Literal[0, 1]
    loudness: float  # dB, typically -60..0
    speechiness: float = Field(ge=0.0, le=1.0)
    acousticness: float = Field(ge=0.0, le=1.0)
    instrumentalness: float = Field(ge=0.0, le=1.0)
    liveness: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=0.0, le=1.0)
    tempo: float
    time_signature: int = Field(ge=3, le=7)
    duration_ms: int | None = None
    analyzer: str = "essentia"
    track_name: str | None = None
    artist: str | None = None


class DistributorResult(BaseModel):
    distributor: str
    category: Literal[
        "independent-aggregator", "major", "label-imprint", "unknown"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    label: str | None = None
    copyright_lines: list[str] = []


class LookupTrack(BaseModel):
    source: str
    source_id: str
    track_name: str
    artist: str
    album: str | None = None
    isrc: str | None = None
    preview_url: str | None = None
    artwork_url: str | None = None
