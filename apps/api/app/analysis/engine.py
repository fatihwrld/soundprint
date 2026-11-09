"""Audio analysis: Essentia when available, librosa heuristic fallback.

IMPORTANT: values are computed from real 30s previews. The mappings to
Spotify's 0-1 scales (esp. valence, danceability) are heuristics for M0 and
need calibration against the AcousticBrainz dataset in M1.
"""

import json
import logging
import tempfile
from pathlib import Path

import httpx
import numpy as np

logger = logging.getLogger(__name__)

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _grid_support(oenv: "np.ndarray", fps: float, tempo_bpm: float) -> float:
    """Best mean onset strength over a beat grid at the given tempo.

    A beat grid 'exists' if nearly every beat lands on an onset. We scan
    phase offsets and take the best mean, which measures how consistently
    onsets fall on the grid.
    """
    period = 60.0 * fps / max(tempo_bpm, 1e-6)
    best = 0.0
    for phase in np.linspace(0.0, period, max(2, int(period)), endpoint=False):
        idx = np.arange(phase, len(oenv) - 1, period).astype(int)
        if len(idx) >= 4:
            best = max(best, float(np.mean(oenv[idx])))
    return best


def _resolve_octave(oenv: "np.ndarray", fps: float, tempo: float) -> float:
    """If a double-tempo grid is comparably supported, the estimate was half-time."""
    if 2.0 * tempo <= 180.0:
        s_base = _grid_support(oenv, fps, tempo)
        s_double = _grid_support(oenv, fps, tempo * 2.0)
        if s_base > 0 and s_double >= 0.8 * s_base:
            tempo *= 2.0
    # Keep the final value inside the plausible band
    while tempo < 70.0:
        tempo *= 2.0
    while tempo > 180.0:
        tempo /= 2.0
    return tempo


def _try_essentia(path: str) -> dict | None:
    try:
        import essentia.standard as es  # type: ignore
    except ImportError:
        return None

    audio = es.MonoLoader(filename=path, sampleRate=16000)()
    extractor = es.Extractor(
        computeLowLevelDescriptors=False,
        computeRhythmDescriptors=True,
        computeTonalityDescriptors=True,
        computeChromaDescriptors=False,
    )
    results = extractor(audio)
    # Mapping from full Extractor output is an M1 task; return raw for now.
    return {"engine": "essentia", "raw": results}


_FFMPEG: str | None = None


def _find_ffmpeg() -> str:
    """Locate ffmpeg: PATH first, then known install locations (WinGet portable etc.)."""
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    import os
    import shutil

    found = shutil.which("ffmpeg")
    if not found:
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ]
        found = next((c for c in candidates if c and os.path.isfile(c)), None)
    if not found:
        raise RuntimeError("ffmpeg not found (install via winget or Docker image)")
    _FFMPEG = found
    return found


def _decode_to_wav(path: Path) -> Path:
    """Convert any preview container (aac/m4a/mp3) to 22.05kHz mono WAV via ffmpeg."""
    import subprocess

    wav_path = path.with_suffix(".wav")
    subprocess.run(
        [
            _find_ffmpeg(), "-y", "-loglevel", "error", "-i", str(path),
            "-ac", "1", "-ar", "22050", str(wav_path),
        ],
        check=True,
        capture_output=True,
    )
    return wav_path


def raw_descriptors(path: str) -> dict:
    """Compute raw (uncalibrated) signal descriptors via librosa.

    These are the single source of truth that calibration curves map from.
    """
    import librosa
    import numpy as np
    import scipy.stats as stats

    y, sr = librosa.load(str(wav_path := _decode_to_wav(Path(path))), mono=True, duration=30)
    wav_path.unlink(missing_ok=True)

    oenv = librosa.onset.onset_strength(y=y, sr=sr)
    tempo_fn = getattr(librosa.feature, "tempo", None) or getattr(librosa.beat, "tempo")
    prior = stats.lognorm(s=float(np.log(2.0)), loc=0.0, scale=120.0)
    tempo_candidates = tempo_fn(onset_envelope=oenv, sr=sr, prior=prior)
    tempo = float(np.atleast_1d(tempo_candidates)[0])
    fps = sr / 512.0  # onset_strength default hop_length
    tempo = _resolve_octave(oenv, fps, tempo)

    rms = librosa.feature.rms(y=y)[0]
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    zero_rate = librosa.feature.zero_crossing_rate(y=y)[0]
    flatness = librosa.feature.spectral_flatness(y=y)[0]
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_idx = int(np.argmax(chroma.mean(axis=1)))

    return {
        "tempo": tempo,
        "key": key_idx,
        "loudness": float(20 * np.log10(max(np.mean(np.abs(y)), 1e-8))),
        "rms": float(np.mean(rms)),
        "centroid": float(np.mean(centroid)),
        "zcr": float(np.mean(zero_rate)),
        "flatness": float(np.mean(flatness)),
        "duration": float(len(y) / sr),
    }


