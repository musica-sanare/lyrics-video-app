[Docs index](../en/README.md)

# Phase 6 plan: everyday use, from the Dock to the next song

Status: proposed on 2026-11-01, waiting for the owner's answers to the questions in the last section. The owner chose
this scope on 2026-11-01.

## Goal

Make a lyrics video for a new song without a terminal and without a fixed folder layout:

1. **Start the app like any Mac app.** A "Lyrics Video" app in the Dock or Applications opens the page in the
   browser. No `cd` into the repository and no command.
2. **A start page.** Without a song, the page shows recent songs, "Open song…" and "New song…".
3. **A new song from files that already exist.** Choose the audio, the background image and the lyrics text with
   the Finder's own dialogs, wherever they are; give the title, credits, design and font; the app writes the song
   file. The owner has all three files when a song starts (no need to make lyrics or images in the app).
4. **Song settings on the page.** Change the title, credits, files and font of an open song later, also with Finder
   dialogs.
5. **Named designs carry their fonts**, so a new song with a named design needs no font of its own.

The terminal commands (`sync`, `still`, `render`) stay as they are.

Not in this phase: MusicXML draft timing and automatic alignment, line clips (Phase 4 plan A2), a native window
instead of the browser, signing or distributing the app to other Macs.

Inputs: [Phase 5 acceptance](PHASE5_ACCEPTANCE.md), [Architecture](../en/ARCHITECTURE.md), [Decisions](DECISIONS.md)
ADR-006 to ADR-011, `cli.py`, `web/server.py`, `web/app.py`, the [User guide](../en/USER_GUIDE.md) §1 and §2.

## Today

- The page starts only from a terminal, inside the repository: `uv run lyrics-video sync work/my-song/song.toml`.
  Stopping it means `Ctrl+C` in that terminal.
- One server is one song. Another song means stopping the server and starting it again with the other song file.
- A new song means copying `examples/song.example.toml` and `examples/lyrics.example.txt` by hand and typing the
  paths of the audio, the background and the font into the song file.
- Paths in a song file are relative to it or absolute (`~` allowed), so the files can already live anywhere; only the
  way to create and edit song files assumes a folder per song.
- Measured on this Mac: a minimal app bundle (an `Info.plist` and a shell script in `Contents/MacOS`) made locally
  opens with `open` and runs its script; it needs no signing for local use. audio-spectrum-app's own page picks files
  with macOS's dialogs through `osascript` (`choose file`), which works the same way here (this app's own code).

## Options

### A. How the app starts without a terminal

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. `lyrics-video install-app` writes a small app bundle, `~/Applications/Lyrics Video.app`, whose script starts this repository's app with `uv` (both by absolute paths found when installing) | Double-click or Dock like any app; no new dependency; code changes take effect without installing again (it runs the repository's code) | The bundle holds local paths, so it is made on each Mac, never committed; moving the repository needs `install-app` again; the default app icon | **Recommended** |
| A2. A `.command` file to double-click | Simplest | Opens a Terminal window every time, which is what the owner wants to avoid | Not recommended |
| A3. `uv tool install` so `lyrics-video` works from any folder | No `cd` | Still a terminal; the installed copy must be updated after each change | Not on its own |
| A4. A native window (for example pywebview) instead of the browser | Looks like an app | A new GUI dependency and build step; the browser page already works | Not now |

### B. Where a new song's file goes

The owner's audio, image and lyrics can live anywhere. The song file and what the app writes next to it (the timing
file and `videos/`) need a place.

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. Next to the audio file by default, as `<audio name>.toml`; "Change…" chooses another folder | Nothing to decide for most songs; the video ends up next to the song's own files; several songs in one folder work (each has its own timing file and video name) | Writes into the folder of the audio | **Recommended** |
| B2. A folder chosen every time | Full control | One more dialog for every song | Available through "Change…" |
| B3. A library folder of the app (Application Support) | Songs are in one place | Videos end up far from the song's files; another fixed place, which the owner does not want | Not recommended |

