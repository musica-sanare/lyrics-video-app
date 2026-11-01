[Docs index](../en/README.md)

# Phase 4 acceptance: a preview of the video and design settings on the page

Status: accepted by the owner on 2026-11-01. Version 0.3.0.

Plan: [PHASE4_PLAN.md](PHASE4_PLAN.md). Machine: Apple M1 (8 cores), Python 3.13, Pillow 13.0.0,
audio-spectrum-app 0.5.0, FastAPI 0.162.0, uvicorn 0.54.0, tomlkit 0.15.2, gitleaks 8.30.1.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `f100ad2`, `53062c3` | Plan; approved with every recommendation (A1, B1, C1, Q1 to Q9) |
| 1. Preview video | `eac3e2d` | Preview video button on the `sync` page: the whole song at 960 × 540 and 15 fps from unsaved lines, played in step with the song, out-of-date marks |
| 1a. Test client | `5de06a0` | `httpx2` instead of `httpx`, which removes the deprecation warning carried over from Phase 2 |
| 2. Text faces and title box | `42fa2b5` | `font_face`, `bold`, `italic` for title, captions and credits; `title.panel` |
| 3. Design mode | `2488d45` | Design mode on the `sync` page: settings with live stills, font list, saving to the song file's `[design]` |
| 4. Owner's check | none | The owner tried the Design mode and the preview video (section 2) |
| 5. Acceptance | this commit | ADR-008, ADR-009, this report, version 0.3.0 |

## 2. The owner's results

- **Design mode and preview video.** The owner tried both on the owner's song and found how they work fine. The
  owner accepted the phase on that basis.
- **Not done yet.** The owner did not save a design to the song file or render a video with a changed design in this
  phase; the first such video is an open item (section 7).

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| A preview of the whole song with design, captions and spectrum is ready in less than a quarter of the song's length on an idle M1 | Met | 18.9 s to 19.6 s for the owner's 279.1 s song (7 %), even with other load on the machine (section 4) |
| The preview shows the same captions at the same times as the final video | Met by test | `test_the_preview_shows_the_captions_of_the_stills` (preview frames against stills of the same times; stills equal video frames since Phase 3). The owner has not yet compared a preview with a rendered video |
| A time corrected after watching the preview shows in the next preview and in the video | Met | By hand on a generated song: a changed line is marked, the next preview shows it; the video renders the saved timing (Phase 3) |
| The owner can set caption background color and opacity, title font, bold, italic and background color, and the same kinds of settings of the other parts on the page, and sees each change in the still at once (well under a second) | Met | The owner tried it (section 2); 0.13 s to 0.37 s per still after a change on the owner's song (section 4) |
| Saved settings are in the song file's `[design]`, only the changed keys, with comments and other sections kept; `still` and `render` use them | Met | `test_saving_a_design_named_by_a_key`, `test_saving_replaces_a_design_table_in_place`, `test_a_design_that_does_not_load_is_not_saved`, `test_saving_the_design_writes_the_song_file`; by hand on a generated song. Comments inside `[design]` are not kept (section 6) |
| Existing song files and built-in designs render exactly as before | Met | 24 frames of the built-in designs at 1080p (with and without letter spacing, four times each) were compared before and after milestones 2 and 3: identical. Not a stored test, since the pixels depend on the system fonts |
| The page writes only on Save, Render video and Preview video (the preview into a temporary folder removed at the end); the final render uses saved files only | Met | `test_the_preview_is_made_from_unsaved_lines`, `test_closing_the_session_removes_the_preview`, `test_no_design_is_saved_while_a_video_renders`, `test_rendering_needs_saved_timing`; by hand: Render video waits for Save of the timing and the design |
| Docs in English and Japanese, nothing private committed (no font paths, songs or lyrics) | Met | Translation hashes match; every commit's file list reviewed; section 5. The Mermaid diagrams changed in Phases 3 and 4 still need a look on GitHub (section 7) |

Test suite: 222 tests, all passing, with no warnings (181 at the end of Phase 3). The page was checked by hand on a
generated song in Japanese, English and Spanish: preview, Cancel, out-of-date marks, the Design mode's settings, font
list, reset and Save, and stopping the server (the preview folder is removed).

## 4. Measurements

On the 8-core M1, with other work running (load average 3 to 5).

Preview video of the owner's 279.1 s song (a 5000 × 3333 photo), 960 × 540 at 15 fps, H.264 `veryfast`, no audio:

| Run | Time | Share of the song | Size |
|---|---|---|---|
| 1 | 19.6 s | 7 % | 19.3 MB |
| 2 | 18.9 s | 7 % | 19.3 MB |

In the page, the preview video stays 20 ms to 30 ms behind the song's audio, steady over the song (under half a
preview frame); the page corrects it only beyond 0.1 s.

A still on the owner's song after a design change, measured in the server (drawing and PNG):

| Change | Time per still |
|---|---|
| None | 0.09 s |
| Title size | 0.13 s |
| Caption text color | 0.13 s to 0.23 s |
| Background dim (the photo is scaled again) | 0.37 s |

The plan estimated tens of milliseconds for a change that keeps the background. Every picture except the scaled
photo is drawn again, the frosted boxes and the caption included, so it takes about 0.1 s more. That is well under a
second, so `set_design` stays simple.

## 5. Repository safety

- `gitleaks git --redact -v .` over the whole history (32 commits) before this commit: no leaks found.
  `gitleaks dir --redact .` over the working tree, including the ignored `work/`: no leaks found.
- History searched for home paths: none. The only author is the owner's GitHub no-reply address.
- Tests use generated tones, images and made-up lyrics, and system fonts. The page was checked by hand on a generated
  song in a temporary folder. The owner's song, lyrics, photo, fonts and song file stay in `work/`; measurements on
  the owner's song record numbers only.
- One dependency was added (`tomlkit`, MIT license) and one replaced (`httpx2` for `httpx`, tests only), both from
  the local package cache.

## 6. Findings

- **The preview is quick enough to use often.** About 7 % of the song's length, so it can be made again after each
  round of corrections.
- **macOS lists some font file names decomposed.** Names such as ヒラギノ come back from the file system in NFD,
  while song files are typed in NFC. The font list normalizes paths to NFC, so the font a song file names is found in
  the list.
- **Faces of one collection can look alike.** The faces of Hiragino Sans W3 draw Latin text identically; Helvetica's
  collection (regular, bold, oblique) is used to test `font_face`.
- **Comments inside `[design]` are lost when the page saves.** `tomlkit` keeps the rest of the song file, comments
  included, but the page replaces the whole `[design]` table. The previous file is kept as `song.toml.bak`.
- **A design change costs more than estimated** (section 4), but stays well under a second.

## 7. Open items

- P4-1: The first video with a design set on the page: the owner saves a design, renders the song and compares the
  video with the preview. Not done in this phase (section 2).
- Named designs for other songs (plan C3): wanted by the owner, in a later phase.
- Spectrum settings on the page: wanted by the owner in a later phase, so that a video can be set up and rendered in
  this app alone. audio-spectrum-app's public API (`preset_schema`, `override_preset`, `preset_to_toml`,
  `save_user_preset`) is the starting point; anything missing is planned in its own repository.
- MusicXML draft timing and automatic alignment (the handoff's old Phase 4).
- Short full-size clips of the selected line (plan A2): only if the whole-song preview turns out not to be enough.
- The order of the four items above is decided when the next phase is planned.
- The Mermaid diagrams changed in Phases 3 and 4 (user guide overview and flowchart, architecture layers and sync
  page) need a look on GitHub after the next push.
