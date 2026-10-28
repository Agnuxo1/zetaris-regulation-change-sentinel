# Demo video pipeline

1. `record_zetaris_ui.py` — signs in to the Zetaris UI in an unrecorded browser context, then records one continuous session (Playwright video) that runs the four queries of `sql/30_queries.sql` style. Writes `events-<take>.json` with timestamps used to cue the narration.
2. `tts.py` — renders `narration.json` with a Microsoft neural voice (edge-tts) and per-sentence subtitles.
3. `build_video.py` — composes title cards, the live recording, the README figures and the narration into a 1920×1080 MP4 with burned-in and soft English subtitles.

The narration is synthetic; the "why Zetaris was amazing" segment is the team's own statement read by that voice.
