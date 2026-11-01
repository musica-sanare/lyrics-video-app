[Docs index](../en/README.md)

# Phase 3 plan: the whole lyrics video in one step

Status: proposed on 2026-11-01, waiting for the owner's approval. The questions are in the last section.

## Goal

Turn a timed song into the finished lyrics video with one command, and replace the iMovie workflow:

1. A `render` command: the song file in, a 1920 × 1080 video with the song's audio out. The backdrop of Phases 1 and
   2 (background, title, captions by time, credits) is passed to audio-spectrum-app's `render_video`, which draws the
   spectrum on top (ADR-001).
2. Safe output, parts of songs, progress and cancellation, as in audio-spectrum-app.
3. A render started from the `sync` page, so a song can be timed and rendered in one place.
4. The first whole video of the owner's song, with the whole song timed on the `sync` page (P2-1).
5. The removal of the caption image commands `captions` and `compare`, once the first video replaces the iMovie
   workflow (Phase 2 plan Q8).

Not in this phase: MusicXML drafts and automatic alignment (Phase 4), a page for designs or spectrum settings, other
output sizes than the song file's `[video]`.

Inputs: [Handoff](HANDOFF.md) §4 and §5, [Architecture](../en/ARCHITECTURE.md), [Decisions](DECISIONS.md) ADR-001
to ADR-006, [Phase 2 acceptance](PHASE2_ACCEPTANCE.md) section 7, and audio-spectrum-app's embedding guide (its
`docs/en/EMBEDDING.md` §2: `RenderJob`, `render_video`, backdrops).

## What audio-spectrum-app already does

`render_video(RenderJob(...), progress, cancel)` covers most of a render; this app only builds the job.

| Need | Provided by `render_video` | Left to this app |
|---|---|---|
| Frames in sync with the audio | Frame `n` at `n / fps`; the backdrop gets the whole song's index and time, also for a part | Nothing |
| Worker processes | `workers` (0 = one per core minus one); the backdrop is pickled to each worker | Keep the backdrop picklable (already tested) |
| Parts of songs | `start`, `duration`; frames equal the full video's, audio cut to match | Options and file names |
| Safe output | Temporary file and rename; `OutputExistsError` without `overwrite`; no file after a failure or `Cancelled` | Check before decoding, so an existing video fails at once |
| Progress, cancellation | `progress(done, total)`, `cancel()` checked per frame | Show progress; turn Ctrl+C into `cancel` |
| Audio, encoding | H.264 with AAC 320k (`.mp4`) or ProRes (`.mov`); `EncodeSettings.crf` | Choose the defaults (Q4) |
| Errors | `AudioSpectrumError` subclasses, `BackdropError` when the backdrop fails | Turn them into this app's messages, as `still` does |

A transparent background cannot be combined with a backdrop, and none is needed: the video is complete.

## Options

### A. How a whole video is made

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. A `render` command that builds `LyricsBackdrop` and calls `render_video` in this process | One render path for stills and videos; everything audio-spectrum-app handles (sync, workers, safe output, parts) comes for free; matches ADR-001 | The song is decoded twice (once here for its duration, once in `render_video`), about a second | **Recommended** |
| A2. Render a backdrop-only video, then lay audio-spectrum-app's spectrum video over it with ffmpeg | No Python API needed | Two encodes (quality loss, twice the time), keying again, a second sync path; what Phase 1 and 2 avoided | Not recommended |
| A3. Run audio-spectrum-app's CLI as a subprocess | Isolated process | The CLI cannot take a backdrop; would need a change there for nothing gained | Not recommended |

### B. Where the video goes

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. `videos/<song file name>.mp4` next to the song file, like `stills/`; a part adds its times (`song_60s-75s.mp4`); `--output` chooses another file | Every output of a song in one folder; nothing to configure | One more folder per song | **Recommended** |
| B2. `<song file name>.mp4` right next to the song file | Easy to find | Mixed with the inputs (song, image, lyrics) | Not recommended |
| B3. An `output` setting in the song file | Fixed per song | One more setting; `--output` covers the rare case | Not now |

### C. Rendering from the `sync` page

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. A "Render video" button on the `sync` page: renders the saved timing in a background thread, with progress, cancel and "Show in Finder", like audio-spectrum-app's GUI | Time, check and render without leaving the page; the handoff's "CLI and GUI" | More server code and page texts in four languages | **Recommended**, after the command |
| C2. The command only in this phase | Least work | Switching to the terminal after each timing session | Fallback if Q6 says so |
| C3. A separate render page | Room for future settings | A second page for one button | Not now |

## Design

### The `render` command

```bash
uv run lyrics-video render work/my-song/song.toml
# writes work/my-song/videos/song.mp4: 1920 x 1080, the song's fps, the song's audio
uv run lyrics-video render work/my-song/song.toml --start 60 --duration 15
# writes work/my-song/videos/song_60s-75s.mp4, the same frames as the whole video at those times
```

