[Docs index](../en/README.md)

# Phase 2 acceptance: timing of the lyrics

Status: accepted by the owner on 2026-11-01, with P2-1 open. Version 0.1.0.

Plan: [PHASE2_PLAN.md](PHASE2_PLAN.md). Machine: Apple M1, Python 3.13, Pillow 13.0.0, audio-spectrum-app 0.5.0,
FastAPI 0.162.0, uvicorn 0.54.0.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `4f5e399` | Approved plan (A1 local web page, B1 LRC file, C1 FastAPI as a normal dependency) |
| 1. Mock-up | `f7adf29` | The owner tried a mock-up of the tapping page (not committed); keys and multi-line shifting settled |
| 2. Captions by time | `756ed8d` | `timing.py`, the song file's `timing`, lead, fades, `crossfade` and `sequential`, `still` by time, 16-bit caption cache |
| 3. Tapping page | `e7670ad` | `lyrics-video sync`: server, tap and adjust page, exact stills, safe save, four page languages |
| 4. Architecture and acceptance | this commit | `ARCHITECTURE.md` in English and Japanese, `sequential` as the default transition, ADR-005 and ADR-006, this report |

## 2. The owner's decisions

- **`sequential` is the default transition** (2026-11-01). From stills of both transitions around a line change and
  a pause of the owner's song, with the spectrum on top: with `crossfade` the old and new texts overlap in the same
  place for about 0.1 s and neither reads well; with `sequential` they never overlap, at the cost of a moment with no
  caption between back-to-back lines. `crossfade` stays available as a design setting.
- **The page works as wished.** The owner timed part of a song with the page and found nothing to change in its
  handling.

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The owner times a whole song with the page in about the song's length plus a few minutes of corrections | Not checked | The owner timed 7 of 18 lines of a 279 s song and saved them; no usability problems were found, but the time for a whole song was not recorded (P2-1) |
| Stills at chosen moments show the right caption, entering and leaving as wished | Met | Stills of both transitions around a line change and a pause (in `work/`, not committed); the owner chose `sequential` (section 2). Tests: `test_with_timing_each_still_shows_the_caption_of_its_moment`, `test_lead_crossfade_and_fades_around_a_pause`, `test_sequential_fades_the_old_caption_out_before_the_new_one` |
| Times survive a round trip and a changed `lyrics.txt` keeps the times of unchanged lines | Met | `test_writing_and_a_round_trip`, `test_a_round_trip_keeps_the_times`, `test_merging_keeps_the_times_of_unchanged_lines`, `test_a_changed_lyrics_file_keeps_the_times_of_unchanged_lines` |
| Frames with a crossfade stay under 20 ms at 1080p (others as in Phase 1) | Met | Section 4 |
| The page cannot be driven by other web pages, and nothing is written without Save | Met | `test_api_requests_need_the_token`, `test_the_token_in_the_url_is_accepted_for_the_audio_only`, `test_foreign_hosts_are_refused`, `test_the_page_and_no_cross_origin_headers`; by hand in a browser: nothing written before Save, leaving with unsaved changes asks |
| Docs (including the architecture) in English and Japanese, nothing private committed | Met | Translation hashes match; every commit's file list reviewed; section 5 |

Test suite: 171 tests, all passing (101 at the end of Phase 1). The page itself was checked by hand on a generated
song: tapping, adjusting, undo, shifting all lines, setting a time to the playhead, saving with a backup, the list of
changed lyrics and the four languages.

## 4. Measurements

`tools/time_backdrop.py` on the owner's song file: 1920 × 1080, a 5000 × 3333 photo, 240 frames per state, mean time
per frame in one process. The crossfade column forces `crossfade`; with the default `sequential` two captions are
never blended, so its frames cost as much as a caption fading.

| Design | Prepare (once) | No caption | Caption | Caption fading | Crossfade | Credits fading |
|---|---|---|---|---|---|---|
| `classic` | 317 ms | 0.2 ms | 6.5 ms | 6.1 ms | 12.3 ms | 29.1 ms |
| `soft` (default) | 293 ms | 0.2 ms | 7.6 ms | 7.8 ms | 15.3 ms | 0.3 ms |
| `panel` | 297 ms | 0.2 ms | 3.2 ms | 3.3 ms | 6.4 ms | 0.6 ms |

Before the 16-bit caption cache (milestone 2), `soft` took 10.9 ms with a caption and 20.6 ms to 21.9 ms during a
crossfade. Converting each caption to 16-bit arrays once per appearance, and keeping only the last three per process,
brought every state under its target. `classic` credits fading (about 3 s of a song) stay at 27 ms to 34 ms, as in
Phase 1.

## 5. Repository safety

- `gitleaks git --redact -v .` (gitleaks 8.30.1) over the whole history (19 commits) before this commit: no leaks
  found. `gitleaks dir --redact .` over the working tree, including the ignored `work/`: no leaks found.
- History searched for home paths and e-mail addresses: none. The owner's song, lyrics, timing, photo, fonts and
  stills stay in `work/`; `*.lrc` is ignored.
- Tests use generated tones, images and made-up lyrics; the page was checked by hand on a generated song.

## 6. Findings

- **Exact stills while adjusting are cheap enough.** The page keeps one decoded song and one backdrop; a 1080p still
  takes about 90 ms on the owner's song (spectrum, backdrop and PNG), so it is redrawn whenever the song is paused
  and a time changes.
- **Lines without a time need a direct way in.** New lines from a changed lyrics file cannot be tapped in order, so
  adjust mode gained "set to the playhead" (`Enter`), which the plan did not list.
- **A song file can point to a missing song.** The owner's local song file still named an earlier song's audio and
  title; `sync` reports a missing audio file before serving, but nothing checks that the title matches.

## 7. Open items

- P2-1: Time a whole song with the page and record the time taken (the first acceptance criterion). The owner
  accepted Phase 2 with this open; it is done with the first whole video in Phase 3.
- Tests print a deprecation warning: Starlette asks for `httpx2` instead of `httpx` in its test client, as in
  audio-spectrum-app.
- `classic` credits fading take about 30 ms per 1080p frame; acceptable for about 3 s of a song, or to be cached like
  the captions if Phase 3 needs it.
- Next: Phase 3, the whole video in one step (`render_video` with `LyricsBackdrop`), CLI and page; the removal of
  `captions` and `compare` is planned there (plan Q8).
