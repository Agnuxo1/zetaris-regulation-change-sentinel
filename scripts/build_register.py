"""Build the synthetic compliance register of a fictional grant recipient.

Every assessment cites one real paragraph of 2 CFR Part 200 as it read on
2024-09-30 (the day before the 2024 Uniform Guidance revision took effect).
The organisation, owners and conclusions are fictional (CC0).

Selection is reproducible: 8 anchor paragraphs that a grants office cites most
often, plus a seeded random sample of requirement-bearing paragraphs.
"""
import csv, json, pathlib, random, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PARAS = ROOT / "data" / "processed" / "paragraphs.csv"
OUT = ROOT / "data" / "processed" / "compliance_register.csv"
SEED, N_RANDOM, BEFORE = 20261028, 40, "2024-09-30"

ANCHORS = [("200.1", r"^Equipment means"), ("200.1", r"^Modified Total Direct Cost"),
           ("200.414", r"de minimis rate of 10%"), ("200.501", r"^\(a\) Audit required"),
           ("200.313", r"fair market value of \$5,000 or less"), ("200.439", r"unit cost of \$5,000"),
           ("200.333", r"fixed amounts up to the Simplified"), ("200.334", r"^\(c\) Records for real property")]
REQUIREMENT = re.compile(r"\b(must|may not|should|unallowable|allowable|required|prior (written )?approval|"
                         r"no later than|calendar days|percent|\$[0-9])", re.I)
AREAS = {"200.1": "Definitions", "200.112": "Conflict of interest", "200.113": "Mandatory disclosures",
         "200.211": "Award terms", "200.216": "Telecom prohibition", "200.305": "Payment",
         "200.308": "Budget revisions", "200.313": "Equipment", "200.314": "Supplies",
         "200.318": "Procurement standards", "200.320": "Procurement methods", "200.329": "Reporting",
         "200.332": "Subrecipient monitoring", "200.333": "Fixed amount subawards",
         "200.334": "Record retention", "200.344": "Closeout", "200.403": "Allowable costs",
         "200.414": "Indirect costs", "200.431": "Fringe benefits", "200.432": "Conferences",
         "200.438": "Entertainment", "200.439": "Capital expenditures", "200.456": "Participant support",
         "200.475": "Travel", "200.501": "Single audit", "200.512": "Audit reporting"}
OWNERS = ["Grants Office", "Finance", "Procurement", "Internal Audit", "Programme Management"]


def main():
    rows = [r for r in csv.DictReader(open(PARAS, encoding="utf-8")) if r["version_date"] == BEFORE]
    chosen, seen = [], set()
    for sec, pat in ANCHORS:
        r = next(r for r in rows if r["section_id"] == sec and re.search(pat, r["paragraph_text"]))
        chosen.append(("anchor", r)); seen.add((sec, r["ordinal"]))
    pool = [r for r in rows if (r["section_id"], r["ordinal"]) not in seen
            and 80 <= len(r["paragraph_text"]) <= 900 and REQUIREMENT.search(r["paragraph_text"])]
    rng = random.Random(SEED)
    chosen += [("random", r) for r in rng.sample(pool, N_RANDOM)]
    out = []
    for i, (how, r) in enumerate(chosen, 1):
        sec = r["section_id"]
        out.append({"assessment_id": f"NCHA-{i:03d}", "policy_area": AREAS[sec], "section_id": sec,
                    "cited_ordinal": int(r["ordinal"]), "cited_label": r["label"],
                    "cited_text": r["paragraph_text"], "cited_version": BEFORE,
                    "conclusion": f"Our {AREAS[sec].lower()} procedure was reviewed against 2 CFR {sec} "
                                  f"as cited and found compliant.",
                    "owner": OWNERS[i % len(OWNERS)], "assessed_on": "2024-06-14",
                    "selection": how, "source_url": r["source_url"]})
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print(json.dumps({"assessments": len(out), "anchors": len(ANCHORS), "random": N_RANDOM, "seed": SEED,
                      "pool": len(pool), "sections": len({o["section_id"] for o in out})}))


if __name__ == "__main__":
    main()
