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

## ADR-008: A low-resolution preview video of the whole song on the sync page

- Context: The owner wanted to check the caption changes as in the video, with the design and the spectrum, before
  the long render (P3-1, [Phase 4 plan](PHASE4_PLAN.md), option A). The page's live preview while playing showed the
  captions only; exact stills appeared only when paused.
- Decision:
  - "Preview video" renders the whole song from the page's current lines and design, saved or not, through the same
    `LyricsBackdrop` and `render_video` as the video, at most 960 × 540 and 15 fps, H.264 `veryfast` without audio
    (`prepare_preview`). The backdrop and the spectrum scale with the frame height.
  - It runs as a second kind of task in the page's `RenderTask` (one render at a time, video or preview), writes into
    a temporary folder of the session that is removed when the server stops, and replaces the previous preview only
    when done. `GET /api/preview/video` serves it and accepts the token in the URL, as the audio route does.
  - The page plays it muted while the song plays and keeps it within 0.1 s of the `<audio>` element, which stays the
    one clock. Lines changed since the preview, or a changed design, mark it out of date; it is not rebuilt
    automatically.
- Consequences: A preview of a 279 s song takes about 19 s (7 %) on the M1, so it can be made after each round of
  corrections. Text and thin lines are softer than at 1080p, and fades are less smooth at 15 fps. The rule that the
  page writes only on Save or Render video gains one exception, a temporary file outside the song's folder.
  Rejected: frames drawn live by the server while playing (too few per second, drifting, holding the session's
  `Preview`), drawing the design in the browser (a second drawing path), and short full-size clips per line for now
  (one line at a time; kept as an option if the whole-song preview is not enough).

## ADR-009: Design settings on the sync page, saved in the song file

- Context: The owner wanted to set the look of each part with a preview (P3-2, [Phase 4 plan](PHASE4_PLAN.md),
  options B and C), including bold, italic and a title background, which the designs could not express.
- Decision:
  - New design keys for the title, caption and credits: `font_face` (a face of a font collection), `bold` (a widened
    outline, 3 % of the font size) and `italic` (a 12° slant), synthetic because Japanese fonts have no italic and
    few weights; and `title.panel`, a plain or frosted box. `panel = false` turns off a box of the base design. The
    defaults draw the same pixels as before.
  - A Design mode on the `sync` page shows a chosen set of settings per part, with the still updated at each change.
    The page keeps the song file's overrides of a base design; stills and previews send them, and the server
    validates them as the song file would. `LyricsBackdrop.set_design` keeps the scaled background image when the
    background settings are unchanged.
  - Save writes only the changed settings into the song file's `[design]` table with `tomlkit`, which keeps the rest
    of the file and its comments; the new text is loaded before it is written, and the previous file is kept as
    `.bak`. Render video waits until the design is saved.
  - The font list holds the faces of the macOS font folders and of the folders of the song file's fonts, with paths
    in composed Unicode (NFC) as song files are typed.
- Consequences: One song file stays the single source for `still`, `render` and the page. A still after a design
  change takes 0.13 s to 0.37 s on the owner's song. Comments inside `[design]` are lost when the page saves. New
  settings in the Design mode need labels in four languages. Rejected: a separate design page (a second server and
  preview), and a separate design file per song (two files to keep together). Named designs for other songs and
  spectrum settings on the page are left to a later phase.

## ADR-010: The spectrum as part of the design, edited on the sync page

- Context: The owner wanted to set up and render a video in this app alone, without audio-spectrum-app's own page,
  and to reuse a whole look, spectrum included ([Phase 5 plan](PHASE5_PLAN.md), options A, B and D). The song file
  chose the spectrum with `[spectrum] preset` and `set`; designs had only `spectrum.set`.
- Decision:
  - A design's `spectrum` holds `preset` (a name, or a file relative to the song file), `foreground`, and the preset's
    own tables `analysis`, `look`, `fill` and `fx`, turned into `--set` overrides; `set` stays for old files.
  - One function, `config.spectrum_preset`, builds the preset for `still`, `render`, the preview and the page: the
    song file's `[spectrum] preset`, else the design's, else `default`; then the design's changes; then the song
    file's `set`. A song file that sets the spectrum itself therefore wins, and the page says so. `load_song` calls it
    once, so a wrong key fails at once with audio-spectrum-app's message and the song file's name.
  - The Design mode shows a chosen set of about 18 flat-look settings with labels in four languages; their defaults
    come from the chosen preset (`config.preset_values`). Analysis settings apply when the slider is released.
    Perspective presets hide the flat look's settings and gradients.
