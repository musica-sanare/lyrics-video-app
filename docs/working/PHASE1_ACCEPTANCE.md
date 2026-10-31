[Docs index](../en/README.md)

# Phase 1 acceptance: the design of a lyrics video as configurable parts

Status: delivered on 2026-10-31, waiting for the owner's acceptance (要確認 P1-1). Version 0.1.0.

Plan: [PHASE1_PLAN.md](PHASE1_PLAN.md). Machine: Apple M1, Python 3.13, Pillow 13.0.0, audio-spectrum-app 0.5.0.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `7ef7a33` | Approved plan with the owner's answers |
| 1. Frame model | `cc3076e` | Parts and designs, layers drawn once per process, `LyricsBackdrop`, the `still` command, the `classic` design |
| 2. Designs | `8266ea1` | `soft` and `panel`, title letter spacing and rule, credits positions and panels, several designs and a comparison sheet in `still`, `tools/time_backdrop.py`, ADR-004 |
| 3. Choice | this commit | `soft` as the default design, the title as one line without a subtitle, this report |

## 2. The owner's choice

From stills over the owner's own photo, font and song (in `work/`, not committed), with the spectrum drawn on top:

- **`soft` is the default design**: the title small at the top left with a thin rule, captions left-aligned over a
  soft shade rising from the bottom, credits small at the bottom right. `classic` and `panel` stay available.
- **The title is one line.** Songs have no subtitle; anything like one is part of the title. The `subtitle` key and
  the title's `subtitle_size` and `gap` were removed (a change from the plan's frame model).
- **Credits are short**, for example a single `by <name>` line, at the bottom right. Details (music, lyrics,
  pictures) belong in the YouTube description. The song file's `credits` holds any lines; the example shows one.
- Captions stay as today in every design: left-aligned, at most two rows (plan Q9).

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The owner has chosen a default design from stills over their own background, font and song | Met | Section 2 |
| A still equals the video frame it stands for: backdrop and spectrum, at the same time | Met | `test_a_still_is_the_backdrop_with_the_spectrum_drawn_over_it`: with a silent song and no baseline the still equals the backdrop byte for byte; with sound the spectrum is drawn on top. The same backdrop object goes to `render_video` in Phase 3 |
| Backgrounds of any aspect ratio are covered and cropped, never stretched | Met | `test_backgrounds_cover_and_crop_without_stretching` (4:1, 1:4, 1:1 and 16:9 images keep a square square, with no empty borders); the owner's 3:2 photo in the stills |
| The backdrop is fast enough for Phase 3: under 10 ms per 1080p frame in a worker, or a plan to get there | Met | Section 4 |
| Docs in three languages, nothing private committed | Met | Translation hashes match; every commit's file list reviewed; section 5 |

Test suite: 101 tests, all passing (43 at the end of Phase 0).

## 4. Measurements

`tools/time_backdrop.py` on the owner's song file: 1920 × 1080, a 5000 × 3333 photo, 120 frames per state, mean time
per frame in one process (the render workers run the same code in parallel).

| Design | Prepare (once) | No caption | Caption | Caption fading | Credits fading |
|---|---|---|---|---|---|
| `classic` | 341 ms | 0.2 ms | 7.6 ms | 7.9 ms | 27.3 ms |
| `soft` (default) | 286 ms | 0.2 ms | 9.4 ms | 9.7 ms | 0.3 ms |
| `panel` | 280 ms | 0.2 ms | 4.1 ms | 4.1 ms | 0.5 ms |

Every design stays under 10 ms with a caption. `classic` darkens the whole frame behind its credits, so the frames
where the credits fade (about 3 s of a song) take 27 ms; fully shown credits are composed once. Each caption is drawn
once per worker the first time it appears (a few milliseconds per caption).

## 5. Repository safety

- `gitleaks git --redact -v .` (gitleaks 8.30.1) over the whole history before this commit: no leaks found.
- History and tracked files searched for home paths, e-mail addresses, the owner's song, photo and font names:
  none. Stills, the song, photo and fonts stay in `work/`.
- Built-in design files are tracked through a `.gitignore` exception for `src/lyrics_video/designs/*.toml`; every
  other `*.toml` except `pyproject.toml` and `*.example.toml` stays ignored.

## 6. Findings

- **Credits under the caption.** Credits are composed under the caption, so a caption shown during the credits stays
  bright, and fully shown credits cost nothing per frame.
- **Frosted panels are cheap** because the background is still: the blur is computed once per frame size.
- **The default spectrum overlaps the caption region slightly** in every design; the owner accepted that (plan Q6).

## 7. Open items

- 要確認 P1-1: accept Phase 1.
- An architecture document (planned to start in Phase 1 by the Phase 0 plan) is not written yet; it is proposed for
  Phase 2, when timing adds the next module chain.
- Next: Phase 2, timing of the lyrics (tap-to-sync and fine adjustment, stored next to the lyrics), planned in
  `PHASE2_PLAN.md`.
