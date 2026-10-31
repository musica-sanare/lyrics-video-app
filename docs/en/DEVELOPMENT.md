English | [日本語](../ja/DEVELOPMENT.md) · [Docs index](README.md)

# Development

Setup, checks and conventions for working on the code of lyrics-video-app. Read it before changing code or docs.
To use the app on a song instead, see the [User guide](USER_GUIDE.md).

## 1. Setup

```bash
brew install uv ffmpeg
git clone https://github.com/musica-sanare/audio-spectrum-app ../audio-spectrum-app   # once, next to this repository
uv sync
```

- `uv` manages Python 3.13 and all dependencies (`pyproject.toml`, `uv.lock`).
- audio-spectrum-app is a path dependency (`../audio-spectrum-app`, editable, version 0.5.0 or later), so changes
  there are picked up without reinstalling
  ([ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum)).
  Only its public API, the names exported by `audio_spectrum`, may be used.
- Add a dependency with `uv add <package>`. Keep dependencies few and widely used.

## 2. Tests

```bash
uv run pytest
```

Tests use generated text, images and signals only (`tests/signals.py`), never real songs, lyrics or third-party
fonts. Tests that need a font use macOS system fonts and are skipped where they are missing.

| File | Covers |
|---|---|
| `test_lyrics.py` | Lyrics files: line indexes, rows, separators, errors |
| `test_config.py` | The song file: defaults, paths, colors from sample images, validation, the examples |
| `test_fonts.py` | Collecting font files and their labels |
| `test_caption_image.py` | Caption images: the same pixels as a transcription of the old script, sizes, layout |
| `test_cli.py` | `captions` and `compare`: file names, overwriting, no files on errors, fonts from the command line |
| `test_design.py` | Built-in designs, overrides, design files, invalid values |
| `test_layers.py` | Background cover and crop (never stretched), focus, dim and blur; title (spacing, rule), caption band, gradient and panel, credits (positions, panel); blending |
| `test_backdrop.py` | Fades, captions and credits by time, pickling and other processes, a still equals the backdrop under the spectrum |
| `test_still.py` | The `still` command: file names, captions, design and spectrum from the song file, several designs and the comparison, errors |
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

### Comparing caption images: `compare_images.py`

Use it whenever a change should not alter the caption images.

```bash
uv run python tools/compare_images.py OLD_FOLDER NEW_FOLDER
```

- It pairs the PNGs of two folders by file name, for example the old lyrics image script's output and this app's.
- For each pair it prints the share of differing pixels, the largest difference and where the differences are.
- Stacked old / new / difference images go to `work/compare_images/`.
- It prints positions instead of file names (add `--names` to see them). So its output can go into reports without
  song or font names.

### Timing the backdrop: `time_backdrop.py`

It times the picture under the spectrum per frame for each design. It uses a song file's background, fonts and video
size.

```bash
uv run python tools/time_backdrop.py work/my-song/song.toml --design classic soft panel
```

The target is under 10 ms per 1080p frame with a caption
([ADR-004](../working/DECISIONS.md#adr-004-text-for-video-frames-drawn-with-pillow-composed-in-numpy-in-the-render-workers)).

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
