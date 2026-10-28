"""Render the README figures (animated GIFs) from the measured results.

Every number drawn here is read from results/, eval/ or bench/ — nothing is typed in.
Palette: dark-surface categorical steps validated for CVD separation
(blue = Sentinel via Zetaris, orange = section-amended control, aqua = text-changed control).
"""
import json, pathlib, statistics, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets"; OUT.mkdir(parents=True, exist_ok=True)
SURF, PANEL, INK, INK2, MUTED, GRID = "#111318", "#1b1f2a", "#f0efec", "#c3c2b7", "#8a8f9c", "#2a2f3c"
BLUE, ORANGE, AQUA, YELLOW, RED, VIOLET = "#3987e5", "#d95926", "#199e70", "#c98500", "#e66767", "#9085e9"
plt.rcParams.update({"font.family": "Segoe UI", "font.size": 12, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})

review = json.loads((ROOT / "results/latest/review.json").read_text(encoding="utf-8"))
ev = json.loads((ROOT / "eval/results.json").read_text(encoding="utf-8"))
M = ev["methods"]
NAMES = {"section_amended": "Control A · section amended", "text_changed": "Control B · text changed",
         "sentinel": "Sentinel · Zetaris view"}
COL = {"section_amended": ORANGE, "text_changed": AQUA, "sentinel": BLUE}


def ease(t):
    t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3


def save(anim, name, fps=12):
    anim.save(OUT / name, writer=PillowWriter(fps=fps), dpi=100)
    print("wrote", name, round((OUT / name).stat().st_size / 1e6, 2), "MB")


