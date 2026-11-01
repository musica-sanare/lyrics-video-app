[Docs index](../en/README.md)

# Decisions

Architecture decision records. Each one states the context, the decision and its consequences. Background for the
first ones: [Handoff](HANDOFF.md) and the [Phase 0 plan](PHASE0_PLAN.md).

## ADR-001: A separate repository that draws under audio-spectrum-app's spectrum

- Context: The owner makes lyrics videos by stacking a background image, caption images and a spectrum video in
  iMovie. audio-spectrum-app is meant to stay a reusable component (its ADR-008) and gained an additive API for this
  purpose in its version 0.5.0 (its ADR-013).
- Decision: Lyrics, captions, title, credits and layout live in this repository. Videos are made by implementing
  audio-spectrum-app's `Backdrop` (a picklable object returning the picture under the spectrum for frame `n` at time
  `n / fps`) and calling `render_video`, which handles sync, worker processes, progress, cancellation, parts of
  songs, audio and safe output. Only its public API (`audio_spectrum`) is used. It is a path dependency
  (`../audio-spectrum-app`, editable, `>=0.5.0`) while both repositories change.
- Consequences: One render path and one sync invariant for both apps; previews (`Preview.frames`) equal video
  frames. A checkout needs audio-spectrum-app next to it. Changes needed there are planned in its own workspace,
  never made from here. Rejected: lyrics features inside audio-spectrum-app; a second render loop on its internals.
- Update (2026-10-31, [Phase 0 acceptance](PHASE0_ACCEPTANCE.md) P0-3): when the repositories are made public, the
  path dependency is replaced by a Git dependency on a tag of audio-spectrum-app (for example
  `git+https://github.com/musica-sanare/audio-spectrum-app@v0.5.0`), so `uv sync` alone installs it.
  audio-spectrum-app is made public first or together with this repository, and the README links to it. Rejected: a
  Git submodule (more steps to clone and update, nothing gained over a pinned tag) and a PyPI release (not needed
  for now).

## ADR-002: Pillow for the caption PNGs

- Context: The old caption script (2022) uses Pillow and `ImageDraw.textsize`, removed in Pillow 10. The caption
  PNGs must keep working in iMovie until this app makes whole videos. Skia is available through audio-spectrum-app.
- Decision: The caption PNGs are drawn with Pillow, with the old fitting and layout rules and `textbbox` in place
  of `textsize`. A check with Pillow 13.0.0 gave the same font size and layout as the old output, with glyphs at most
  about 1 px apart ([Phase 0 plan](PHASE0_PLAN.md), "Feasibility check"). Text drawing stays in one module.
- Consequences: Pillow is a dependency next to Skia. Skia's metrics would have changed sizes and positions. Which
  library draws captions inside videos is decided in Phase 1 with the caption design.
- Update (2026-11-01, [Phase 3 plan](PHASE3_PLAN.md) Q5 and milestone 4): superseded for the caption PNGs. The
  `captions` and `compare` commands and the song file's `[captions]` and `[compare]` sections were removed once the
  first whole video replaced the iMovie workflow; old song files with those sections stop with an error that names
  them, and `separator` moved to the top level. The old fitting and layout rules stay in `caption_image.py` for the
  `classic` caption band (ADR-004).

## ADR-003: One TOML file per song; the old lyrics format

- Context: The old script reads one TOML file for all settings and a lyrics text file with one caption per line and
  `;` between two rows. Timing does not exist yet (Phase 2).
- Decision: Each song has one TOML file, validated with pydantic, with paths relative to it and `~` expanded; later
  phases add sections to the same file. The lyrics file keeps the old format. Colors are `#RRGGBB` or a path to an
  image whose center pixel is used, so old sample images still work. Only `*.example.toml` files are committed.
- Consequences: Settings shared by songs are repeated for now; shared defaults can be added later. The timing format
  is chosen in Phase 2 (ADR-005).

## ADR-004: Text for video frames drawn with Pillow, composed in NumPy in the render workers

- Context: ADR-002 left open which library draws text inside videos. The backdrop runs in audio-spectrum-app's
  worker processes once per frame; Phase 1 needed a title, captions in three styles (band, gradient, frosted panel)
  and credits ([Phase 1 plan](PHASE1_PLAN.md), option B).
- Decision: Pillow draws every text layer once per process and frame size, as a coverage mask colored afterwards
  (straight-alpha RGBA, with optional blurred shadows). The background and title are composed once; the frosted
  panel blurs that still picture once. Per frame, NumPy blends only the caption's layer (and the credits while they
  fade) over a copy of the cached picture. Captions keep today's rules (left-aligned, up to two rows) behind an
  `align` setting that can grow.
