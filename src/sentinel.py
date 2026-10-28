"""Regulation Change Sentinel agent.

Reads one federated Zetaris view (regsentinel.change_review) and turns it into an
auditable review queue: which compliance assessments must be re-opened after a
regulation changed, why, and with what evidence. The agent itself holds a single
connection (Zetaris); the database, file store and live eCFR API stay behind it.

Usage:
  python -m src.sentinel provision            # register sources + create the view
  python -m src.sentinel review [--out DIR]   # run the review and write reports
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import sys

from .zetaris_client import Zetaris, ZetarisError

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
VIEW = "regsentinel.change_review"
VARIANTS = {
    "v1": (VIEW, "20_change_review_view.sql"),
    "modal-v2": ("regsentinel.change_review_modal_v2", "21_change_review_modal_v2.sql"),
}


def split_sql(text: str) -> list[str]:
    body = "\n".join(l for l in text.splitlines() if not l.strip().startswith("--"))
    return [s.strip() for s in body.split(";") if s.strip()]


def provision(z: Zetaris, variant: str = "v1") -> None:
    view_name, sql_name = VARIANTS[variant]
    for stmt in split_sql((SQL_DIR / "10_register_sources.sql").read_text(encoding="utf-8")):
        try:
            z.sql(stmt)
            print("ok   ", stmt[:70].replace("\n", " "))
        except ZetarisError as err:
            if "exist" not in str(err).lower():
                raise
            print("skip ", stmt[:70].replace("\n", " "), "(already exists)")
    view = (SQL_DIR / sql_name).read_text(encoding="utf-8")
    view = view[view.index("CREATE SCHEMASTORE VIEW"):]
    try:
        z.sql("DROP VIEW " + view_name)
    except ZetarisError:
        pass
    z.sql(view)
    print("ok    view", view_name)


def parse_list(value) -> list[str]:
    if isinstance(value, list):
        return value
    try:
        return json.loads(value) if value else []
    except (TypeError, json.JSONDecodeError):
        return []


def explain(r: dict) -> str:
    removed, added = parse_list(r["facts_removed"]), parse_list(r["facts_added"])
    v = r["verdict"]
    if v == "UNCHANGED":
        return "Cited text is unchanged in the new version; the assessment stands."
    if v == "EDITORIAL_ONLY":
        return ("Wording changed but every amount, deadline and obligation word in the cited "
                f"requirement is preserved (successor paragraph #{r['successor_ordinal']}). No re-review needed.")
    if v == "REVIEW_NOT_FOUND":
        return ("No sufficiently similar paragraph exists in the new version (closest edit distance "
                f"{float(r['distance']):.2f}). The requirement was rewritten, moved or removed: re-review.")
    parts = []
    if removed:
        parts.append("no longer states " + ", ".join(removed))
    if added:
        parts.append("now states " + ", ".join(added))
    return "Successor paragraph #%s %s: re-review." % (r["successor_ordinal"], " and ".join(parts))


def review(z: Zetaris, out: pathlib.Path, view: str = VIEW) -> dict:
    if view not in {v[0] for v in VARIANTS.values()}:
        raise ValueError("Unknown review view")
    res = z.sql(f"SELECT * FROM {view} ORDER BY assessment_id")
    rows = res["rows"]
    for r in rows:
        r["explanation"] = explain(r)
        r["needs_review"] = r["verdict"].startswith("REVIEW")
    queue = [r for r in rows if r["needs_review"]]
    summary = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "view": view, "assessments": len(rows), "needs_review": len(queue),
               "by_verdict": {v: sum(r["verdict"] == v for r in rows) for v in sorted({r["verdict"] for r in rows})},
               "zetaris_server_ms": res["server_ms"], "wall_s": round(res["wall_s"], 3)}
    out.mkdir(parents=True, exist_ok=True)
    (out / "review.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    md = [f"# Review queue — {summary['generated_utc']}", "",
          f"{summary['needs_review']} of {summary['assessments']} assessments need re-review. "
          f"Source: one federated Zetaris query ({summary['zetaris_server_ms']} ms server time).", "",
          "| Assessment | Area | 2 CFR | Verdict | Why |", "|---|---|---|---|---|"]
    md += [f"| {r['assessment_id']} | {r['policy_area']} | [{r['section_id']}]({r['successor_url'] or r['cited_url']}) "
           f"| {r['verdict']} | {r['explanation']} |" for r in queue]
    (out / "review.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "review.html").write_text(render_html(summary, rows), encoding="utf-8")
    return summary


def mark(text: str, facts: list[str], cls: str) -> str:
    out = html.escape(text or "")
    for f in sorted(facts, key=len, reverse=True):
        out = re.sub(r"(?<![\w,.])(%s)(?![\w,])" % re.escape(html.escape(f)), rf'<mark class="{cls}">\1</mark>',
                     out, flags=re.I)
    return out


def render_html(summary: dict, rows: list[dict]) -> str:
    cards = []
    for r in rows:
        if not r["needs_review"]:
            continue
        cards.append(f"""<article class="card"><header><b>{r['assessment_id']}</b> · {html.escape(r['policy_area'])}
 · 2 CFR {r['section_id']} · owner {html.escape(r['owner'])}<span class="v">{r['verdict']}</span></header>
<p class="why">{html.escape(r['explanation'])}</p>
<div class="cols"><div><h4>Cited on {r['cited_version']} <a href="{r['cited_url']}">source</a></h4><p>{mark(r['cited_text'], parse_list(r['facts_removed']), 'old')}</p></div>
<div><h4>In force from {r['amendment_date'] or '?'} <a href="{r['successor_url'] or '#'}">source</a></h4><p>{mark(r['successor_text'], parse_list(r['facts_added']), 'new')}</p></div></div></article>""")
    counts = " · ".join(f"{k}: {v}" for k, v in summary["by_verdict"].items())
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Review queue</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:24px;background:#0b1020;color:#e6e9f2}}
h1{{font-size:22px}}.card{{background:#141a33;border:1px solid #2a3360;border-radius:10px;padding:14px;margin:12px 0}}
.v{{float:right;font-weight:700;color:#ffb44c}}.why{{color:#9fe3c8}}.cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
h4{{margin:4px 0;color:#9aa6d6;font-weight:600}}a{{color:#7fb2ff}}mark.old{{background:#5c1f2b;color:#ffd0d6}}mark.new{{background:#164a35;color:#c9ffe6}}</style>
<h1>Regulation Change Sentinel — review queue</h1>
<p>{summary['needs_review']} of {summary['assessments']} assessments need re-review ({counts}). One federated Zetaris query, {summary['zetaris_server_ms']} ms.</p>
{''.join(cards)}</html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["provision", "review"])
    ap.add_argument("--variant", choices=VARIANTS, default="v1")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    z = Zetaris()
    if args.command == "provision":
        provision(z, args.variant)
    else:
        out = pathlib.Path(args.out) if args.out else ROOT / "results" / ("latest" if args.variant == "v1" else "modal-v2-live")
        print(json.dumps(review(z, out, VARIANTS[args.variant][0]), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
