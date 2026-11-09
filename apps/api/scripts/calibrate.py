"""Fit calibration curves: our raw DSP descriptors → Spotify's audio features.

Data source: maharshipandya/spotify-tracks-dataset (114k tracks, BSD) —
real Spotify audio-features values collected before the API lockdown.

Pipeline:
1. Download dataset.csv (cached locally)
2. Sample rows, resolve each Spotify track_id → preview via our resolver
3. Compute raw descriptors with our analyzer
4. Fit per-feature monotonic (isotonic) curves + tempo scale + loudness affine
5. Save apps/api/app/analysis/calibration.json

Usage: .venv/Scripts/python scripts/calibrate.py [n_tracks]
"""

import asyncio
import csv
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

import httpx
from sklearn.isotonic import IsotonicRegression

from app.analysis import engine
from app.services import resolver

DATASET_URL = (
    "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset"
    "/resolve/main/dataset.csv"
)
DATASET_FILE = Path("scripts/dataset.csv")
CALIBRATION_FILE = Path("app/analysis/calibration.json")

BOUNDED = engine.BOUNDED_FEATURES


def download_dataset() -> None:
    if DATASET_FILE.exists():
        print(f"dataset cached: {DATASET_FILE}")
        return
    print(f"downloading dataset ({DATASET_URL}) ...")
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        with client.stream("GET", DATASET_URL) as resp:
            resp.raise_for_status()
            DATASET_FILE.parent.mkdir(exist_ok=True)
            with open(DATASET_FILE, "wb") as f:
                for chunk in resp.iter_bytes(1 << 20):
                    f.write(chunk)
    print(f"downloaded: {DATASET_FILE.stat().st_size / 1e6:.1f} MB")


def load_rows() -> list[dict]:
    with open(DATASET_FILE, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    random.Random(42).shuffle(rows)
    return rows


async def collect_pairs(n_target: int) -> list[dict]:
    rows = load_rows()
    pairs: list[dict] = []
    attempted = 0
    for row in rows:
        if len(pairs) >= n_target or attempted >= n_target * 3:
            break
        attempted += 1
        track_id = row["track_id"]
        try:
            resolved = await resolver.resolve(track_id)
            if not resolved or not resolved.get("preview_url"):
                continue
            path = await engine.download_preview(resolved["preview_url"])
            try:
                raw = engine.raw_descriptors(str(path))
            finally:
                path.unlink(missing_ok=True)
            target = {
                "danceability": float(row["danceability"]),
                "energy": float(row["energy"]),
                "speechiness": float(row["speechiness"]),
                "acousticness": float(row["acousticness"]),
                "instrumentalness": float(row["instrumentalness"]),
                "liveness": float(row["liveness"]),
                "valence": float(row["valence"]),
                "tempo": float(row["tempo"]),
                "loudness": float(row["loudness"]),
            }
            pairs.append({"raw": raw, "target": target})
            if len(pairs) % 20 == 0:
                print(f"  {len(pairs)}/{n_target} analyzed (attempted {attempted})")
        except Exception as e:  # noqa: BLE001
            print(f"  skip {track_id[:8]}: {type(e).__name__}: {e}")
        await asyncio.sleep(0.3)  # be polite to preview CDNs
    return pairs


def fit_isotonic(pairs: list[dict]) -> tuple[dict, dict]:
    curves: dict = {}
    report: dict = {}
    for feature in BOUNDED:
        xs = [engine._raw_scalar(feature, p["raw"]) for p in pairs]
        ys = [p["target"][feature] for p in pairs]
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(xs, ys)
        # Sample ~60 points for a compact JSON curve
        x_grid = [min(xs)] if len(xs) == 1 else [
            min(xs) + (max(xs) - min(xs)) * i / 59.0 for i in range(60)
        ]
        curves[feature] = {"x": [round(v, 6) for v in x_grid], "y": [round(float(v), 4) for v in iso.predict(x_grid)]}
        preds = list(iso.predict(xs))
        mae = sum(abs(pr - yr) for pr, yr in zip(preds, ys)) / len(ys)
        report[feature] = {"mae": round(mae, 4), "n": len(ys)}
    return curves, report


def fit_tempo(pairs: list[dict]) -> tuple[float, dict]:
    ratios = []
    for p in pairs:
        raw_t, target_t = p["raw"]["tempo"], p["target"]["tempo"]
        if raw_t <= 0 or target_t <= 0:
            continue
        best = min(
            (abs(raw_t * m - target_t) / max(target_t, 1e-6), raw_t * m)
            for m in (0.5, 1.0, 2.0)
        )
        ratios.append(best[1] / raw_t)
    scale = sorted(ratios)[len(ratios) // 2] if ratios else 1.0
    return round(scale, 4), {"median_ratio": scale, "n": len(ratios)}


def fit_loudness(pairs: list[dict]) -> tuple[dict, dict]:
    xs = [p["raw"]["loudness"] for p in pairs]
    ys = [p["target"]["loudness"] for p in pairs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx if sxx else 1.0
    b = my - a * mx
    preds = [a * x + b for x in xs]
    mae = sum(abs(p - y) for p, y in zip(preds, ys)) / n
    return {"a": round(a, 4), "b": round(b, 4)}, {"mae": round(mae, 4), "n": n}


async def main() -> None:
    n_target = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    download_dataset()
    print(f"collecting {n_target} analyzed tracks ...")
    t0 = time.time()
    pairs = await collect_pairs(n_target)
    print(f"collected {len(pairs)} pairs in {time.time() - t0:.0f}s")
    if len(pairs) < 30:
        print("Not enough data to fit; aborting")
        return

    curves, feature_report = fit_isotonic(pairs)
    tempo_scale, tempo_report = fit_tempo(pairs)
    loudness, loudness_report = fit_loudness(pairs)

    calibration = {
        "version": 1,
        "n_tracks": len(pairs),
        "dataset": "maharshipandya/spotify-tracks-dataset (BSD)",
        "isotonic": curves,
        "tempo_scale": tempo_scale,
        "loudness": loudness,
    }
    CALIBRATION_FILE.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    print(f"\nSaved {CALIBRATION_FILE}")
    print("\nIn-sample MAE per feature:")
    for feature, stats_ in feature_report.items():
        print(f"  {feature:>18}: {stats_['mae']:.4f} (n={stats_['n']})")
    print(f"  tempo_scale: {tempo_report}")
    print(f"  loudness: {loudness_report}")


if __name__ == "__main__":
    asyncio.run(main())
