[Docs index](../en/README.md)

# Phase 6 acceptance: everyday use, from the Dock to the next song

Status: accepted by the owner on 2026-11-01. Version 0.5.0.

Plan: [PHASE6_PLAN.md](PHASE6_PLAN.md). Machine: Apple M1 (8 cores), Python 3.13, Pillow 13.0.0,
audio-spectrum-app 0.5.0, FastAPI 0.162.0, uvicorn 0.54.0, tomlkit 0.15.2, gitleaks 8.30.1.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `b7ce1b4`, `ec30d41` | Plan; scope chosen by the owner, approved with every recommendation (A1, B1, C1, D1, Q1 to Q6) |
| 1. Start page | `1b021d7` | `start`, `server.json` and reuse of a running app, Quit, the idle stop, the start page with recent songs, Open song…, one song at a time |
| 2. New song and song settings | `c52ebc0` | Finder dialogs, New song…, the Song mode, missing files chosen again, fonts in named designs (D1) |
| 3. App bundle | `283bd35` | `install-app`, the log file, the user guide's "Everyday use" |
| 4. Owner's check | `6194b62` | The owner's check (section 2) and the two fixes it asked for: the page is covered while a Finder dialog opens, and "How to use" on the page |
| 5. Acceptance | this commit | ADR-012, ADR-013, this report, version 0.5.0 |

## 2. The owner's results

- **Everything worked.** The owner installed the app, started it from the Dock, made a new song from files in its
  own folder, and went through the steps of milestone 4.
- **The Finder dialog appears after a short delay.** In that time the page could still be clicked, so a second
  dialog could open. Fixed in `6194b62`: the page is covered until the dialog closes, and the server opens only one
  dialog at a time (409 `dialog_open`).
- **The page did not explain the workflow**, for example that Quit stops the app. Fixed in `6194b62`: "How to use" in
  the top bar lists the steps from the Dock to Quit, and the start page shows them by itself until the first song is
  opened.
- **Not recorded here.** The owner's songs, song files, folders and videos stay outside the repository; this report
  records the owner's statements only.

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The owner starts the app from the Dock and never opens a terminal for a new song, from start to video | Met | The owner's check (section 2) |
| A new song needs only choosing three files, a title, credits and a design; the song file is written where the owner wants it | Met | The owner's check; `test_a_new_song_from_files_in_any_folder`, `test_a_new_song_goes_to_the_chosen_folder_and_never_replaces_one` |
| The audio, image and lyrics can be in any folder and are not copied | Met | `test_a_new_song_names_its_files_where_they_are`, `test_a_new_song_with_a_font_under_the_home_folder`; the owner's song |
| A second start opens the running app instead of a second server; Quit and the idle stop leave no server and no temporary files | Met | `test_a_second_start_opens_the_running_app`, `test_a_recorded_server_that_stopped_is_replaced`, `test_quitting`, `test_idle_after_a_while_without_requests`, `test_only_the_process_that_recorded_the_server_forgets_it`; by hand with the bundle's script (section 4) |
| Song files written by the page are normal song files: `sync`, `still` and `render` read them | Met | `test_a_new_song_from_files_in_any_folder` loads the written file with `load_song`, which the commands use; `test_changing_song_settings_keeps_the_rest` |
| Nothing on the owner's Mac outside the song's folder, the app bundle and the app's Application Support and log files is written | Met | Tests use temporary folders for the app's files, named designs and the bundle (`$LYRICS_VIDEO_APP_DIR`, `$LYRICS_VIDEO_DESIGN_DIR`); code review |
| Docs in English and Japanese, nothing private committed (the app bundle and its paths are made locally, never committed) | Met | Translation hashes match; every commit's file list reviewed; section 5. The Mermaid diagrams changed in Phases 3 to 6 still need a look on GitHub (section 7) |

Test suite: 296 tests, all passing (255 at the end of Phase 5). The page was checked by hand on generated songs with
the app's folder in a temporary place: the start page, New song…, missing files, the Song mode, Quit, the cover while
a dialog opens (with the dialog's answer delayed by 4 s, a second click sent no request) and "How to use" in Japanese.

## 4. Measurements

On the 8-core M1, with other work running, the app's folder in a temporary place.

| Step | Time |
|---|---|
| `lyrics-video start` until the server answers (uv's environment ready) | 0.8 s |
| A second `start` that finds the running app and opens its page | 0.45 s |

The bundle's script returns at once, because it starts `uv` in the background. The first start after a change of the
dependencies takes longer while `uv` updates the environment. The bundle was also run with an empty environment
(`env -i`): it found `uv` and ffmpeg, a preview render ran, and Quit stopped the server.

## 5. Repository safety

- `gitleaks git --redact .` over the whole history (45 commits) before this commit: no leaks found.
  `gitleaks dir --redact .` over the working tree, including the ignored `work/`: no leaks found.
- History searched for home paths: none. The only author is the owner's GitHub no-reply address.
- The app bundle, `server.json` (port and session token, mode 0600), `recent.json`, `settings.json` and the log file
  are made on the owner's Mac and never committed. Tests never read or write the owner's folders.

## 6. Findings

- **The page is on the browser's side of the screen, the dialog on the Mac's.** The Finder dialog is shown by the
  server through `osascript`, so the page cannot see it and must wait for its answer. Covering the page while it waits
  is the simplest way to keep the two in step.
- **An app bundle needs its tools by absolute path.** An app started from the Finder gets a short `PATH`, so
  `install-app` writes the folders of `uv` and ffmpeg into the script.
- **Reopening is simpler than previewing unsaved song settings.** The Song mode saves and opens the song again
  instead of showing unsaved changes in the still; a new audio file needs decoding again anyway (recorded in the plan).
- **Tests must not touch the owner's app folders.** An early test run wrote `recent.json` into the owner's real
  Application Support folder; it held test paths only and was removed. Every test now uses a temporary app folder.

## 7. Open items

- MusicXML draft timing and automatic alignment: only if the owner still wants them.
- Line clips (Phase 4 plan A2), only if the preview is not enough.
- A measured render time with a heavier spectrum, if render time becomes a concern.
- An icon for the app bundle (Q6: the default icon for now).
- The Mermaid diagrams changed in Phases 3 to 6 (user guide overview and flowchart, architecture layers and sync page)
  need a look on GitHub after the next push.