- Consequences: Captions in videos use the same text engine and metrics as the caption PNGs. Measured on an M1 at
  1080p with a 5000 × 3333 photo (`tools/time_backdrop.py`): a frame with a caption takes 4.0 ms (panel), 7.6 ms
  (classic) and 9.4 ms (soft), under the 10 ms target; frames without a caption 0.2 ms; credits fading in or out
  1 ms to 2 ms, except 27 ms for designs that darken the whole frame (classic), for about 3 s of a song. Rejected for
  now: Skia for text (different metrics from the caption PNGs; kept as the fallback if a later design is too slow).

## ADR-005: Timing in an LRC file; captions placed by sung times and design settings

- Context: ADR-003 left the timing format to Phase 2. Captions need start times, ends where the singing pauses, a
  little lead and short fades; the owner's songs often pause ([Phase 2 plan](PHASE2_PLAN.md), options B and Q2 to Q4).
- Decision:
  - Times live in an LRC file next to the lyrics (`timing = "lyrics.lrc"` in the song file): `[mm:ss.xx]` and the
    caption per line, a time with no text ending the caption above it, lines without a time kept as not timed yet.
    Times are the sung times, written to the hundredth of a second.
  - How captions enter and leave is a design setting, so it can change without timing again: `lead_seconds` (0.2),
    `fade_seconds` (0.3) and `transition`. The default transition is `sequential` (the old caption fades out before
    the new one fades in), chosen by the owner from stills of both on 2026-11-01 because the two texts never
    overlap; `crossfade` stays available.
  - A changed lyrics file is merged in order with the timing: unchanged lines keep their times, new lines have none.
- Consequences: The text exists twice (lyrics file and LRC) once a song is timed; `still` reads the LRC. At most two
  captions are blended at once; each process keeps the last three captions as 16-bit arrays so a crossfade frame stays
  under 20 ms at 1080p. Rejected: times by line index in JSON or TOML (an added line shifts every later time), times
  inside the lyrics file (breaks the old format).

## ADR-006: The sync page as a local web page

- Context: Tapping needs exact times from the audio's own clock, a waveform and exact stills
  ([Phase 2 plan](PHASE2_PLAN.md), options A and C). audio-spectrum-app's GUI (its ADR-012) already solved the same
  problems.
- Decision: `lyrics-video sync` serves a plain HTML, CSS and JavaScript page from FastAPI and uvicorn, which are
  normal dependencies. The server listens on `127.0.0.1` only, refuses foreign `Host` headers and API requests without
  the per-session token, accepts the token in the URL for the audio route only (an `<audio>` element cannot send
  headers), and sends no cross-origin headers. Stills go through one `Preview` and one `LyricsBackdrop` per session.
  Edits stay in the page until Save, which writes the LRC through a temporary file and keeps a `.bak` copy. Page texts
  in Japanese, English, Spanish and French.
- Consequences: The page is checked by hand; the server is tested with FastAPI's test client. The keys were settled
  with a mock-up first (`Space` start, `Enter` end, `Backspace` undo); setting a time to the playhead was added for
  lines without a time. Rejected: a terminal tool (unknown player delay, no waveform) and writing times by hand.

## ADR-007: Whole videos through `render_video`, from the command and from the sync page

- Context: Phase 3 had to turn a timed song into the finished video in one step and replace the iMovie workflow
  ([Phase 3 plan](PHASE3_PLAN.md), options A to C). audio-spectrum-app's `render_video` already handles sync, worker
  processes, parts of songs, audio, safe output, progress and cancellation for a backdrop (ADR-001).
- Decision:
  - `lyrics-video render` builds `LyricsBackdrop` and passes it to `render_video` in the same process (A1).
    `prepare_render` first does everything that can fail quickly: the song file, the timing, an existing output, the
    times against the song's duration and the backdrop's `prepare`, so a missing image or font fails before any
    worker starts.
  - The video goes to `videos/<song file name>.mp4` next to the song file; a part adds its times
    (`song_60s-75s.mp4`); `--output` chooses another file (B1). An existing video is replaced only with
    `--overwrite`, or after a confirmation in the page.
  - H.264 with CRF 18 by default (no chroma keying is needed, unlike audio-spectrum-app's 14); `--codec prores` and
    `--crf` for other uses. Lines without a time are listed in a warning and left out.
  - Ctrl+C and SIGTERM interrupt the render, which leaves no file; the command exits with 130.
  - The sync page renders the saved timing file only, one render at a time, in a background thread with progress,
    Cancel and Show in Finder (C1). Save is refused while it runs; stopping the server cancels the render and waits
    for it.
- Consequences: Stills and videos share one drawing path, so a still is the frame of the video (up to H.264
  compression). The song is decoded twice per render (once for its duration), about a second. A whole 279 s video
  renders in about half the song's length on an idle M1; with other load on the machine it can take longer than the
  song. Rejected: overlaying a backdrop video and a spectrum video with ffmpeg (two encodes and a second sync path)
  and running audio-spectrum-app's CLI as a subprocess (it cannot take a backdrop).
