[Docs index](../en/README.md)

# Phase 3 acceptance: the whole lyrics video in one step

Status: accepted by the owner on 2026-11-01. Version 0.2.0.

Plan: [PHASE3_PLAN.md](PHASE3_PLAN.md). Machine: Apple M1 (8 cores), Python 3.13, Pillow 13.0.0,
audio-spectrum-app 0.5.0, FastAPI 0.162.0, uvicorn 0.54.0, gitleaks 8.30.1.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `c5b66c5` | Plan; approved with every recommendation (A1, B1, C1, Q1 to Q8) |
| 1. Render command | `79743ec` | `lyrics-video render`: output rules, parts, progress, Ctrl+C, checks before any worker starts; measured render times |
| 2. Render from the page | `fbb9a5a` | Render video button on the `sync` page: saved timing only, progress, Cancel, Show in Finder, four languages |
| 3. First whole video | none | The owner timed a whole song on the page, rendered it and watched it (section 2) |
| 4. Remove caption images | `b374acd` | `captions`, `compare` and their song file sections removed; `separator` at the top level |
| 5. Acceptance | this commit | ADR-007, this report, version 0.2.0 |

## 2. The owner's results

- **Timing a whole song (P2-1).** The owner timed all 18 lines of the 279 s song (18 starts and 5 ends before pauses) by playing it once and pressing
  `Space` and `Enter` live; corrections took almost no time. The time spent is therefore about the song's length.
- **The first video replaces the iMovie workflow.** The owner rendered the song (`videos/song.mp4`, 132 MB) and
  watched the whole video: captions, title and credits were right. The caption image commands were then removed (milestone 4).
- **Render time on the owner's run.** About 5 minutes, with other load on the machine, against about 2.5 minutes
  measured on an idle machine (section 4).
- **Requests for the next phase** (section 7): a quick preview before rendering, to check the caption changes and fix
  times before the long render; and settings with a preview for the design, such as the caption background color
  and opacity, and the title's font, bold, italic and background.

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The owner times a whole song on the `sync` page in about the song's length plus a few minutes of corrections (P2-1) | Met | Section 2: one pass of the song, almost no corrections |
| One command turns the timed song into a 1920 × 1080 video with its audio, the right captions at the right moments, the title and the credits | Met | The owner watched the whole video (section 2); every measured video has 8374 frames at 1920 × 1080 and 279.1 s of AAC audio; `test_the_whole_video_with_its_audio` |
| The video's frames are the `still`s of the same times | Met | `test_the_frames_of_the_video_are_the_stills` (mean difference under 3 levels, from H.264's half-resolution colors); `test_several_workers_through_the_console_script` gives the same frames with two workers |
| A whole video renders in less time than the song lasts at 1080p30 | Met on an idle machine | 51 % to 55 % of the song's length warm, 69 % to 84 % on cold first runs (section 4); the owner's run under other load took about 5 minutes, slightly more than the song |
| Nothing is overwritten without `--overwrite` or a confirmation in the page; a cancelled or failed render leaves no file | Met | `test_refusals_before_any_work`, `test_a_cancelled_render_leaves_no_file`, `test_ctrl_c_exits_with_130`, `test_an_existing_video_is_replaced_only_when_asked`, `test_cancelling_a_render`; by hand: Cancel in the page and Ctrl+C on the server mid-render left the previous video and no partial file |
| The page renders only saved timing and keeps its local protections | Met | `test_rendering_needs_saved_timing`, `test_one_render_at_a_time_and_no_saving_while_it_runs`, `test_render_routes_need_the_token`; by hand: the button waits for Save |
| `captions` and `compare` are gone, and an old song file says clearly what to change | Met | `test_the_caption_image_commands_are_gone`, `test_removed_sections_are_named`; the owner's song file had no old sections and loads unchanged |
| Docs in English and Japanese, nothing private committed | Met | Translation hashes match; every commit's file list reviewed; section 5. The Mermaid diagrams changed in this phase still need a look on GitHub (section 7) |

Test suite: 181 tests, all passing (171 at the end of Phase 2; the caption image tests were removed with the
commands). The page was checked by hand on a generated song: the button disabled until Save, progress and time
left, the replace confirmation, Cancel, Show in Finder (button shown; opening the Finder covered by a test), and
stopping the server during a render.

## 4. Measurements

`lyrics-video render` on the owner's 279.1 s song (a 5000 × 3333 photo), 1920 × 1080 at 30 fps, H.264 CRF 18,
automatic workers, on an otherwise idle machine. Each video is about 125 MB.

| Design | First run | Second run (warm) |
|---|---|---|
| `soft` | 234.1 s (84 %) | 143.3 s (51 %) |
| `classic` | 191.6 s (69 %) | 149.3 s (54 %) |
| `panel` | 153.8 s (55 %) | not repeated |

The first runs were made one after the other and got faster each time, so the first `soft` run paid for a cold start.
Warm, every design renders in about half the song's length, close to audio-spectrum-app's 57 % over a still photo.
`classic` is not noticeably slower than the others, so its credits, which take about 30 ms per frame while they fade,
stay as they are (plan Q8). A render from the `sync` page of a 20 s generated song at 1280 × 720 took 4 s.

## 5. Repository safety

- `gitleaks git --redact -v .` over the whole history (25 commits) before this commit: no leaks found.
  `gitleaks dir --redact .` over the working tree, including the ignored `work/`: no leaks found.
- History searched for home paths and e-mail addresses: none; the only author is the owner's GitHub no-reply
  address. The owner's song, lyrics, timing, photo, fonts, stills and videos stay in `work/`.
- Tests use generated tones, images and made-up lyrics; the page was checked by hand on a generated song in a
  temporary folder.

## 6. Findings

- **Tapping live is enough.** With `Space` and `Enter` while the song plays once, a whole song needs almost no
  correction, so the adjust mode is a safety net rather than the main tool.
- **Render time depends on the machine's load.** Rendering uses every core but one; with other work running, a whole
  video can take longer than the song. `--workers` limits the processes if the machine is needed meanwhile.
- **The cold start is visible.** The first render after a while took up to about 60 % longer than the next ones.
- **The live preview is not the video.** While the song plays, the page shows a simple caption preview without the
  design or the spectrum; exact stills appear only when paused. The owner asked for a preview that shows the caption
  changes as in the video before rendering (section 7).

## 7. Open items

- P3-1: A quick preview before rendering, close enough to the video to check the caption changes, so times can be
  fixed before the long render (owner's request). For the next phase.
- P3-2: Settings with a preview for the design: caption background color and opacity, title font, bold, italic and
  background color, and similar settings of the other parts (owner's request). Some exist as design keys in the song
  file today (colors and opacities of the band, gradient and panel; title font, size and color); bold, italic and a
  title background do not. For the next phase.
- The handoff's Phase 4 (MusicXML draft timing, automatic alignment) moves after P3-1 and P3-2, which the owner wants
  first (2026-11-01).
- The Mermaid diagrams changed in this phase (user guide flowchart, architecture layers and sync page) need a look
  on GitHub after the next push.
- Tests still print Starlette's deprecation warning asking for `httpx2` instead of `httpx`.
