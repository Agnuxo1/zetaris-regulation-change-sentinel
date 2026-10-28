"""Offline checks: data integrity, decision rule, evaluation reproducibility (no Zetaris needed)."""
import csv, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.control_direct import decide, facts  # noqa: E402

PARAS = list(csv.DictReader(open(ROOT / "data/processed/paragraphs.csv", encoding="utf-8")))
REG = list(csv.DictReader(open(ROOT / "data/processed/compliance_register.csv", encoding="utf-8")))
REVIEW = json.loads((ROOT / "results/latest/review.json").read_text(encoding="utf-8"))


def test_register_quotes_are_verbatim_ecfr():
    old = {(p["section_id"], p["paragraph_text"]) for p in PARAS if p["version_date"] == "2024-09-30"}
    assert len(REG) == 48 and all((a["section_id"], a["cited_text"]) in old for a in REG)


def test_facts_ignore_section_numbers_and_labels():
    assert facts("(b) See § 200.414. Costs of $5,000 must be approved.") == ["5,000", "must"]
    assert "unallowable" in facts("are unallowable as a direct cost") and "allowable" not in facts("are unallowable")


def test_python_control_matches_recorded_zetaris_verdicts():
    versions = json.loads((ROOT / "data/raw/ecfr/versions_title2_part200.json").read_text(encoding="utf-8"))["content_versions"]
    newp = [p for p in PARAS if p["version_date"] == "2024-10-01"]
    reg = [{k: a[k] for k in ("assessment_id", "section_id", "cited_text")} for a in REG]
    ours = decide(reg, newp, versions)
    zetaris = {r["assessment_id"]: r["verdict"] for r in REVIEW["rows"]}
    assert {k: v["verdict"] for k, v in ours.items()} == zetaris


def test_known_threshold_changes_are_flagged():
    v = {r["assessment_id"]: r for r in REVIEW["rows"]}
    for aid, old, new in [("NCHA-001", "5,000", "10,000"), ("NCHA-002", "25,000", "50,000"), ("NCHA-004", "750,000", "1,000,000")]:
        assert v[aid]["verdict"] == "REVIEW_MATERIAL"
        assert old in v[aid]["facts_removed"] and new in v[aid]["facts_added"]


def test_evaluation_is_reproducible():
    subprocess.run([sys.executable, str(ROOT / "eval/evaluate.py")], check=True, capture_output=True)
    m = json.loads((ROOT / "eval/results.json").read_text(encoding="utf-8"))["methods"]
    assert round(m["sentinel"]["f1"], 3) == 0.727 and m["sentinel"]["flagged"] == 25
    assert m["section_amended"]["flagged"] == 48 and m["text_changed"]["flagged"] == 45
