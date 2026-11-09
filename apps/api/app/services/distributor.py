"""Distributor intelligence: normalize label/copyright text into a distributor.

Signals, in order of reliability:
1. Spotify album `label` + `copyrights[].text` (via spotify-scraper, public web data)
2. Apple Music `copyright` line (cross-check)
3. MusicBrainz label relations (fallback)

This module implements the normalization layer (signal 1 today).
"""

import re
from typing import NamedTuple

from app.schemas import DistributorResult

# Alias table: canonical name → regex fragments (lowercase, matched against
# label and copyright text). Extend freely; this is the heart of the feature.
DISTRIBUTORS: dict[str, list[str]] = {
    # --- Independent aggregators ---
    "DistroKid": ["distrokid", "© dk", "©dk"],
    "TuneCore": ["tunecore"],
    "CD Baby": ["cd baby", "cdbaby"],
    "Believe": ["believe music", "believe recordings", "believe distribution"],
    "ONErpm": ["onerpm"],
    "Amuse": ["amuse io", "amuse music"],
    "SoundOn (TikTok)": ["soundon", "tiktok music distribution"],
    "UnitedMasters": ["unitedmasters", "united masters"],
    "Vydia": ["vydia"],
    "Too Lost": ["too lost"],
    "Symphonic Distribution": ["symphonic"],
    "Ditto Music": ["ditto music"],
    "LANDR": ["landr"],
    "RouteNote": ["routenote"],
    "Stem": ["stem distribution"],
    "AWAL": ["awal"],
    "The Orchard": ["the orchard", "orchard enterprises"],
    "FUGA": ["fuga"],
    "Ingrooves": ["ingrooves"],
    "Empire": ["empire distribution"],
    # --- Majors (self-distribution) ---
    "Universal Music Group": ["universal music group", "umg recordings", "universal music limited"],
    "Sony Music Entertainment": ["sony music entertainment", "sony music ltd", "columbia records", "epic records"],
    "Warner Music Group": ["warner music group", "warner music uk", "atlantic records", "elektra records"],
}

MAJORS = {"Universal Music Group", "Sony Music Entertainment", "Warner Music Group"}

# Major-label imprints: owned by a major group, so they self-distribute.
IMPRINT_OWNERSHIP: dict[str, str] = {
    "Republic Records": "Universal Music Group",
    "Interscope Records": "Universal Music Group",
    "Geffen Records": "Universal Music Group",
    "Def Jam Recordings": "Universal Music Group",
    "Capitol Records": "Universal Music Group",
    "Island Records": "Universal Music Group",
    "Polydor Records": "Universal Music Group",
    "A&M Records": "Universal Music Group",
    "Aftermath Entertainment": "Universal Music Group",
    "Columbia Records": "Sony Music Entertainment",
    "RCA Records": "Sony Music Entertainment",
    "Legacy Recordings": "Sony Music Entertainment",
    "Atlantic Records": "Warner Music Group",
    "Elektra Records": "Warner Music Group",
    "Warner Records": "Warner Music Group",
    "Parlophone Records": "Warner Music Group",
}
DISTRIBUTORS.update(IMPRINT_OWNERSHIP)

INDEPENDENT_AGGREGATORS = {
    name for name, cats in DISTRIBUTORS.items()
    if name not in MAJORS
}


class _Match(NamedTuple):
    distributor: str
    confidence: float
    evidence: str


def classify(label: str | None, copyright_lines: list[str]) -> DistributorResult:
    texts = [t for t in ([label] + copyright_lines) if t]
    haystacks = [(t, t.lower()) for t in texts]

    matches: list[_Match] = []
    for distributor, fragments in DISTRIBUTORS.items():
        for original, lowered in haystacks:
            for fragment in fragments:
                idx = lowered.find(fragment.lower())
                if idx >= 0:
                    # Confidence: label field is a cleaner signal than ©-line
                    from_field = 1.0 if original == label else 0.8
                    fragment_quality = 1.0 if len(fragment) > 6 else 0.7
                    matches.append(
                        _Match(distributor, from_field * fragment_quality, original)
                    )

    if not matches:
        return DistributorResult(
            distributor="unknown",
            category="unknown",
            confidence=0.0,
            evidence=texts,
            label=label,
            copyright_lines=copyright_lines,
        )

    best = max(matches, key=lambda m: m.confidence)

    # Heuristic: a ©-line mentioning two aggregator names usually means
    # "distributed by" — keep the one from the label field first.
    owner = IMPRINT_OWNERSHIP.get(best.distributor)
    if best.distributor in MAJORS or owner:
        category = "major"
    else:
        category = "independent-aggregator"

    return DistributorResult(
        distributor=best.distributor,
        category=category,
        confidence=round(best.confidence, 2),
        evidence=list(dict.fromkeys(m.evidence for m in matches)),
        label=label,
        copyright_lines=copyright_lines,
    )


# Shared pattern for future Apple Music cross-check:
_APPLE_COPYRIGHT_RE = re.compile(r"^(?P<symbol>[©℗])\s*(?P<year>\d{4})\s*(?P<holder>.+)$")
