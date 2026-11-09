from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.analysis import engine
from app import db
from app.api_guard import ApiGuardMiddleware
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


app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ApiGuardMiddleware)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": "0.3.0",
        "spotify_catalog": spotify_catalog.configured(),
        "database": settings.database_url.split("://")[0],
        "api_keys_enabled": bool(settings.api_keys),
        "rate_limit_per_minute": settings.rate_limit_per_minute,
    }


async def _features_one(raw_id: str) -> AudioFeatures:
    """Resolve → (cache?) → download → DSP → cache. Raises HTTPException on failure."""
    cached = db.get_features(raw_id)
    if cached:
        fields = {k: v for k, v in cached.items() if k in AudioFeatures.model_fields}
        return AudioFeatures(**fields, id=raw_id)
    resolved = await resolver_svc.resolve(raw_id)
    if not resolved or not resolved.get("preview_url"):
        raise HTTPException(404, f"Could not resolve a preview for '{raw_id}'")

    if resolved.get("isrc"):
        by_isrc = db.get_by_isrc(resolved["isrc"])
        if by_isrc:
            db.put_features(
                id=raw_id, isrc=resolved["isrc"], spotify_id=resolved.get("spotify_id"),
                track_name=resolved["track_name"], artist=resolved["artist"],
                analyzer=by_isrc["analyzer"], features=by_isrc,
            )
            return AudioFeatures(**by_isrc, id=raw_id)

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
    return AudioFeatures(
        id=raw_id, isrc=resolved.get("isrc"),
        track_name=resolved.get("track_name"), artist=resolved.get("artist"),
        **features,
    )


@app.get("/v1/lookup", response_model=list[LookupTrack])
async def lookup(track: str, artist: str | None = None) -> list[LookupTrack]:
    """Search across preview sources (Spotify + iTunes + Deezer), merged + deduped."""
    itunes = await preview_svc.search_itunes(track, artist)
    try:
        deezer = await preview_svc.search_deezer(track, artist)
    except (httpx.HTTPError, KeyError):
        deezer = []
    try:
        spotify = await preview_svc.search_spotify(track, artist)
    except (httpx.HTTPError, KeyError):
        spotify = []

    results = spotify + itunes + deezer
    if not results:
        raise HTTPException(404, "No previews found")
    seen: set[tuple[str, str]] = set()
    deduped: list[LookupTrack] = []
    for r in results:
        key = (str(r.get("track_name") or "").lower(), str(r.get("artist") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(LookupTrack(**r))
    return deduped


@app.get("/v1/audio-features", response_model=list[AudioFeatures])
async def audio_features(ids: str = Query(..., description="comma-separated ids (Spotify ID, ISRC or name)")):
    """Spotify-compatible audio features, computed from real previews."""
    out: list[AudioFeatures] = []
    for raw_id in ids.split(","):
        raw_id = raw_id.strip()
        if raw_id:
            out.append(await _features_one(raw_id))
    return out


class BatchRequest(BaseModel):
    ids: list[str]


@app.post("/v1/audio-features/batch")
async def audio_features_batch(req: BatchRequest) -> dict[str, Any]:
    """Batch analysis: up to 100 ids; per-item failures don't break the batch."""
    if not req.ids:
        raise HTTPException(400, "ids must not be empty")
    if len(req.ids) > 100:
        raise HTTPException(400, "Maximum 100 ids per batch")

    results: list[AudioFeatures] = []
    errors: list[dict[str, str]] = []
    for raw_id in req.ids:
        raw_id = raw_id.strip()
        if not raw_id:
            continue
        try:
            results.append(await _features_one(raw_id))
        except HTTPException as e:
            errors.append({"id": raw_id, "error": e.detail})
        except Exception as e:
            errors.append({"id": raw_id, "error": str(e)})
    return {"results": results, "errors": errors, "count": len(results)}


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
