English | [日本語](../ja/DEVELOPMENT.md) · [Docs index](README.md)

# Development

Setup, checks and conventions for working on the code of lyrics-video-app. Read it before changing code or docs.
To use the app on a song instead, see the [User guide](USER_GUIDE.md).

## 1. Setup

```bash
brew install uv ffmpeg
git clone https://github.com/musica-sanare/lyrics-video-app
cd lyrics-video-app
uv sync
```

- `uv` manages Python 3.13 and all dependencies (`pyproject.toml`, `uv.lock`).
- audio-spectrum-app comes from its public GitHub repository at the tag `v0.5.0`, locked to its commit in `uv.lock`
  ([ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum)).
  Only its public API, the names exported by `audio_spectrum`, may be used.
- To change both repositories together, clone audio-spectrum-app next to this one and layer it over the locked
  version for a run. The project's environment and `uv.lock` stay as they are.

  ```bash
  git clone https://github.com/musica-sanare/audio-spectrum-app ../audio-spectrum-app
  ```

  ```bash
  uv run --with-editable ../audio-spectrum-app pytest
  ```

- To move to a new release of audio-spectrum-app, change its tag in `pyproject.toml` (`[tool.uv.sources]`) and run
  `uv lock`.
- Add a dependency with `uv add <package>`. Keep dependencies few and widely used.

## 2. Tests

```bash
uv run pytest
```

Tests use generated text, images and signals only (`tests/signals.py`), never real songs, lyrics or third-party
fonts. Tests that need a font use macOS system fonts and are skipped where they are missing; video tests are skipped
without ffmpeg. The `sync` page itself
(`src/lyrics_video/web/static/`) is checked by hand in a browser.

| File | Covers |
|---|---|
| `test_lyrics.py` | Lyrics files: line indexes, rows, separators, errors |
| `test_config.py` | The song file: defaults, paths, the separator, removed sections, validation, the examples |
| `test_caption_image.py` | The `classic` caption band: the same pixels as a transcription of the old script, sizes, layout |
| `test_cli.py` | The command line: version, running as a module, removed commands |
| `test_design.py` | Built-in designs, overrides, design files, invalid values |
| `test_layers.py` | Background cover and crop (never stretched), focus, dim and blur; title (spacing, rule), caption band, gradient and panel, credits (positions, panel); blending |
| `test_timing.py` | Timing files (LRC): reading, writing, round trip, ends, invalid files, the merge with a changed lyrics file |
| `test_backdrop.py` | Fades, captions by time (lead, crossfade, sequential, pauses, short captions, at most two at once), credits, pickling and other processes, a still equals the backdrop under the spectrum |
| `test_still.py` | The `still` command: file names, captions by time or chosen, design and spectrum from the song file, several designs and the comparison, errors |
| `test_render.py` | The `render` command: the video with its audio, frames equal to the stills, several workers through the console script, parts, file names, refusals before any work, cancellation and Ctrl+C, progress |
| `test_web.py` | The `sync` server: token and host checks, the token in the URL for the audio only, range requests, loading, saving (backup, invalid times), stills equal to `still`, rendering from the page (saved timing only, one at a time, replacing, cancelling, stopping, Show in Finder), complete page messages in four languages |
| `test_spectrum_dependency.py` | audio-spectrum-app is installed; a still is drawn over a supplied backdrop |

## 3. Local files

Keep songs, lyrics, background images, fonts, real song files and everything rendered in `work/` (ignored by Git) or
outside the repository.

`.gitignore` also ignores, anywhere in the tree:

- media, image and font files;
- every `*.toml` except `pyproject.toml` and `*.example.toml`.

Before a commit, check the file list for any of these. Also check for absolute paths that contain a user name (write
`~/...`).

## 4. Tools

### Timing the backdrop: `time_backdrop.py`

It times the picture under the spectrum per frame for each design. It uses a song file's background, fonts and video
size.

```bash
uv run python tools/time_backdrop.py work/my-song/song.toml --design classic soft panel
```

It prints the mean time per frame without a caption, with a caption, while a caption fades in, while two captions
crossfade, and while the credits fade in. The targets per 1080p frame are under 10 ms with a caption
([ADR-004](../working/DECISIONS.md#adr-004-text-for-video-frames-drawn-with-pillow-composed-in-numpy-in-the-render-workers))
and under 20 ms during a crossfade ([Phase 2 plan](../working/PHASE2_PLAN.md)).

## 5. Conventions

- Code, comments, commit messages and docs are in English. Japanese appears only in the translations
  (`docs/ja/`, `README.ja.md`).
- Frame `n` shows the audio at time `n / fps`; captions and credits are placed by time.
- Normal use is fully offline.
- Stable docs live in `docs/en/`, with a Japanese twin in `docs/ja/`.
  - Each translation records the English blob hash (`git hash-object docs/en/<FILE>.md`) on its first line.
  - It is updated in the same commit as the English file.
  - Working docs (plans, decisions, acceptance reports) live in `docs/working/` in English only.
- Work proceeds in phases:
  1. a plan in `docs/working/PHASE<N>_PLAN.md`, approved by the owner;
  2. implementation, with a commit per milestone;
  3. an acceptance report.
- Before the repository is made public, its whole history is scanned with a secret scanner (for example
  `gitleaks`).
