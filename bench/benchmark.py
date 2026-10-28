"""Latency and agreement benchmark: federated Zetaris view vs direct control.

Runs inside a container attached to the Zetaris Docker network so both paths see
the same network. Each path: 3 warm-up runs, then N timed end-to-end runs
(connect + fetch + decide). The Zetaris login happens once, outside the timing,
as a long-running agent would hold its session.
"""
import json, os, pathlib, platform, statistics, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.control_direct import run as control_run  # noqa: E402
from src.zetaris_client import Zetaris  # noqa: E402

N, WARM = int(os.environ.get("BENCH_RUNS", "30")), 3


def timed(fn):
    t0 = time.perf_counter(); out = fn(); return time.perf_counter() - t0, out


def stats(xs):
    xs = sorted(xs)
    return {"n": len(xs), "median_s": round(statistics.median(xs), 4), "mean_s": round(statistics.mean(xs), 4),
            "stdev_s": round(statistics.stdev(xs), 4), "p10_s": round(xs[int(0.1 * len(xs))], 4),
            "p90_s": round(xs[int(0.9 * len(xs)) - 1], 4)}


def main():
    z = Zetaris()
    zetaris_fn = lambda: {r["assessment_id"]: r for r in z.sql("SELECT * FROM regsentinel.change_review")["rows"]}
    results = {}
    for name, fn in (("zetaris_federated_view", zetaris_fn), ("direct_control", control_run)):
        for _ in range(WARM):
            fn()
        times, last = [], None
        for _ in range(N):
            t, last = timed(fn); times.append(t)
        results[name] = {"latency": stats(times), "verdicts": {k: v["verdict"] for k, v in last.items()}}
    zv, cv = results["zetaris_federated_view"]["verdicts"], results["direct_control"]["verdicts"]
    agree = sum(zv[k] == cv.get(k) for k in zv)
    report = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": N, "warmup": WARM,
              "host": platform.platform(), "agreement": f"{agree}/{len(zv)}",
              "disagreements": {k: [zv[k], cv.get(k)] for k in zv if zv[k] != cv.get(k)},
              "latency": {k: v["latency"] for k, v in results.items()},
              "integration_surface": {"zetaris_federated_view": {"connections_in_agent": 1, "credentials_in_agent": 1,
                                                                  "client_libraries": ["urllib (stdlib)"]},
                                      "direct_control": {"connections_in_agent": 3, "credentials_in_agent": 1,
                                                         "client_libraries": ["psycopg", "csv", "urllib", "rapidfuzz"]}}}
    out = ROOT / "bench" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"benchmark{os.environ.get('BENCH_TAG', '')}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