### C. The chosen files: referenced or copied

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. Referenced where they are: a path relative to the song file when inside its folder, else an absolute path with `~` | Nothing is duplicated (audio files are large); editing the lyrics file in place is seen by the app | Moving or renaming a file breaks the song until it is chosen again on the page (the page says which file is missing and offers "Choose…") | **Recommended** |
| C2. Copied into the song file's folder | The song folder is complete and portable | Duplicates large audio; two copies of the lyrics drift apart | Not recommended |

### D. Fonts in named designs

| Option | For | Against | Recommendation |
|---|---|---|---|
| D1. "Save as design" writes the song's default font into every text part that has no font of its own, so a named design carries its fonts | A new song with a named design needs no font; one less field in "New song…" | A named design no longer follows a song's `fonts.default` for those parts (a part's font can still be changed in the Design mode) | **Recommended** |
| D2. Remember the last used font and preselect it in "New song…" | Works with old named designs | The font is still per song, outside the design | Fallback for designs saved before this phase |

## Design

### Starting and stopping (A1)

```bash
uv run lyrics-video install-app        # once per Mac, from the repository
```

- `install-app` writes `~/Applications/Lyrics Video.app` (asks before replacing it). Its script runs
  `<uv> run --project <repository> lyrics-video start`, with both paths absolute, and writes its output to
  `~/Library/Logs/lyrics-video.log`. The owner then drags it to the Dock once.
- `lyrics-video start` starts the server without a song and opens the start page. If the app is already running, it
  only opens the page of the running server: the server records its port and session token in
  `~/Library/Application Support/lyrics-video/server.json` (readable by the owner only), and a second start checks
  that the recorded server answers before reusing it.
- Stopping: a "Quit" button on the page, after a confirmation when something is unsaved or a render runs (it then
  cancels the render as `Ctrl+C` does today). The server also stops by itself when no page has been open for 10
  minutes and no render runs (Q5), so closing the browser does not leave it running for long.
- `lyrics-video sync SONG` keeps working as today, now with the start page one click away.

### The start page and switching songs

- `/` shows the start page when no song is open: recent songs (the last 20, newest first, kept in
  `~/Library/Application Support/lyrics-video/recent.json`; a missing song file is shown as missing), "Open song…"
  (a Finder dialog for a `.toml` file) and "New song…".
- One server, one open song at a time. Opening another song replaces the session; the page asks first when there are
  unsaved changes, and refuses while a video renders.
- The page's title bar gets a "Songs" link back to the start page.

### New song… (B1, C1)

A form with:

| Field | Filled by | Default |
|---|---|---|
| Audio | "Choose…" (Finder dialog: audio files) | |
| Background image | "Choose…" (images) | |
| Lyrics | "Choose…" (text files) | |
| Title | Text | The audio file's name |
| Credits | Lines of text | Empty |
| Design | List of built-in and named designs | The last one used |
| Font | Font list of Phase 4 | The design's fonts (D1), else the last one used |
| Song file | "Change…" (Finder dialog: folder) | `<audio name>.toml` next to the audio |

- Before writing, the server reads the lyrics file with the usual rules and shows the first problem (for example a
  line with two `;`), and refuses to replace an existing song file.
- The song file it writes is a normal one, made from the example's layout: `timing = "<song name>.lrc"`, paths
  relative or with `~`, the design by name. It can still be edited by hand.
- The song then opens on the page in Tap mode.

### Song settings on the page

- A "Song" mode next to Tap, Adjust and Design shows the title, credits, the three files (each with "Choose…" and
  "Show in Finder") and the font. Changes are unsaved edits like the design's: the still shows them, Save writes them
  into the song file with `tomlkit` (keeping comments), and a changed lyrics file is merged with the timing as today.
- When a file of the song file is missing on opening, the page opens anyway in the Song mode, names the missing file
  and offers "Choose…", instead of failing.

### Fonts in named designs (D1)

`save_user_design` writes the song's `fonts.default` into the title, caption and credits parts that have no `font`,
before writing the design. Named designs saved before this phase keep working; "New song…" then falls back to the
last used font (D2).

### File dialogs

- `osascript` with `choose file` or `choose folder`, run by the server (on the same Mac, so the dialog appears on the
  owner's screen); the chosen path goes back to the page. Cancel returns nothing.
- Only the routes that open a dialog run `osascript`; the page cannot send a script or a path to run. The usual token
  and host checks apply.
- If the dialog is hidden behind the browser, the page says so and keeps a path field as a fallback, as
  audio-spectrum-app's page does.

### Tests

Generated tones, images and lyrics; temporary folders for the app's state, recent songs and named designs; dialogs
replaced by a stand-in.

- `start`: a second start reuses a running server and a stale `server.json` is ignored; Quit stops the server and
  cancels a render; the idle stop.
- Songs: open, switch with and without unsaved changes, refuse while rendering; recent songs (order, limit, missing
  files).
- New song: the song file written (relative and `~` paths, timing name, design), refused when it exists, refused with
  a lyrics problem before anything is written; it opens and renders.
- Song settings: changed files and title in the still; Save keeps comments; a missing file opens the Song mode.
- `install-app`: the bundle's `Info.plist` and script (paths, log) in a temporary folder; nothing outside it.
- Named designs with fonts (D1).

### Documentation

- User guide (English and Japanese): a new first section "Everyday use": install the app once, start it, a new song,
  the next song; the commands move after it. Setup stays.
- Architecture (English and Japanese): `start`, the server's state file and lifetime, sessions per song, dialogs.
- ADR-012: starting from the Dock and the start page (A1, Q5). ADR-013: new songs from existing files (B1, C1, D1).
- README: status and a quick start that ends with the app in the Dock.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 6 plan` | This plan |
| 1. Start page | `feat: start without a song and switch songs` | `start`, server state file and reuse, Quit, idle stop, start page, recent songs, Open song…, one song at a time |
| 2. New song and song settings | `feat: create and edit songs on the page` | File dialogs, New song…, the Song mode, missing files, fonts in named designs (D1) |
| 3. App bundle | `feat: install the app for the Dock` | `install-app`, log file, docs "Everyday use" |
| 4. Owner's check | none | The owner installs the app, starts it from the Dock, makes a new song from files in any folder, times, previews, renders and quits, then opens the song again from the recent list |
| 5. Acceptance | `docs: accept Phase 6` | ADR-012, ADR-013, `PHASE6_ACCEPTANCE.md`, version 0.5.0 |

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| The owner starts the app from the Dock and never opens a terminal for a new song, from start to video | The owner tries it |
| A new song needs only choosing three files, a title, credits and a design; the song file is written where the owner wants it | The owner tries it; tests |
| The audio, image and lyrics can be in any folder and are not copied | Tests; the owner's song |
| A second start opens the running app instead of a second server; Quit and the idle stop leave no server and no temporary files | Tests; by hand |
| Song files written by the page are normal song files: `sync`, `still` and `render` read them | Tests |
| Nothing on the owner's Mac outside the song's folder, the app bundle and the app's Application Support and log files is written | Tests with temporary folders; review |
| Docs in English and Japanese, nothing private committed (the app bundle and its paths are made locally, never committed) | Hash check, file review, `gitleaks` |

## Carried over

- The Mermaid diagrams changed in Phases 3 to 5 need a look on GitHub after the next push.

## After this phase

- MusicXML draft timing and automatic alignment, only if wanted.
- Line clips (Phase 4 plan A2), only if the preview is not enough.
- A measured render time with a heavier spectrum, if render time becomes a concern.

## Questions for the owner

- Q1. Options A to D: are the recommendations (A1 an app made by `install-app`, B1 the song file next to the audio by
  default, C1 files referenced where they are, D1 named designs carry their fonts) fine?
- Q2. The app's name in the Dock: "Lyrics Video" (recommended), or another name?
- Q3. Where the song file goes by default: next to the audio file (recommended), or always ask?
- Q4. The "Song" mode for changing the title, credits, files and font later: in this phase (recommended), or later?
- Q5. Stopping: a Quit button, and the server stops by itself 10 minutes after the last page closed (recommended). A
  different time, or no automatic stop?
- Q6. The app bundle has the default icon. Fine for now (recommended), or should it get an icon (a generic one drawn
  by the app, no third-party images)?
