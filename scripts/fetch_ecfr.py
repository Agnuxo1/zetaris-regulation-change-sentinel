"""Fetch two official versions of selected 2 CFR Part 200 sections from the eCFR.

Source: Electronic Code of Federal Regulations (eCFR) versioner API,
https://www.ecfr.gov/developers/documentation/api/v1 . The CFR is a work of the
U.S. Government and is not subject to copyright in the United States.

Outputs:
  data/raw/ecfr/<date>/<section>.xml       verbatim XML responses
  data/processed/sections.csv              one row per section and version
  data/processed/paragraphs.csv            one row per paragraph and version
  data/raw/ecfr/versions_title2_part200.json  the version index
"""
import csv, gzip, hashlib, json, pathlib, re, time, urllib.request, xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ecfr"
OUT = ROOT / "data" / "processed"
API = "https://www.ecfr.gov/api/versioner/v1"
BEFORE, AFTER = "2024-09-30", "2024-10-01"
SECTIONS = ["200.1", "200.112", "200.113", "200.211", "200.305", "200.308", "200.313",
            "200.314", "200.318", "200.320", "200.329", "200.332", "200.333", "200.334",
            "200.344", "200.403", "200.414", "200.431", "200.432", "200.438", "200.439",
            "200.456", "200.475", "200.501", "200.512", "200.216"]
UA = "zetaris-regulation-change-sentinel/1.0 (research demo)"


def get(url):
    req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
        return gzip.decompress(body) if r.headers.get("Content-Encoding") == "gzip" else body


def norm(text):
    return re.sub(r"\s+", " ", text).strip()


def paragraphs(xml_bytes):
    root = ET.fromstring(xml_bytes)
    head = norm("".join(root.find("HEAD").itertext())) if root.find("HEAD") is not None else ""
    paras = [norm("".join(p.itertext())) for p in root.iter() if p.tag in ("P", "FP")]
    return head, [p for p in paras if p]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = RAW / "versions_title2_part200.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_bytes(get(f"{API}/versions/title-2.json?part=200"))
    sec_rows, par_rows = [], []
    for date in (BEFORE, AFTER):
        for sec in SECTIONS:
            path = RAW / date / f"{sec}.xml"
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(get(f"{API}/full/{date}/title-2.xml?part=200&section={sec}"))
                time.sleep(0.4)
            head, paras = paragraphs(path.read_bytes())
            url = f"https://www.ecfr.gov/on/{date}/title-2/section-{sec}"
            text = " ".join(paras)
            sec_rows.append({"section_id": sec, "version_date": date, "heading": head,
                             "section_text": text, "n_paragraphs": len(paras),
                             "sha256": hashlib.sha256(text.encode()).hexdigest(), "source_url": url})
            for i, p in enumerate(paras, 1):
                label = (re.match(r"^\(([a-z0-9]+|[ivx]+)\)", p) or [None, ""])[1]
                par_rows.append({"section_id": sec, "version_date": date, "ordinal": i,
                                 "label": label, "paragraph_text": p, "source_url": url})
    for name, rows in (("sections.csv", sec_rows), ("paragraphs.csv", par_rows)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    changed = sum(1 for s in SECTIONS if len({r["sha256"] for r in sec_rows if r["section_id"] == s}) > 1)
    print(json.dumps({"sections": len(SECTIONS), "versions": [BEFORE, AFTER],
                      "paragraph_rows": len(par_rows), "sections_text_changed": changed}))


if __name__ == "__main__":
    main()