def load_calibration() -> dict | None:
    """Load fitted calibration curves if present."""
    calibration_file = Path(__file__).with_name("calibration.json")
    if calibration_file.exists():
        with open(calibration_file, encoding="utf-8") as f:
            return json.load(f)
    return None


async def download_preview(url: str) -> Path:
    """Download a preview to a temp file and return its path (deleted by caller)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        # Apple previews end in .aac.p.m4a; content-type is unreliable here
        is_m4a = ".m4a" in url.split("?")[0].lower()
        suffix = ".m4a" if is_m4a else ".mp3"
        fd = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        fd.write(resp.content)
        fd.close()
        return Path(fd.name)


# Raw scalar proxies: which descriptor drives each bounded feature.
def _raw_scalar(feature: str, raw: dict) -> float:
    import numpy as np

    rms_n = float(np.clip(raw["rms"] / 0.3, 0, 1))
    acoustic_raw = float(np.clip(1.0 - raw["centroid"] / 3000.0, 0, 1))
    dance_raw = 0.5 * (raw["tempo"] / 180.0) + 0.3 * rms_n + 0.2 * acoustic_raw
    dance_sq = float(1.0 / (1.0 + np.exp(-(dance_raw - 0.6) * 6.0)))

    proxies = {
        "energy": rms_n,
        "danceability": dance_sq,
        "speechiness": float(np.clip(raw["zcr"] * 2.5, 0, 1)),
        "acousticness": acoustic_raw,
        "instrumentalness": float(np.clip(1.0 - raw["zcr"] * 4, 0, 1)),
        "liveness": float(np.clip(raw["flatness"] * 3, 0, 1)),
        "valence": float(np.clip(0.5 * dance_sq + 0.2 * acoustic_raw, 0, 1)),
    }
    return proxies[feature]


BOUNDED_FEATURES = [
    "danceability", "energy", "speechiness", "acousticness",
    "instrumentalness", "liveness", "valence",
]


def map_features(raw: dict, calibration: dict | None) -> dict:
    """Map raw descriptors → Spotify-schema features.

    With calibration: per-feature monotonic curves fitted on the Spotify
    tracks dataset. Without: documented heuristics.
    """
    import numpy as np

    out: dict = {}
    if calibration:
        for feature in BOUNDED_FEATURES:
            curve = calibration["isotonic"].get(feature)
            x = _raw_scalar(feature, raw)
            if curve:
                out[feature] = float(np.interp(x, curve["x"], curve["y"]))
            else:
                out[feature] = x
        out["tempo"] = round(raw["tempo"] * calibration["tempo_scale"], 2)
        a, b = calibration["loudness"]["a"], calibration["loudness"]["b"]
        out["loudness"] = round(a * raw["loudness"] + b, 2)
    else:
        for feature in BOUNDED_FEATURES:
            out[feature] = round(_raw_scalar(feature, raw), 2)
        out["tempo"] = round(raw["tempo"], 2)
        out["loudness"] = round(raw["loudness"], 2)

    out["key"] = raw["key"]
    out["mode"] = 1
    out["time_signature"] = 4
    out["duration_ms"] = int(raw["duration"] * 1000)
    out["analyzer"] = "librosa" + ("-calibrated" if calibration else "-heuristic")
    return out


def analyze_preview(path: Path) -> dict:
    result = _try_essentia(str(path))
    if result is None:
        raw = raw_descriptors(str(path))
        result = map_features(raw, load_calibration())
    result["analyzer"] = result.pop("engine", result.get("analyzer", "unknown"))
    return result


if __name__ == "__main__":
    # CLI spike: python -m app.analysis.engine <preview_url>
    import asyncio
    import sys

    async def main() -> None:
        url = sys.argv[1]
        preview = await download_preview(url)
        try:
            features = analyze_preview(preview)
            print(json.dumps(features, indent=2))
        finally:
            preview.unlink(missing_ok=True)

    asyncio.run(main())
