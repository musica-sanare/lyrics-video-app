English | [日本語](../ja/ARCHITECTURE.md) · [Docs index](README.md)

# Architecture

How lyrics-video-app is built: its layers, how a song file becomes a frame, the rules every change must keep, where
time goes, and where new features fit. It is for anyone changing the code. To use the app, see the
[User guide](USER_GUIDE.md); for setup and tests, see [Development](DEVELOPMENT.md).

## 1. Layers

The app has four layers. Each one uses only the layers below it, and audio-spectrum-app is reached only through its
public API (`audio_spectrum`).

```mermaid
flowchart TB
  subgraph commands["Commands and the page"]
    cli["cli.py: start, sync, still, render, install-app"]
    web["web/: server and sync page"]
  end
  subgraph frames["Frames"]
    still["still.py, render.py"]
    backdrop["backdrop.py: LyricsBackdrop"]
    layers["layers.py: pictures drawn once"]
  end
  subgraph inputs["Song and designs"]
    config["config.py: song file"]
    design["design.py and designs/*.toml"]
    text["lyrics.py, timing.py"]
  end
  spectrum["audio-spectrum-app: Preview, render_stills, render_video"]
  commands --> frames
  commands --> inputs
  frames --> inputs
  frames --> spectrum
```

| Layer | Modules | Responsibility |
|---|---|---|
| Song and designs | `config.py`, `design.py`, `designs/*.toml`, `lyrics.py`, `timing.py`, `errors.py` | Read and validate the song file, the design with its overrides, the lyrics file and the timing file (LRC). Paths are resolved against the song file |
| Frames | `layers.py`, `backdrop.py`, `still.py`, `render.py` | Draw the parts of a frame (background, title, captions, credits), compose them by time under the spectrum, and hand them to audio-spectrum-app for stills and videos |
| audio-spectrum-app | `audio_spectrum` (another repository) | Decode the song, analyse it and draw the spectrum over this app's backdrop, for stills and videos |
| Commands and the page | `cli.py`, `web/`, `app_files.py`, `app_bundle.py`, `app_icon.py` | Turn user actions into calls of the layers below, and write files; keep the app's own files and its app bundle |

Two helpers of the frames layer come from the caption images of the old workflow, which were removed in version 0.2.0:
`caption_image.py` draws the `classic` caption band with the old script's rules, and `contact_sheet.py` builds the
comparison sheet of `still`. `fonts.py` opens font files for both.

## 2. From a song file to a still

A still is the frame of the video at a time. `still` and the sync page build it the same way:

```mermaid
sequenceDiagram
  participant C as still or sync
  participant S as config, timing
  participant B as LyricsBackdrop
  participant P as audio-spectrum-app Preview
  C->>S: load the song file, design and timing
  S-->>C: Song, TimedLines
  C->>P: decode the song
  C->>B: captions by time, duration
  C->>B: prepare(width, height)
  C->>P: frames(preset, times, backdrop)
  P->>B: frame(index, index / fps)
  B-->>P: RGB picture under the spectrum
  P-->>C: the frame with the spectrum on top
```

1. `config.load_song` reads the song file and resolves the design (a built-in name, a named design in the user folder,
   or a file, with the song file's `[design]` overrides merged over it). `config.spectrum_preset` builds the spectrum's
   preset from the song file and the design; `still`, `render`, the preview and the page all use it, and `load_song`
   calls it once so a wrong preset key fails at once.
2. `timing.read_lrc` reads the timing file; `backdrop.timed_captions` turns its lines into `TimedCaption`s. A caption
   ends at a pause, at the next caption's start or at the end of the song.
3. `LyricsBackdrop` gets the design, the captions and the song's duration. `prepare` draws everything that never
   changes, so missing files or fonts fail before any frame.
4. audio-spectrum-app calls `backdrop.frame(index, seconds, width, height)` for each frame and draws the spectrum
   over the returned picture.

### Whole videos

`render` builds the same backdrop and passes it to audio-spectrum-app's `render_video` (`render.py`):

1. `prepare_render` does everything that can fail quickly, in this process: it loads the song file and the timing,
   refuses an existing output, decodes the song once for its duration, checks the times and calls `prepare`, so a
   missing image or font fails before any worker starts. It returns the `RenderJob` and a summary.
2. `render` calls `render_video` with that job. audio-spectrum-app pickles the backdrop to its worker processes, calls
   `frame` there for each frame of the whole song (also for a part, from `start`), draws the spectrum on top and
   encodes the video with the audio through a temporary file.

A still is therefore the same picture as the video frame it stands for (up to H.264 compression). Ctrl+C interrupts
`render_video`, which stops its workers and removes the temporary file.

### Captions by time

The design's `lead_seconds`, `fade_seconds` and `transition` turn sung times into a window per caption (see
`caption_windows`):

