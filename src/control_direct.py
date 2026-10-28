"""Control pipeline WITHOUT Zetaris.

Implements the same decision rule as sql/20_change_review_view.sql, but the agent
must hold three connections itself: PostgreSQL (psycopg), the CSV file, and the
live eCFR REST API. Used to check that the federated view is correct (identical
verdicts) and to compare latency and integration surface.
"""
from __future__ import annotations

import csv
import json
import os
import re
import urllib.request

from rapidfuzz.distance import Levenshtein

STRIP = re.compile(r"(§+ ?[0-9.]+|part [0-9]+|\([a-z0-9]+\))")
NUM = re.compile(r"([0-9][0-9,.]*[0-9]|[0-9])")
WORDS = re.compile(r"\b(must not|may not|must|may|should|shall|unallowable|allowable|prior written approval|"
                   r"prior approval|required|prohibited|percent|calendar days|months|years)\b")
ECFR = "https://www.ecfr.gov/api/versioner/v1/versions/title-2.json?part=200"


def facts(text: str) -> list[str]:
    low = (text or "").lower()
    return sorted(set(NUM.findall(STRIP.sub(" ", low)) + WORDS.findall(low)))


def load_sources(pg_dsn: str, csv_path: str):
    import psycopg  # only needed for the live control run

    with psycopg.connect(pg_dsn) as con:
        cur = con.execute("SELECT assessment_id, section_id, cited_text FROM compliance_register")
        register = [dict(zip(("assessment_id", "section_id", "cited_text"), r)) for r in cur.fetchall()]
    with open(csv_path, encoding="utf-8", newline="") as f:
        newp = [r for r in csv.DictReader(f) if r["version_date"] == "2024-10-01"]
    req = urllib.request.Request(ECFR, headers={"User-Agent": "regulation-change-sentinel-control"})
    with urllib.request.urlopen(req, timeout=60) as r:
        versions = json.load(r)["content_versions"]
    return register, newp, versions


def decide(register, newp, versions) -> dict[str, dict]:
    amended = {}
    for v in versions:
        if "2024-09-30" < v["amendment_date"] <= "2024-10-01":
            amended[v["identifier"]] = max(amended.get(v["identifier"], ""), v["amendment_date"])
    by_section: dict[str, list[dict]] = {}
    for p in newp:
        by_section.setdefault(p["section_id"], []).append(p)
    out = {}
    for a in register:
        best = None
        for p in by_section.get(a["section_id"], []):
            d = Levenshtein.distance(a["cited_text"].lower(), p["paragraph_text"].lower()) / max(
                len(a["cited_text"]), len(p["paragraph_text"]))
            key = (d, int(p["ordinal"]))
            if best is None or key < best[0]:
                best = (key, p)
        dist = best[0][0] if best else None
        fb, fa = facts(a["cited_text"]), facts(best[1]["paragraph_text"] if best else "")
        if dist == 0:
            verdict = "UNCHANGED"
        elif dist is None or dist > 0.60:
            verdict = "REVIEW_NOT_FOUND"
        elif set(fb) ^ set(fa):
            verdict = "REVIEW_MATERIAL"
        else:
            verdict = "EDITORIAL_ONLY"
        out[a["assessment_id"]] = {"verdict": verdict, "distance": round(dist, 4) if dist is not None else None,
                                   "amendment_date": amended.get(a["section_id"])}
    return out


def run(pg_dsn: str | None = None, csv_path: str | None = None) -> dict[str, dict]:
    return decide(*load_sources(pg_dsn or os.environ["CONTROL_PG_DSN"], csv_path or os.environ["CONTROL_CSV"]))


if __name__ == "__main__":
    print(json.dumps(run(), indent=1))
