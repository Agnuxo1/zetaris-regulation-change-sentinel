"""Assemble the Zetaris Demo Challenge video (1920x1080, 25 fps, English narration + subtitles)."""
import json, os, pathlib, re, subprocess, sys
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
A = REPO / "docs" / "assets"
LIVE = pathlib.Path(os.environ.get("LIVE_MP4", HERE / "out" / "live.mp4"))
NAME = sys.argv[1] if len(sys.argv) > 1 else "EVIDENCE-CHANGE-SENTINEL_291026"
OUT = HERE / "out"; OUT.mkdir(exist_ok=True); TMP = HERE / "tmp"; TMP.mkdir(exist_ok=True)
N = json.load(open(HERE / "narration.json", encoding="utf-8")); D = json.load(open(HERE / "durations.json"))
URL = "github.com/Agnuxo1/zetaris-regulation-change-sentinel"
BG, PANEL, INK, INK2, MUTED = "#111318", "#1b1f2a", "#f0efec", "#c3c2b7", "#8a8f9c"
BLUE, ORANGE, AQUA, YELLOW, RED = "#3987e5", "#d95926", "#199e70", "#c98500", "#e66767"
F = lambda s, b=False: ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if b else "C:/Windows/Fonts/segoeui.ttf", s)


def run(args):
    r = subprocess.run([FF, "-y", "-loglevel", "error", *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


def card(path, title, lines=(), kicker=None, foot=None, big=None):
    im = Image.new("RGB", (1920, 1080), BG); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1920, 8], fill=BLUE)
    y = 190
    if kicker:
        d.text((150, y - 70), kicker, font=F(34, True), fill=BLUE)
    d.text((150, y), title, font=F(70, True), fill=INK); y += 140
    if big:
        x = 150
        for value, label, col in big:
            d.rounded_rectangle([x, y, x + 500, y + 230], 24, fill=PANEL, outline=col, width=4)
            d.text((x + 40, y + 30), value, font=F(96, True), fill=col)
            d.text((x + 40, y + 160), label, font=F(30), fill=INK2); x += 540
        y += 290
    for ln in lines:
        d.text((150, y), ln, font=F(40), fill=INK2); y += 66
    if foot:
        d.text((150, 980), foot, font=F(28), fill=MUTED)
    im.save(path)


def still(img, dur, out):
    run(["-loop", "1", "-t", f"{dur:.2f}", "-i", str(img), "-vf", "fps=25,format=yuv420p", "-c:v", "libx264", "-crf", "18", str(out)])


def gif_frames(src, fps=25):
    """Composite every GIF frame with Pillow (respecting per-frame durations) into a PNG sequence."""
    d = TMP / f"frames_{src.stem}"; d.mkdir(exist_ok=True)
    for f in d.glob("*.png"):
        f.unlink()
    im = Image.open(src); k = 0
    for i in range(im.n_frames):
        im.seek(i); fr = im.convert("RGB"); reps = max(1, round(im.info.get("duration", 83) / (1000 / fps)))
        for _ in range(reps):
            fr.save(d / f"{k:05d}.png"); k += 1
    return d


def anim(src, dur, out, label=None):
    """GIF/PNG centred above the subtitle band, last frame held until dur."""
    vf = (f"scale=w=1800:h=880:force_original_aspect_ratio=decrease:flags=lanczos,pad=1920:1080:(ow-iw)/2:(900-ih)/2+20:color={BG},fps=25,"
          f"tpad=stop_mode=clone:stop_duration={dur:.2f},trim=duration={dur:.2f},format=yuv420p")
    args = (["-framerate", "25", "-i", str(gif_frames(src) / "%05d.png")] if src.suffix == ".gif"
            else ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(src)])
    run([*args, "-vf", vf, "-c:v", "libx264", "-crf", "18", str(out)])