- A caption starts to appear `lead` before it is sung and fades in over `fade`.
- Between captions sung back to back, `crossfade` fades the old one out while the new one fades in; `sequential`
  fades it out before the new one starts.
- At a pause, the caption fades out after its end. The last caption is gone at the end of the song.
- A window never reaches the start of the caption after next, so at most two captions are blended at once.

The sync page computes the same windows in JavaScript for its simple live preview while the song plays. Its stills and
its preview video come from the server and are drawn by `LyricsBackdrop`.

### The sync page

```mermaid
flowchart LR
  page["Page in the browser"]
  server["web/app.py on 127.0.0.1"]
  files["lyrics.txt, lyrics.lrc, song.toml, song"]
  page -->|"GET /api/songs, POST /api/songs/open, POST /api/quit"| server
  page -->|"GET /api/song"| server
  page -->|"GET /api/audio (ranges)"| server
  page -->|"POST /api/still"| server
  page -->|"POST /api/timing, POST /api/design (Save)"| server
  page -->|"GET /api/fonts"| server
  page -->|"POST /api/preview, GET /api/preview/video"| server
  page -->|"POST /api/render, GET /api/render"| server
  server --> files
  server --> temp["preview.mp4 in a temporary folder"]
  page -->|"POST /api/design/save-as"| server
  server --> designs["Named designs folder"]
```

- `Songs` holds the open song's `SyncSession`, or none: then `/api/song` answers 404 `no_song` and the page shows its
  start page (recent songs from `app_files`, Open song… through `web/dialogs.py`, which runs macOS's `choose file` with
  `osascript`). Opening another song loads it first, then closes the old session; it is refused while a render runs.
  Every API request records the time in `Songs.last_request`.
- New songs and the Song mode write song files through `config`: `create_song` writes a new one that names the
  chosen files where they are (`path_in_song_file`), after reading the lyrics; `write_song_settings` changes the
  title, credits, files and default font with `tomlkit`, keeping the rest. Both load the new text before writing.
  `Songs.open` refuses a song whose files are missing (`config.missing_files`, 409 `missing_files` with the list), and
  the page offers to choose them again (`/api/songs/repair`). The page's dialogs go through one route, `/api/choose`,
  by kind (`dialogs.KINDS`: song, audio, image, lyrics, font, folder). Only one dialog opens at a time (409
  `dialog_open`), and the page stays covered until it closes.
