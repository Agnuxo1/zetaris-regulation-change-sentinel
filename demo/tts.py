import asyncio, json, pathlib, subprocess, imageio_ffmpeg, edge_tts
FF = imageio_ffmpeg.get_ffmpeg_exe(); N = json.load(open("narration.json", encoding="utf-8"))
out = pathlib.Path("audio"); out.mkdir(exist_ok=True)
async def one(seg):
    comm = edge_tts.Communicate(seg["text"], N["voice"], rate="+4%"); sub = edge_tts.SubMaker()
    with open(out / f"{seg['id']}.mp3", "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"): sub.feed(ch)
    (out / f"{seg['id']}.srt").write_text(sub.get_srt(), encoding="utf-8")
async def main():
    for s in N["segments"]: await one(s)
asyncio.run(main())
res = {}
for s in N["segments"]:
    p = subprocess.run([FF, "-i", str(out / f"{s['id']}.mp3"), "-f", "null", "-"], capture_output=True, text=True).stderr
    t = [l for l in p.splitlines() if "time=" in l][-1].split("time=")[1].split()[0]
    h, m, sec = t.split(":"); res[s["id"]] = round(int(h) * 3600 + int(m) * 60 + float(sec), 2)
json.dump(res, open("durations.json", "w"), indent=1); print(res, "total", round(sum(res.values()), 1))