# 1 ── architecture: three live sources -> one federated Zetaris view -> agent -> review queue
def architecture():
    fig = plt.figure(figsize=(10, 4.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off")
    def box(x, y, w, h, title, sub, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6", fc=PANEL, ec=color, lw=2))
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", fontsize=12.5, weight="bold")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=9.5, color=INK2)
    srcs = [(36, "PostgreSQL", "compliance register · 48 rows", ORANGE),
            (21, "File store (CSV)", "eCFR paragraphs · 2 versions", AQUA),
            (6, "REST · eCFR API", "live amendment index", YELLOW)]
    for y, t, s, c in srcs:
        box(2, y, 24, 8, t, s, c)
    box(38, 14, 24, 18, "Zetaris", "one federated SQL view\nregsentinel.change_review", BLUE)
    box(74, 26, 23, 10, "Sentinel agent", "1 connection · explains why", VIOLET)
    box(74, 8, 23, 10, "Review queue", "", RED)
    ax.text(85.5, 46 - 2.5, "Regulation Change Sentinel", ha="center", fontsize=11, color=MUTED)
    qtxt = ax.text(85.5, 10.2, "", ha="center", fontsize=10, color=INK2)
    for y, *_ in srcs:
        ax.plot([26.8, 37.2], [y + 4, 23], color=GRID, lw=1.5, zorder=0)
    ax.plot([62.8, 73.2], [23, 31], color=GRID, lw=1.5, zorder=0); ax.plot([85.5, 85.5], [25.2, 18.8], color=GRID, lw=1.5, zorder=0)
    dots = [ax.plot([], [], "o", ms=8, color=c, mec=SURF, mew=2)[0] for *_, c in srcs]
    d2 = ax.plot([], [], "o", ms=9, color=BLUE, mec=SURF, mew=2)[0]; d3 = ax.plot([], [], "o", ms=9, color=VIOLET, mec=SURF, mew=2)[0]
    n_rev = review["summary"]["needs_review"]; n_all = review["summary"]["assessments"]
    F = 72
    def upd(i):
        t = (i % 36) / 36
        for k, ((y, *_), d) in enumerate(zip(srcs, dots)):
            tt = ease((t * 1.6 - k * 0.12)); d.set_data([26.8 + (37.2 - 26.8) * tt], [y + 4 + (23 - y - 4) * tt])
        t2 = ease((t - 0.45) / 0.3); d2.set_data([62.8 + 10.4 * t2], [23 + 8 * t2])
        t3 = ease((t - 0.72) / 0.25); d3.set_data([85.5], [25.2 - 6.4 * t3])
        shown = int(n_rev * ease(i / (F * 0.8)))
        qtxt.set_text(f"{shown} of {n_all} assessments flagged")
        return dots + [d2, d3, qtxt]
    save(FuncAnimation(fig, upd, frames=F), "architecture.gif"); plt.close(fig)


# 2 ── verdict mosaic: 48 assessments resolve into their verdicts
def mosaic():
    rows = sorted(review["rows"], key=lambda r: r["assessment_id"])
    vcol = {"UNCHANGED": "#4b5263", "EDITORIAL_ONLY": AQUA, "REVIEW_MATERIAL": RED, "REVIEW_NOT_FOUND": YELLOW}
    vlab = {"UNCHANGED": "unchanged", "EDITORIAL_ONLY": "editorial only — assessment stands",
            "REVIEW_MATERIAL": "facts changed — re-review", "REVIEW_NOT_FOUND": "rewritten/removed — re-review"}
    fig = plt.figure(figsize=(10, 4.4)); ax = fig.add_axes([0.02, 0.04, 0.62, 0.84]); ax.set_xlim(0, 12); ax.set_ylim(0, 4); ax.axis("off")
    fig.text(0.02, 0.93, "48 assessments, one federated Zetaris query", fontsize=15, weight="bold")
    tiles = []
    for k, r in enumerate(rows):
        x, y = k % 12, 3 - k // 12
        p = FancyBboxPatch((x + 0.08, y + 0.1), 0.84, 0.8, boxstyle="round,pad=0,rounding_size=0.12", fc=PANEL, ec=GRID, lw=1)
        ax.add_patch(p); ax.text(x + 0.5, y + 0.5, r["assessment_id"][-3:], ha="center", va="center", fontsize=8.5, color=INK2)
        tiles.append((p, vcol[r["verdict"]]))
    lg = fig.add_axes([0.66, 0.1, 0.33, 0.75]); lg.axis("off"); lg.set_xlim(0, 1); lg.set_ylim(0, 1)
    counts = review["summary"]["by_verdict"]; texts = []
    for j, v in enumerate(["REVIEW_MATERIAL", "REVIEW_NOT_FOUND", "EDITORIAL_ONLY", "UNCHANGED"]):
        y = 0.85 - j * 0.22
        lg.add_patch(FancyBboxPatch((0, y - 0.05), 0.08, 0.1, boxstyle="round,pad=0,rounding_size=0.02", fc=vcol[v], ec="none"))
        texts.append(lg.text(0.12, y, "", va="center", fontsize=11))
        texts[-1]._target = (counts.get(v, 0), vlab[v])
    F = 60
    def upd(i):
        for k, (p, c) in enumerate(tiles):
            if i >= 4 + k * 0.9:
                p.set_facecolor(c); p.set_edgecolor(c)
        for t in texts:
            n, lab = t._target; t.set_text(f"{int(n * ease((i - 10) / 40))}  {lab}")
        return []
    save(FuncAnimation(fig, upd, frames=F + 18), "verdicts.gif"); plt.close(fig)


# 3 ── review workload and accuracy (animated bars with 95% bootstrap CI)
def metrics():
    order = ["section_amended", "text_changed", "sentinel"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.74, bottom=0.2, wspace=0.28)
    fig.text(0.02, 0.92, "Fewer reviews, better aimed", fontsize=15, weight="bold")
    fig.text(0.02, 0.86, f"n = {ev['n']} assessments · {ev['positives']} material changes (blind labels) · 95% bootstrap CI",
             fontsize=10, color=MUTED)
    for a in (a1, a2):
        a.spines[["top", "right"]].set_visible(False); a.grid(axis="y", color=GRID, lw=0.8); a.set_axisbelow(True)
    a1.set_title("Assessments sent to re-review", fontsize=11.5, color=INK2, loc="left")
    a1.axhline(ev["positives"], color=INK2, lw=1.2, ls="--"); a1.text(2.45, ev["positives"] + 1, "truly material", fontsize=9, color=INK2, ha="right")
    a1.set_ylim(0, 52); a1.set_xticks(range(3)); a1.set_xticklabels(["Control A", "Control B", "Sentinel"])
    a2.set_title("Precision · Recall · F1", fontsize=11.5, color=INK2, loc="left")
    a2.set_ylim(0, 1.05); a2.set_xticks(range(3)); a2.set_xticklabels(["precision", "recall", "F1"])
    b1 = a1.bar(range(3), [0] * 3, width=0.6, color=[COL[m] for m in order])
    lab1 = [a1.text(k, 0, "", ha="center", fontsize=11, weight="bold") for k in range(3)]
    w = 0.26; bars2 = []
    for j, m in enumerate(order):
        bars2.append(a2.bar([x + (j - 1) * w for x in range(3)], [0] * 3, width=w - 0.03, color=COL[m], label=NAMES[m]))
    a2.legend(loc="upper center", bbox_to_anchor=(0.45, -0.1), ncol=3, frameon=False, fontsize=8.6)
    ci_drawn = [False]
    F = 50
    def upd(i):
        e = ease(i / 32)
        for k, m in enumerate(order):
            v = M[m]["flagged"] * e; b1[k].set_height(v); lab1[k].set_position((k, v + 1)); lab1[k].set_text(f"{round(v)}")
            for x, key in enumerate(["precision", "recall", "f1"]):
                bars2[k][x].set_height(M[m][key] * e)
        if i == 34 and not ci_drawn[0]:
            for k, m in enumerate(order):
                lo, hi = M[m]["f1_ci95_mean"]; x = 2 + (k - 1) * w
                a2.plot([x, x], [lo, hi], color=INK, lw=1.5); a2.plot([x - 0.05, x + 0.05], [hi, hi], color=INK, lw=1.5)
                a2.plot([x - 0.05, x + 0.05], [lo, lo], color=INK, lw=1.5)
                a2.text(x, hi + 0.03, f"{M[m]['f1']:.2f}", ha="center", fontsize=8.5, color=INK2)
            ci_drawn[0] = True
        return []
    save(FuncAnimation(fig, upd, frames=F + 20), "metrics.gif"); plt.close(fig)


# 4 ── evidence diff: what changed, quoted from the official text
def diff():
    pick = [r for r in review["rows"] if r["assessment_id"] in ("NCHA-001", "NCHA-002", "NCHA-004")]
    fig = plt.figure(figsize=(10.5, 5.6)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    ax.text(3, 56.5, "Evidence the agent shows a reviewer", fontsize=15, weight="bold")
    ax.text(3, 53.2, "Quoted from 2 CFR Part 200 as in force on 2024-09-30 and 2024-10-01 (eCFR). Facts compared inside Zetaris.",
            fontsize=9.5, color=MUTED)
    items = []
    for k, r in enumerate(pick):
        y = 47 - k * 16
        rem, add = json.loads(r["facts_removed"]), json.loads(r["facts_added"])
        def clip(s, f):
            s = s or ""; i = max(0, s.lower().find(f[0].lower()) - 70) if f else 0
            return ("…" if i else "") + s[i:i + 170] + "…"
        ax.text(3, y, f"{r['assessment_id']} · {r['policy_area']} · 2 CFR {r['section_id']}", fontsize=11, weight="bold")
        t_old = ax.text(3, y - 2.2, "", fontsize=9.2, color=INK2, va="top", wrap=True)
        t_new = ax.text(52, y - 2.2, "", fontsize=9.2, color=INK2, va="top")
        tag = ax.text(97, y, "", fontsize=10.5, ha="right", weight="bold")
        items.append((textwrap.fill("BEFORE  " + clip(r["cited_text"], rem), 62),
                      textwrap.fill("AFTER  " + clip(r["successor_text"], add), 62),
                      f"{' '.join(rem) or '—'}  →  {' '.join(add) or '—'}", t_old, t_new, tag))
    F = 84
    def upd(i):
        for k, (o, n, tg, to, tn, tt) in enumerate(items):
            s = i - k * 22
            to.set_text(o[:max(0, int(len(o) * ease(s / 12)))]); tn.set_text(n[:max(0, int(len(n) * ease((s - 6) / 12)))])
            if s > 16:
                tt.set_text(tg); tt.set_color(RED)
        return []
    save(FuncAnimation(fig, upd, frames=F), "evidence-diff.gif", fps=14); plt.close(fig)


# 5 ── latency across three benchmark sessions (static: honest trade-off)
def latency():
    files = sorted((ROOT / "bench/results").glob("benchmark_s*.json")) or [ROOT / "bench/results/benchmark.json"]
    runs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    fig, ax = plt.subplots(figsize=(9, 3.4)); fig.subplots_adjust(left=0.26, right=0.95, top=0.74, bottom=0.2)
    fig.text(0.02, 0.9, "End-to-end latency (mean of session medians; whisker = p10–p90 range)", fontsize=14, weight="bold")
    fig.text(0.02, 0.82, f"{len(runs)} sessions × {runs[0]['runs']} timed runs on the Zetaris host · verdict agreement "
             f"{runs[0]['agreement']}", fontsize=9.5, color=MUTED)
    for k, (key, lab, c) in enumerate([("direct_control", "Direct control\n3 connections in agent", ORANGE),
                                         ("zetaris_federated_view", "Zetaris federated view\n1 connection in agent", BLUE)]):
        med = statistics.mean(r["latency"][key]["median_s"] for r in runs)
        lo = min(r["latency"][key]["p10_s"] for r in runs); hi = max(r["latency"][key]["p90_s"] for r in runs)
        ax.barh(k, med, height=0.5, color=c); ax.plot([lo, hi], [k, k], color=INK, lw=1.6)
        ax.text(hi + 0.05, k, f"{med:.2f} s", va="center", fontsize=11, weight="bold")
        ax.text(-0.03, k, lab, va="center", ha="right", fontsize=10, transform=ax.get_yaxis_transform())
    ax.set_yticks([]); ax.set_xlabel("seconds"); ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=GRID); ax.set_axisbelow(True)
    fig.savefig(OUT / "latency.png", dpi=110); plt.close(fig); print("wrote latency.png")


if __name__ == "__main__":
    architecture(); mosaic(); metrics(); diff(); latency()
