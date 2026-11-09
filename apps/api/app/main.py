from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import engine
from app import db
from app.config import get_settings
from app.schemas import AudioFeatures, DistributorResult, LookupTrack
from app.services import distributor as distributor_svc
from app.services import preview as preview_svc
from app.services import resolver as resolver_svc
from app.services import spotify_catalog

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.2.0",
        "spotify_catalog": spotify_catalog.configured(),
        "database": settings.database_url.split("://")[0],
    }


@app.get("/v1/lookup", response_model=list[LookupTrack])
async def lookup(track: str, artist: str | None = None) -> list[LookupTrack]:
    """Search across preview sources (iTunes + Deezer), merged."""
    itunes = await preview_svc.search_itunes(track, artist)
    try:
        deezer = await preview_svc.search_deezer(track, artist)
    except (httpx.HTTPError, KeyError):
        deezer = []
    results = itunes + deezer
    if not results:
        raise HTTPException(404, "No previews found")
    return [LookupTrack(**r) for r in results]


@app.get("/v1/audio-features", response_model=list[AudioFeatures])
async def audio_features(ids: str = Query(..., description="comma-separated ids (Spotify ID, ISRC or name)")):
    """Spotify-compatible audio features, computed from real previews."""
    out: list[AudioFeatures] = []
    for raw_id in ids.split(","):
        raw_id = raw_id.strip()
        if not raw_id:
            continue

        # 1) cache (by the identifier itself)
        cached = db.get_features(raw_id)
        if cached:
            fields = {k: v for k, v in cached.items() if k in AudioFeatures.model_fields}
            out.append(AudioFeatures(**fields, id=raw_id))
            continue

        # 2) resolve to metadata + preview (Spotify ID → ISRC → preview)
        resolved = await resolver_svc.resolve(raw_id)
        if not resolved or not resolved.get("preview_url"):
            raise HTTPException(404, f"Could not resolve a preview for '{raw_id}'")

        # 3) ISRC-level cache before spending DSP time
        if resolved.get("isrc"):
            by_isrc = db.get_by_isrc(resolved["isrc"])
            if by_isrc:
                db.put_features(
                    id=raw_id, isrc=resolved["isrc"], spotify_id=resolved.get("spotify_id"),
                    track_name=resolved["track_name"], artist=resolved["artist"],
                    analyzer=by_isrc["analyzer"], features=by_isrc,
                )
                out.append(AudioFeatures(**by_isrc, id=raw_id))
                continue

        path = await engine.download_preview(resolved["preview_url"])
        try:
            data = engine.analyze_preview(path)
        finally:
            path.unlink(missing_ok=True)

        features = {
            k: v for k, v in data.items()
            if k in AudioFeatures.model_fields and k != "id"
        }
        db.put_features(
            id=raw_id, isrc=resolved.get("isrc"), spotify_id=resolved.get("spotify_id"),
            track_name=resolved["track_name"], artist=resolved["artist"],
            analyzer=data["analyzer"], features=features,
        )
        out.append(AudioFeatures(id=raw_id, **features))
    return out


@app.get("/v1/distributor/{track_id}", response_model=DistributorResult)
async def distributor(track_id: str) -> DistributorResult:
    """Which distributor released this track? (label/copyright normalization)"""
    try:
        track = await spotify_catalog.get_track(track_id)
    except RuntimeError as e:
        raise HTTPException(501, str(e)) from e
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Spotify API error: {e}") from e

    album_id = (track.get("album") or {}).get("id")
    if not album_id:
        raise HTTPException(404, "Track has no album reference")
    album = await spotify_catalog.get_album(album_id)
    label, copyright_lines = spotify_catalog.extract_album_rights(album)
    return distributor_svc.classify(label, copyright_lines)