def main():
    segs, t, audio, srt_parts = [], 0.0, [], []
    def add(path, dur, narr_ids_with_offsets):
        nonlocal t
        for sid, off in narr_ids_with_offsets:
            audio.append((HERE / "audio" / f"{sid}.mp3", t + off)); srt_parts.append((sid, t + off))
        segs.append(path); t += dur

    card(TMP / "c1.png", "Regulation Change Sentinel", ["When the rules behind your grants change overnight,",
         "which of your compliance decisions are now wrong?"], kicker="ZETARIS DEMO CHALLENGE · OPEN AGENT HACKATHON 2026",
         foot="Team Evidence Change Sentinel · Francisco Angulo de Lafuente")
    d1 = D["s1_title"] + 1.2; still(TMP / "c1.png", d1, TMP / "v1.mp4"); add(TMP / "v1.mp4", d1, [("s1_title", 0.5)])
    card(TMP / "c2.png", "2 CFR Part 200 was rewritten", ["Effective 1 October 2024 · source: eCFR versioner API (public domain)",
         "Fictional grants office, real regulatory text"], kicker="THE PROBLEM",
         big=[("188", "sections amended", ORANGE), ("48", "assessments quoting them", AQUA), ("?", "still valid", RED)])
    d2 = D["s2_problem"] + 1.0; still(TMP / "c2.png", d2, TMP / "v2.mp4"); add(TMP / "v2.mp4", d2, [("s2_problem", 0.4)])
    # live recording, untouched timing, with a corner label
    label = "LIVE · Zetaris SQL Workspace on our server · continuous capture 2026-10-28"
    run(["-i", str(LIVE), "-vf", f"scale=1680:945:flags=lanczos,pad=1920:1080:120:0:color={BG},"
         f"drawtext=fontfile='C\\:/Windows/Fonts/segoeuib.ttf':text='{label}':fontcolor={BLUE}:fontsize=22:box=1:boxcolor=0x111318@0.85:boxborderw=8:x=(w-text_w)/2:y=10,fps=25,format=yuv420p",
         "-an", "-c:v", "libx264", "-crf", "18", str(TMP / "v3.mp4")])
    d3 = 75.0; add(TMP / "v3.mp4", d3, [(s["id"], s["cue"]) for s in N["segments"] if "cue" in s])
    d4 = D["s4_evidence"] + 1.0; anim(A / "evidence-diff.gif", d4, TMP / "v4.mp4"); add(TMP / "v4.mp4", d4, [("s4_evidence", 0.3)])
    split = 19.0; d5b = D["s5_metrics"] + 1.0 - split
    anim(A / "metrics.gif", split, TMP / "v5a.mp4"); anim(A / "latency.png", d5b, TMP / "v5b.mp4")
    add(TMP / "v5a.mp4", split, [("s5_metrics", 0.3)]); add(TMP / "v5b.mp4", d5b, [])
    d6 = D["s6_architecture"] + 1.0; anim(A / "architecture.gif", d6, TMP / "v6.mp4"); add(TMP / "v6.mp4", d6, [("s6_architecture", 0.3)])
    card(TMP / "c7.png", "Why we thought Zetaris was amazing", [
        "•  One CREATE LIGHTNING REST TABLE made a live federal API joinable",
        "    with our PostgreSQL register and a CSV file store",
        "•  levenshtein · regexp_extract_all · array_except inside federated SQL:",
        "    the whole change-detection rule became one Zetaris view",
        "•  48/48 verdicts identical to an independent Python control",
        "•  Agent: 3 connections + 4 client libraries  →  1 endpoint"],
        kicker="IN OUR OWN WORDS · 40–60 s SEGMENT", foot="Voiceover: synthetic voice (Microsoft neural TTS) reading the team's statement")
    t7 = t; d7 = D["s7_why"] + 2.0; still(TMP / "c7.png", d7, TMP / "v7.mp4"); add(TMP / "v7.mp4", d7, [("s7_why", 1.0)])
    card(TMP / "c8.png", "Open source, reproducible", [URL, "", "SQL views · data pipeline · blind evaluation · benchmark · this video",
         "Data: eCFR (U.S. Government work, public domain) · organisation and assessments are fictional"],
         kicker="REGULATION CHANGE SENTINEL", foot="Built with Zetaris, PostgreSQL, eCFR API · coded with Claude Code")
    d8 = D["s8_close"] + 2.5; still(TMP / "c8.png", d8, TMP / "v8.mp4"); add(TMP / "v8.mp4", d8, [("s8_close", 0.4)])

    (TMP / "list.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in segs))
    run(["-f", "concat", "-safe", "0", "-i", str(TMP / "list.txt"), "-c", "copy", str(TMP / "video.mp4")])
    ins = sum([["-i", str(p)] for p, _ in audio], [])
    flt = "".join(f"[{i}:a]adelay={int(o * 1000)}|{int(o * 1000)}[a{i}];" for i, (_, o) in enumerate(audio))
    flt += "".join(f"[a{i}]" for i in range(len(audio))) + f"amix=inputs={len(audio)}:normalize=0,apad,atrim=0:{t:.2f}[aout]"
    run([*ins, "-filter_complex", flt, "-map", "[aout]", "-c:a", "pcm_s16le", "-ar", "48000", str(TMP / "audio.wav")])
    # subtitles: shift each segment's SRT
    def ts(x):
        h, m = divmod(int(x), 3600); m, s = divmod(m, 60); return f"{h:02}:{m:02}:{s:02},{int(round((x % 1) * 1000)):03}"
    def parse(x):
        h, m, s = x.replace(",", ".").split(":"); return int(h) * 3600 + int(m) * 60 + float(s)
    cues = []
    for sid, off in srt_parts:
        for blk in (HERE / "audio" / f"{sid}.srt").read_text(encoding="utf-8").strip().split("\n\n"):
            ln = blk.strip().splitlines()
            a, b = [parse(v.strip()) for v in ln[1].split("-->")]
            cues.append((a + off, b + off, " ".join(ln[2:])))
    srt = "".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n" for i, (a, b, txt) in enumerate(cues, 1))
    (OUT / f"{NAME}.srt").write_text(srt, encoding="utf-8")
    sub = (OUT / f"{NAME}.srt").as_posix().replace(":", "\\:")
    style = "FontName=Segoe UI,FontSize=12,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,BorderStyle=4,Outline=0,Shadow=0,MarginV=10"
    run(["-i", str(TMP / "video.mp4"), "-i", str(TMP / "audio.wav"), "-i", str(OUT / f"{NAME}.srt"),
         "-vf", f"subtitles='{sub}':force_style='{style}'", "-map", "0:v", "-map", "1:a", "-map", "2:s",
         "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-c:s", "mov_text", "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", str(OUT / f"{NAME}.mp4")])
    meta = {"file": f"{NAME}.mp4", "duration_s": round(t, 2), "why_segment": {"start_s": round(t7 + 1.0, 2),
            "length_s": D["s7_why"]}, "live_segment": {"start_s": round(sum([d1, d2]), 2), "length_s": d3}}
    (OUT / "manifest.json").write_text(json.dumps(meta, indent=1)); print(meta)


if __name__ == "__main__":
    main()
