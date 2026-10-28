"""Score change-detection methods against blind ground-truth labels.

Ground truth: eval/labeling/labels.csv (independent annotator, blind to the method)
plus the 3 assessments whose cited text is byte-identical in the new version.
Positive class = the assessment must be re-reviewed (MATERIAL change).

Methods
  section_amended  control A: re-review everything citing a section the eCFR marks as amended
  text_changed     control B: re-review whenever the cited paragraph text is not identical
  sentinel         this project: federated Zetaris view (facts diff + successor alignment)
"""
import csv, json, pathlib, random, statistics, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REVIEW = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "latest" / "review.json"


def prf(y, p):
    tp = sum(a and b for a, b in zip(y, p)); fp = sum((not a) and b for a, b in zip(y, p))
    fn = sum(a and (not b) for a, b in zip(y, p)); tn = len(y) - tp - fp - fn
    prec = tp / (tp + fp) if tp + fp else 0.0; rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": prec, "recall": rec, "f1": f1,
            "accuracy": (tp + tn) / len(y), "flagged": tp + fp}


def bootstrap(y, p, seed, n=2000):
    rng = random.Random(seed); idx = range(len(y)); f1s = []
    for _ in range(n):
        s = [rng.choice(idx) for _ in idx]
        f1s.append(prf([y[i] for i in s], [p[i] for i in s])["f1"])
    f1s.sort()
    return f1s[int(0.025 * n)], f1s[int(0.975 * n)]


def main():
    rows = {r["assessment_id"]: r for r in json.loads(REVIEW.read_text(encoding="utf-8"))["rows"]}
    labels = {r["assessment_id"]: r for r in csv.DictReader(open(ROOT / "eval/labeling/labels.csv", encoding="utf-8"))}
    ids = sorted(rows)
    truth, conf = [], []
    for i in ids:
        if i in labels:
            truth.append(labels[i]["label"].strip().upper() == "MATERIAL"); conf.append(labels[i]["confidence"].strip())
        else:  # identical text in the new version
            assert rows[i]["verdict"] == "UNCHANGED", i
            truth.append(False); conf.append("high")
    preds = {
        "section_amended": [bool(rows[i]["amendment_date"]) for i in ids],
        "text_changed": [rows[i]["verdict"] != "UNCHANGED" for i in ids],
        "sentinel": [rows[i]["verdict"].startswith("REVIEW") for i in ids],
    }
    out = {"n": len(ids), "positives": sum(truth), "methods": {}}
    for name, p in preds.items():
        m = prf(truth, p)
        cis = [bootstrap(truth, p, s) for s in (0, 1, 2)]
        m["f1_ci95_seeds"] = [[round(a, 3), round(b, 3)] for a, b in cis]
        m["f1_ci95_mean"] = [round(statistics.mean(c[0] for c in cis), 3), round(statistics.mean(c[1] for c in cis), 3)]
        hi = [k for k, c in enumerate(conf) if c == "high"]
        m["high_confidence_subset"] = prf([truth[k] for k in hi], [p[k] for k in hi]) | {"n": len(hi)}
        reg = {r["assessment_id"]: r["selection"] for r in csv.DictReader(open(ROOT / "data/processed/compliance_register.csv", encoding="utf-8"))}
        rnd = [k for k, i in enumerate(ids) if reg[i] == "random"]
        m["random_sample_subset"] = prf([truth[k] for k in rnd], [p[k] for k in rnd]) | {"n": len(rnd)}
        m["review_load_vs_section_amended"] = round(m["flagged"] / sum(preds["section_amended"]), 3)
        out["methods"][name] = m
    out["errors_sentinel"] = [{"assessment_id": i, "truth": "MATERIAL" if t else "NOT_MATERIAL",
                               "verdict": rows[i]["verdict"], "label_confidence": c,
                               "label_rationale": labels.get(i, {}).get("rationale", "identical text")}
                              for i, t, p, c in zip(ids, truth, preds["sentinel"], conf) if t != p]
    (ROOT / "eval" / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    with open(ROOT / "eval" / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["method", "precision", "recall", "f1", "f1_ci95_low", "f1_ci95_high", "flagged", "n"])
        for name, m in out["methods"].items():
            w.writerow([name, round(m["precision"], 3), round(m["recall"], 3), round(m["f1"], 3),
                        *m["f1_ci95_mean"], m["flagged"], out["n"]])
    print(json.dumps({k: {x: (round(v, 3) if isinstance(v, float) else v) for x, v in m.items()
                          if x in ("precision", "recall", "f1", "flagged", "f1_ci95_mean")} | {"random_f1": round(m["random_sample_subset"]["f1"], 3), "highconf_f1": round(m["high_confidence_subset"]["f1"], 3)}
                      for k, m in out["methods"].items()}, indent=1))
    print("sentinel errors:", json.dumps(out["errors_sentinel"], indent=1))


if __name__ == "__main__":
    main()