- `lyrics-video install-app` (`app_bundle.py`) writes `Lyrics Video.app`: an `Info.plist` and a shell script that
  sets `PATH` to the folders of `uv` and `ffmpeg` (an app started from the Finder gets a short one) and runs
  `uv run --project <repository> lyrics-video start` in the background, then exits. Each click therefore runs the
  script again, and `start` opens the running app's page. The paths are found when installing, so the bundle is made
  on each Mac and never committed. Its icon, `Contents/Resources/AppIcon.icns`, is drawn by `app_icon.py` with Pillow
  (shapes and the page's colors only, no image file in the repository), or made from the owner's image
  (`--icon`), and turned into an `.icns` with macOS's `iconutil`. Without `iconutil` the bundle keeps the default icon
  and the command warns.
- `lyrics-video start` runs the server without a song in app mode: it records its port and token in
  `server.json` in the app's folder (`app_files`, written through a temporary file, so readable by the owner only),
  and a second `start` opens that server's page when it answers `/api/ping`. In app mode the server stops itself when
  no request came for 10 minutes and nothing renders; the page asks `/api/ping` every 30 s while it is open. Quit
  (`/api/quit`) closes the session, cancelling a render only when asked, and stops the server after answering.
- `SyncSession` decodes the song once, keeps one `Preview` and one `LyricsBackdrop`, and replaces the backdrop's
  captions before each still (`set_captions`). Pictures already drawn are kept.
- The Design mode edits the song file's design overrides in the page. Each still and preview sends them with the
  base design's name; the server validates them as the song file would (`song_design`) and passes the result to
  `LyricsBackdrop.set_design`, which draws again but keeps the scaled background image unless the background settings
  changed. `/api/song` also sends every base design's values, and the values of every preset the spectrum can start
  from (`config.preset_values`) with what the song file's own `[spectrum]` sets, so the page shows what changed;
  `/api/fonts` lists the faces of the macOS font folders and of the folders of the song file's fonts
  (`fonts.font_faces`), once per session.
- "Save as design" (`POST /api/design/save-as`) writes the page's design, saved or not, as a named design
  (`config.save_user_design`) into the user folder (`design.user_design_folder`, `$LYRICS_VIDEO_DESIGN_DIR` in
  tests). Only keys that differ from the defaults are written, with font and preset files as absolute paths, so the
  design works from any song folder. `design.load_design` finds a name among the built-in designs, then the named
  designs, then as a file.
- The page plays the song from `/api/audio` with range requests and records key presses at the audio element's time.
  It decodes the same audio in the browser for the waveform.
- The page keeps all edits in memory. Only Save writes: the timing file, and for a changed design the song file
  (`config.write_design`). It replaces the `[design]` table through `tomlkit`, which keeps the rest of the file and
  its comments, and loads the new text before writing it, so a design that does not load changes nothing.
- "Preview video" starts the same `RenderTask` with `prepare_preview` (`render.py`): the page's current lines and
  design, saved or not, at most 960 × 540 and 15 fps, without audio (`preview_size`). The backdrop and the spectrum
  scale with the frame height, so it shows the video's design, captions and spectrum. It goes to a temporary folder of
  the session, replacing the previous preview only when done, and `GET /api/preview/video` serves it (the token is
  accepted in the URL, as for the audio). The page plays it muted and keeps it within 0.1 s of the `<audio>` element,
  which stays the one clock, and marks lines changed since the preview was made. `SyncSession.close` removes the folder
  when the server stops.
- "Render video" starts the session's `RenderTask`: `prepare_render` runs in the request, so its errors answer at
  once; `render` then runs in a background thread with `cancel` tied to the page's Cancel. The page polls the task's
  state. Only the saved timing file is rendered, one render (video or preview) at a time, and Save is refused while
  a video renders. Stopping the server cancels the render and waits for it.

## 3. Rules every change keeps

- **Frame `n` shows the audio at `n / fps`.** Captions and credits are placed by time, never by real-time playback.
- **The backdrop is picklable and pure.** It holds settings and paths only; pictures are built lazily in each process
  (`__getstate__` drops them). `frame` depends only on its arguments and never changes cached pictures.
- **Stills equal video frames.** Every preview goes through `LyricsBackdrop` and audio-spectrum-app's `Preview`, never
  through a second drawing path. Tests check this (`test_a_still_is_the_backdrop_with_the_spectrum_drawn_over_it`,
  `test_stills_are_the_frames_of_the_video`).
- **Nothing is written without an explicit command or Save.** Commands draw every image before writing any, refuse to
  overwrite without `--overwrite`, and write each file through a temporary file and a rename. The page writes only on
  Save (keeping the previous timing file and song file as `.bak`) and on "Render video", which asks before replacing a
  video. The
  preview video is the one exception: it goes to a temporary folder of the session, never next to the song, and is
  removed when the server stops.
- **The page cannot be driven by other web pages.** The server listens on `127.0.0.1`, refuses foreign `Host` headers
  and API requests without the session token (accepted in the URL for the audio and the preview video only), and
  sends no cross-origin headers.
- **Only audio-spectrum-app's public API is used.** Changes it needs are planned in its own repository.
- **Errors meant for the user** are `LyricsVideoError` subclasses with the file and, for text files, the line.

## 4. Performance

The backdrop runs once per frame in audio-spectrum-app's workers, next to the spectrum (about 20 ms per 1080p frame).
How it stays cheap
([ADR-004](../working/DECISIONS.md#adr-004-text-for-video-frames-drawn-with-pillow-composed-in-numpy-in-the-render-workers)):

- Pillow draws every text layer once per process and frame size, as straight-alpha RGBA. Background and title are
  composed once; so are the fully shown credits.
- Per frame, NumPy copies the cached picture and blends only the captions of the moment, and the credits while they
  fade.
- Each process keeps the last three captions as 16-bit arrays ready to blend (`WIDE_CAPTIONS`). Workers render
  consecutive frames, so a caption is converted once per appearance; memory stays bounded however long the song is.

Measured with `tools/time_backdrop.py` on an M1 at 1080p (Phase 2): about 8 ms per frame with a caption and 17 ms
during a crossfade in the default `soft` design. A whole 279 s video with the spectrum renders in 143 s to 154 s
(51 % to 55 % of the song) in every built-in design; its preview video (960 × 540 at 15 fps) in about 19 s (7 %).
See the phase acceptance reports for the full tables.

## 5. Where new features fit

| Feature | Where | Notes |
|---|---|---|
| A new caption style | `CaptionStyle.style` in `design.py`, a `_<style>_caption` function in `layers.py` | Return one `Layer`; the backdrop caches and blends it like the others |
| Another alignment | `CaptionStyle.align` | The setting exists so song files need no change |
| A new design | A TOML file in `src/lyrics_video/designs/` | Built-in designs are found by file name |
| A new part of the frame | A style in `design.py`, a layer in `layers.py`, composition in `LyricsBackdrop` | Draw once in `_prepared_for` if it never changes; blend per frame only while it changes |
| Another timing source (MusicXML, alignment) | A reader that returns `TimedLine`s | `timing.py` writes them as LRC; the backdrop needs no change |
| A new setting in the Design mode | `DESIGN_FIELDS` in `app.js`, its label in every `web/static/i18n/<code>.json` | The key must exist in `design.py`; the page edits it as an override |
| A new page language | `web/static/i18n/<code>.json` and `LANGUAGES` in `app.js` | A test keeps every message file complete |