- Consequences: One design is the whole look of a video. audio-spectrum-app needed no change: only its public API
  (`load_preset`, `override_preset`, `preset_to_toml`, preset names) is used, and its page's labels are not copied.
  A look change shows in about 0.4 s, an analysis change in about 0.5 s. Rejected: the song file's `[spectrum]` only
  (named designs would not carry the spectrum), audio-spectrum-app user presets (another app's folder), every preset
  key from the schema (English only, hard to use), and `set` strings as the page's format (hard to read).

## ADR-011: Named designs in a user folder

- Context: The owner wanted to save a song's look and use it for other songs ([Phase 5 plan](PHASE5_PLAN.md),
  option C).
- Decision:
  - Named designs are TOML files in `~/Library/Application Support/lyrics-video/designs/` (`$LYRICS_VIDEO_DESIGN_DIR`
    when set, which tests use). `load_design` looks a name up among the built-in designs, then the named designs,
    then as a file relative to the song file.
  - "Save as design" on the page writes the whole look as it is on the page, saved or not (`config.save_user_design`):
    only keys that differ from the defaults, colors as `#RRGGBB`, font and preset files as absolute paths with `~`.
    Fonts are not copied. Replacing a design asks first and keeps a `.bak`; built-in names and names that look like
    paths are refused. The page then offers to use the design for the song.
  - "Show designs folder" opens the folder in the Finder for renaming and deleting.
- Consequences: Any song file, `still --design` and `render --design` use a named design like a built-in one. A
  named design depends on its font files staying where they are. Rejected: a `designs/` folder next to the songs
  (relative paths break when folders move).

## ADR-012: Starting from the Dock, with a start page

- Context: The page started only from a terminal inside the repository, one song per server. The owner wanted to
  start the app like any Mac app and move to the next song without commands ([Phase 6 plan](PHASE6_PLAN.md), option A).
- Decision:
  - `lyrics-video install-app` writes `~/Applications/Lyrics Video.app`: an `Info.plist` and a shell script that runs
    `uv run --project <repository> lyrics-video start` in the background, with the folders of `uv` and ffmpeg in
    `PATH` and output in `~/Library/Logs/lyrics-video.log`. It is made on each Mac and never committed.
  - `start` serves the page without a song. It records its port, token and process in
    `~/Library/Application Support/lyrics-video/server.json` (mode 0600); a second start opens the page of the
    recorded server if it answers.
  - One server holds one open song at a time (`Songs`); the start page lists the recent songs and opens others.
  - Quit on the page stops the server; it also stops after 10 minutes without requests while nothing renders, and the
    page pings every 30 s while open.
  - "How to use" on the page lists the steps from the Dock to Quit.
- Consequences: No terminal in everyday use, and code changes apply at the next start without installing again.
  Moving the repository or `uv` needs `install-app --overwrite`. The app has the default icon. Rejected: a
  `.command` file (opens Terminal), `uv tool install` alone (still a terminal), a native window (a new GUI
  dependency).

## ADR-013: New songs from files where they are

- Context: A new song meant copying the example song file and typing paths by hand. The owner keeps the audio,
  background image and lyrics in folders of their own choosing and has all three when a song starts (Phase 6 plan,
  options B to D).
- Decision:
  - "New song…" takes the three files from the Finder's own dialogs, which the server shows with `osascript`
    (`choose file`, `choose folder`) by kind through one route, `/api/choose`. Only one dialog opens at a time, and
    the page is covered until it closes.
  - The song file goes next to the audio as `<audio name>.toml` unless another folder is chosen, and never replaces
    one. It names the files where they are: relative inside its folder, else absolute with `~`. Nothing is copied.
  - The Song mode changes the title, credits, files and font with `tomlkit`, keeping comments and a `.bak`, then
    opens the song again. A song whose files are missing offers to choose them again.
  - "Save as design" writes the song's default font into the parts without a font, so a named design carries its
    fonts; the page remembers the last design and font for new songs.
- Consequences: Songs live wherever the owner wants and the video lands next to the song file. Moving or renaming a
  file breaks the song until it is chosen again on the page. Rejected: a library folder in Application Support
  (another fixed place), copying the files (duplicates large audio, two lyrics files drift apart).
