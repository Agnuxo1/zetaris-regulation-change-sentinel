"""Continuous live recording of the Zetaris UI running the Sentinel queries.
Login happens in a separate, unrecorded context; the recording starts signed in."""
import json, sys, time
from playwright.sync_api import sync_playwright
from common import CHROME, login

TAG = sys.argv[1] if len(sys.argv) > 1 else "take1"
Q = [
    ("federation", "SELECT 'PostgreSQL: compliance register' AS source, count(*) AS row_count FROM grants_pg.compliance_register\nUNION ALL SELECT 'File store: eCFR paragraphs', count(*) FROM ecfr_files.paragraphs\nUNION ALL SELECT 'REST: live eCFR versions', count(*) FROM ecfr_rest.part200_versions LATERAL VIEW explode(content_versions) t AS cv"),
    ("sources", "SELECT cv.identifier AS section, cv.amendment_date, cv.name\nFROM ecfr_rest.part200_versions\nLATERAL VIEW explode(content_versions) t AS cv\nWHERE cv.amendment_date = '2024-10-01'"),
    ("summary", "SELECT verdict, count(*) AS assessments\nFROM regsentinel.change_review\nGROUP BY verdict ORDER BY assessments DESC"),
    ("queue", "SELECT assessment_id, policy_area, section_id, facts_removed, facts_added, verdict\nFROM regsentinel.change_review\nWHERE verdict LIKE 'REVIEW%' ORDER BY assessment_id"),
]
events, t0 = [], None


def ev(name):
    events.append({"t": round(time.time() - t0, 2), "event": name}); print(events[-1], flush=True)


def type_sql(pg, sql):
    pg.click(".monaco-editor .view-lines"); pg.keyboard.press("Control+A"); pg.keyboard.press("Delete")
    for i in range(0, len(sql), 3):  # input events only: no shortcuts, no autocomplete acceptance
        pg.keyboard.insert_text(sql[i:i + 3]); pg.wait_for_timeout(28)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME); home = login(b)
    ctx = b.new_context(viewport={"width": 1600, "height": 900}, storage_state="state.json",
                        record_video_dir=f"video-{TAG}", record_video_size={"width": 1600, "height": 900})
    pg = ctx.new_page(); t0 = time.time(); ev("start")
    pg.goto(home, wait_until="networkidle"); pg.wait_for_timeout(1500)
    pg.get_by_text("SQL Workspace").first.click(); pg.wait_for_timeout(1500); ev("workspace")
    pg.get_by_text("File Source & API", exact=True).first.click(); pg.wait_for_timeout(1500)
    if not pg.get_by_text("grants_pg").count():
        pg.get_by_text("Database", exact=True).first.click(); pg.wait_for_timeout(1200)
    for name in ("ecfr_files", "ecfr_rest", "grants_pg"):
        loc = pg.get_by_text(name, exact=False)
        if loc.count():
            loc.first.hover(); pg.wait_for_timeout(1200)
    pg.screenshot(path=f"shot-{TAG}-sources.png")
    ev("sources_visible"); pg.wait_for_timeout(2500)
    pg.get_by_text("New Query").first.click(); pg.wait_for_timeout(2500)
    pg.mouse.move(1070, 597); pg.mouse.down(); pg.mouse.move(1070, 420, steps=12); pg.mouse.up(); pg.wait_for_timeout(800)
    ev("editor")
    for name, sql in Q:
        ev(f"type_{name}"); type_sql(pg, sql); pg.wait_for_timeout(700)
        ev(f"run_{name}"); n_before = pg.get_by_text("Total Count").count()
        pg.click("[data-testid=execute-btn]"); pg.mouse.move(900, 300)
        pg.wait_for_timeout(600)
        pg.wait_for_function("() => { const t = document.body.innerText; return t.includes('Success') && !t.includes('Executing query') && !/Running/.test(t); }", timeout=90000)
        pg.wait_for_timeout(3500); ev(f"result_{name}")
        pg.screenshot(path=f"shot-{TAG}-{name}.png"); pg.wait_for_timeout(3000)
        if name == "queue":
            for _ in range(4):
                nxt = pg.locator("button:has(svg.lucide-chevron-right)").last
                if nxt.count() and nxt.is_enabled():
                    nxt.click(); pg.wait_for_timeout(2200)
            pg.wait_for_timeout(1500); pg.screenshot(path=f"shot-{TAG}-queue-scrolled.png")
    ev("end"); video = pg.video.path(); ctx.close(); b.close()
json.dump({"video": str(video), "events": events, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
          open(f"events-{TAG}.json", "w"), indent=1)
print("video", video)
