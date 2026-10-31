English | [日本語](../ja/DEVELOPMENT.md) | [Español](../es/DEVELOPMENT.md) · [Docs index](README.md)

# Development

Setup, checks and conventions for working on the code.

## 1. Setup

```bash
brew install uv ffmpeg
git clone <audio-spectrum-app repository> ../audio-spectrum-app   # once, next to this repository
uv sync
```

Python 3.13 and all dependencies are managed by `uv` (`pyproject.toml`, `uv.lock`). audio-spectrum-app is a path
dependency (`../audio-spectrum-app`, editable, version 0.5.0 or later), so changes there are picked up without
reinstalling ([ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum)).
Only its public API, the names exported by `audio_spectrum`, may be used. Add a dependency with `uv add <package>`;
keep dependencies few and widely used.

## 2. Tests

```bash
uv run pytest
```

- Tests use generated text, images and signals only (`tests/signals.py`), never real songs, lyrics or third-party
  fonts. Tests that need a font use macOS system fonts and are skipped where they are missing.

| File | Covers |
|---|---|
| `test_lyrics.py` | Lyrics files: line indexes, rows, separators, errors |
| `test_config.py` | The song file: defaults, paths, colors from sample images, validation, the examples |
| `test_fonts.py` | Collecting font files and their labels |
| `test_caption_image.py` | Caption images: the same pixels as a transcription of the old script, sizes, layout |
| `test_cli.py` | `captions` and `compare`: file names, overwriting, no files on errors, fonts from the command line |
| `test_spectrum_dependency.py` | audio-spectrum-app is installed; a still is drawn over a supplied backdrop |

## 3. Local files

Songs, lyrics, background images, fonts, real song files and everything rendered stay in `work/` (ignored by Git) or
outside the repository. `.gitignore` also ignores media, image and font files and every `*.toml` except
`pyproject.toml` and `*.example.toml` anywhere in the tree. Before a commit, check the file list for any of these and
for absolute paths that contain a user name (write `~/...`).

## 4. Comparing images

`tools/compare_images.py` compares two folders of PNGs by file name, for example the old lyrics image script's
output with this app's, and prints for each pair the share of differing pixels, the largest difference and where the
differences are; stacked old / new / difference images go to `work/compare_images/`:

```bash
uv run python tools/compare_images.py OLD_FOLDER NEW_FOLDER
```

It prints positions instead of file names (add `--names` to see them), so its output can go into reports without
song or font names. Use it whenever a change should not alter the caption images.

## 5. Conventions

- Code, comments, commit messages and docs are in English. Japanese and Spanish appear only in the translations
  (`docs/ja/`, `docs/es/`, `README.ja.md`, `README.es.md`).
- Frame `n` shows the audio at time `n / fps`; captions and credits are placed by time.
- Normal use is fully offline.
- Stable docs live in `docs/en/` with a Japanese twin in `docs/ja/` and a Spanish twin in `docs/es/`; each
  translation records the English blob hash (`git hash-object docs/en/<FILE>.md`) on its first line and is updated
  in the same commit as the English file. Working docs (plans, decisions, acceptance reports) live in
  `docs/working/` in English only.
- Work proceeds in phases: a plan in `docs/working/PHASE<N>_PLAN.md` approved by the owner, then implementation with a
  commit per milestone, then an acceptance report.
- Before the repository is made public, its whole history is scanned with a secret scanner (for example
  `gitleaks`).