| Option | Default | Meaning |
|---|---|---|
| `SONG` | | The song file (TOML) |
| `--output FILE` | `videos/<song file name>.mp4` | Another output file (`.mp4` for H.264, `.mov` for ProRes) |
| `--overwrite` | off | Replace an existing video; without it nothing is decoded or drawn |
| `--start SECONDS`, `--duration SECONDS` | whole song | Render a part, as audio-spectrum-app's options |
| `--design NAME` | the song file's | Another design, as for `still` (one name) |
| `--workers N` | 0 (automatic) | Render processes; 1 renders in this process |
| `--codec`, `--crf` | `h264`, see Q4 | Passed to `EncodeSettings` |

Steps, so that every mistake shows before the long part starts:

1. Load the song file, design and timing (as `still`). Refuse without `audio`; without `timing`, refuse too: a whole
   video with one fixed caption makes no sense (Q3 covers lines that are not timed yet).
2. Refuse an existing output without `--overwrite`.
3. Decode the song once with `Preview` for its duration; check that the times are inside the song; build the
   captions and `LyricsBackdrop`; call `prepare(width, height)` in this process, so a missing image or font fails
   before any worker starts.
4. Print a summary: song title, audio file, design, timed lines (and lines without a time), length, output. A song
   file that still names another song's audio or title (Phase 2 finding) is then visible at once.
5. `render_video(RenderJob(..., backdrop=backdrop))` with the spectrum preset and overrides as in `still`.
6. Print the output path, the time taken and its share of the song's length.

The command is a console script, so worker processes re-import a module that has the `__main__` guard
(audio-spectrum-app's own CLI works the same way). A test renders with two workers to keep it so.

### Progress and cancellation

- Progress on stderr, one line updated in place: percent, frames, elapsed time and an estimate of the time left,
  at most about four times a second. Plain lines when stderr is not a terminal.
- Ctrl+C and SIGTERM set a flag that `cancel` returns, so `render_video` stops its workers and removes the temporary
  file; the command prints "cancelled" and exits with 130, as audio-spectrum-app does.
- Exit codes: 0 done, 1 failed (including an existing output), 2 usage, 130 cancelled.

### Rendering from the `sync` page (C1)

- `SyncSession` gains one `RenderTask` (one render at a time, in a background thread), modeled on audio-spectrum-app's
  GUI but written here: `POST /api/render` starts it, `GET /api/render` reports state and progress, `POST
  /api/render/cancel` cancels it. The same token and host checks apply.
- It renders the saved timing file, never the page's unsaved edits: the button is disabled while there are unsaved
  changes, so the video always matches a file on disk.
- Output as the command's default (B1). An existing video asks in the page before it is replaced.
- While a render runs, stills still work (they use the session's `Preview` in the server thread; the render runs
  in its own processes); Save is disabled so the timing cannot change under the render.
- Stopping the server with Ctrl+C cancels a running render and waits for it, so no temporary file is left.
- "Show in Finder" selects the video (`open -R`, only for the path the server wrote).
- New page texts in Japanese, English, Spanish and French; the existing test keeps the message files complete.

### Removing `captions` and `compare`

Done only after the owner confirms that the first whole video replaces the iMovie workflow (milestone 4).

| Removed | Kept |
|---|---|
| Commands `captions` and `compare`; `captions.py` (its `Written` moves to `output.py`) | `caption_image.py` text fitting and `fonts.load_font`: the caption layers of videos use them |
| `fonts.collect_fonts`, `font_labels`; `tools/compare_images.py` | `contact_sheet.py`: the `still` comparison sheet uses it |
| Song file sections `[captions]` and `[compare]`; the caption PNG settings in `CaptionLook` | The row separator `;`, which moves to a top-level `separator` setting |
| User guide sections on caption images and on moving from the old script; their tests | ADR-002 stays as history, marked superseded |

Song files are validated strictly (unknown keys are errors), so an old song file with `[captions]` would stop
loading. Recommended: a clear error that names the section, says it is no longer used and how to move `separator`
(Q5). The example song file and the owner's song file in `work/` are updated by hand.

### `classic` credits

Credits fading in `classic` take about 30 ms per 1080p frame, because the whole frame is darkened. They fade for
1.5 s at the start and at the end: about 90 frames, roughly 3 s of worker time per song, shared by all workers. That
is under 1 % of a render, so the plan leaves it as it is and checks it in the measurements of milestone 1. If a
whole `classic` render turns out noticeably slower than `soft`, the faded credits are cached like the captions.

### Performance

Expected at 1080p30 on the M1: the spectrum takes about 20 ms per frame and the backdrop about 8 ms with a caption,
in each worker. audio-spectrum-app rendered a 317.7 s song over a still photo in 182.1 s (57 %). The target is a
whole video in less time than the song lasts; milestone 1 measures each built-in design on the owner's song and
`tools/time_backdrop.py` stays the tool for the backdrop alone.

### Tests

Generated tones, images and made-up lyrics; system fonts, skipped where missing; video tests skipped without ffmpeg.

- Render a few seconds of a generated song with a timing file: the video exists, has the expected frame count, size
  and audio length, and a decoded frame is close to the `still` of the same time (H.264 is lossy, so with a tolerance;
  exact equality is already tested in audio-spectrum-app).
- With two workers: the same result (the backdrop works when pickled to workers through the console script).
- Parts: `--start` and `--duration` give the expected name, length and first frame.
- Refusals before any work: an existing output without `--overwrite`, no `audio`, no `timing`, times beyond the song,
  a missing font or image (fails in `prepare`, before `render_video`).
- Cancellation: a `cancel` that turns true leaves no output and no temporary file; the command exits with 130.
- Page (FastAPI's test client): start, status, cancel, refusing a second render, refusing to replace an existing
  video unless asked, the token on every render route.

### Documentation

- User guide (English and Japanese): the `render` command, rendering from the `sync` page, the whole way from a new
  song to a video; later without `captions` and `compare`.
- Architecture (English and Japanese): `render` in the layer diagram, the way from a song file to a video, the
  render task of the page; "Whole videos" leaves the table of features to come.
- ADR-007: whole videos (A1, B1, C1, output and cancellation rules). ADR-002 marked superseded when the caption
  images are removed.
- README: status and the quick start end with a video.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 3 plan` | This plan |
| 1. Render command | `feat: render the whole lyrics video` | `render` with output rules, parts, progress, cancellation; tests; user guide and architecture; measured render times per design |
| 2. Render from the page | `feat: render videos from the sync page` | Render task and routes, button, progress, cancel, "Show in Finder", page texts in four languages; tests; user guide |
| 3. First whole video | none | The owner times the whole song on the `sync` page and records the time (P2-1), renders it, and checks the video; results go into the acceptance report |
| 4. Remove caption images | `refactor: remove the caption image commands` | After the owner's confirmation: `captions`, `compare` and their settings removed, `separator` moved, docs and example song file updated |
| 5. Acceptance | `docs: accept Phase 3` | ADR-007, `PHASE3_ACCEPTANCE.md`, version 0.2.0 |

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| The owner times a whole song on the `sync` page in about the song's length plus a few minutes of corrections (P2-1) | The owner tries it; the time spent is recorded |
| One command turns the timed song into a 1920 × 1080 video with its audio, the right captions at the right moments, the title and the credits | The owner watches the whole video; frame count and audio length checked |
| The video's frames are the `still`s of the same times | Test with a tolerance for H.264 |
| A whole video renders in less time than the song lasts at 1080p30 | Measured on the owner's song, each built-in design |
| Nothing is overwritten without `--overwrite` or a confirmation in the page; a cancelled or failed render leaves no file | Tests; by hand with Ctrl+C and the page's Cancel |
| The page renders only saved timing and keeps its local protections | Server tests; by hand |
| `captions` and `compare` are gone, and an old song file says clearly what to change | Tests; the owner's song file updated |
| Docs in English and Japanese, nothing private committed | Hash check, file review, `gitleaks` |

## Questions for the owner

- Q1. Options A to C: are the recommendations (A1 a `render` command on `render_video`, B1 `videos/` next to the song
  file, C1 a render button on the `sync` page after the command) fine?
- Q2. File name: is `videos/<song file name>.mp4` (for example `videos/song.mp4`) fine, or should the name come from
  the song's title (which can contain characters that are awkward in file names)?
- Q3. Lines without a time: when the timing file still has lines without a time, should `render` refuse (safer for
  the final video) or warn and render without them (handy for a draft)? Recommended: warn, list the lines, render.
- Q4. Quality: audio-spectrum-app's H.264 default (CRF 14) is chosen for clean chroma keying, which this video does
  not need. For YouTube uploads, CRF 18 looks the same and gives smaller files. Recommended: CRF 18 by default, with
  `--crf` and `--codec prores` for other uses. Fine?
- Q5. Old song files after the removal of `captions` and `compare`: a clear error that names the sections to delete
  (recommended), or silently ignore them?
- Q6. The render button on the `sync` page: wanted in this phase (recommended), later, or not at all?
- Q7. The first whole video (P2-1): which song? The song file in `work/design/` still names an earlier song's title;
  please correct it (or put the song for the first video in a new folder) and time all its lines on the `sync` page,
  recording how long it took.
- Q8. `classic` credits fading at about 30 ms per frame: leave them as they are unless the measured whole render
  shows a real difference (recommended)?
