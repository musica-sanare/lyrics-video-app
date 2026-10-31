[Docs index](../en/README.md)

# Phase 0 acceptance: a safe foundation and the caption images as a CLI

Status: accepted by the owner on 2026-10-31. Version 0.1.0.

Plan: [PHASE0_PLAN.md](PHASE0_PLAN.md). Machine: Apple M1, Python 3.13, Pillow 13.0.0, audio-spectrum-app 0.5.0.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `c378068` | Project rules, handoff, approved plan, `.gitignore` |
| 1. Foundation | `dc4288b` | `uv` project with audio-spectrum-app as a path dependency, `--version`, the backdrop smoke test, MIT license, READMEs, docs index and development guide in three languages, ADR-001 to ADR-003 |
| 2. Captions CLI | `a54349f` | `captions` and `compare` (with a contact sheet), the song file, safe writing, examples, tests, the user guide in three languages |
| 3. Acceptance | `807b960` | `tools/compare_images.py`, this report, status in the READMEs |

## 2. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| `uv sync` and `uv run pytest` succeed on a fresh clone next to audio-spectrum-app, offline once dependencies are cached | Met | A clone of `a54349f` next to a link to audio-spectrum-app: `uv sync --offline --frozen` and `uv run --offline --frozen pytest`, 43 passed |
| For the two sets that still have inputs, every new PNG has the old size, colors and chosen font size, and differs only at glyph edges by at most about 1 px of position | Met | Section 3: 23 of 29 images identical to the pixel; the other 6 differ by glyphs placed about 1 px apart, checked visually in the stacked images |
| The owner can make the caption PNGs of a new song with one command and use them in iMovie as before | Met | The owner checked the images in `work/legacy/new_captions/` (P0-2) |
| Nothing private is tracked: no lyrics, media, fonts, real configuration or user-name paths in any commit | Met | Each commit's file list reviewed before approval; section 4 |
| Docs exist in three languages with matching blob hashes | Met | Every translation's first line matches `git hash-object` of its English file; no broken relative links |

Test suite: 43 tests, all passing.

## 3. Comparison with the old output

The old script's inputs that still exist were copied into `work/legacy/` with a local song file pointing to the same
sample images and fonts as the old configuration, and both commands were run. `tools/compare_images.py` compared the
results with the old PNGs. Only numbers are recorded here: no lyrics, song names or font paths.

| Set | Images | Identical to the pixel | Others: differing pixels, where |
|---|---|---|---|
| Captions of the last song (one font from the owner's font folder) | 18 | 15 | 3 images, 0.56 %–0.59 %: glyphs after a Latin letter about 1 px apart |
| Last font comparison (11 fonts, one text) | 11 | 8 | 1 font from the owner's folder 1.30 %; Hiragino Sans W2 5.08 % and Hiragino Mincho ProN 6.72 %: glyphs about 1 px apart, growing along the row |

Every image has the old size (1440 × 232) and background color, and every chosen font size equals the old one (the
same glyph shapes at the same scale in the stacked images). The Hiragino differences most likely come from updated
system fonts in macOS; the others from changes in FreeType's glyph advances since 2022. Both commands take about
0.5 s for these sets.

The comparison images (`<font>_<line>.png`) and the contact sheet were written as planned; the contact sheet showed
decomposed Japanese font names (macOS file names are NFD) until labels were normalized to NFC during milestone 2.

## 4. Repository safety

- `gitleaks git --redact -v .` (gitleaks 8.30.1) over the whole history (3 commits before the acceptance commit): no leaks
  found. Repeated after `807b960` (4 commits): no leaks found.
- History searched for absolute home paths and e-mail addresses: none. Commits use the GitHub no-reply address.
- `.gitignore` covers `work/`, media, image and font files, LRC files and every `*.toml` except `pyproject.toml` and
  `*.example.toml`; `examples/` holds placeholders and made-up text only.
- The README links to audio-spectrum-app's GitHub page, which works once that repository is public. It is kept
  (P0-3): this repository can only be used by others once audio-spectrum-app is public, so the link is valid
  whenever this repository is.

## 5. Findings

- **The old rules reproduce exactly on current Pillow.** `textbbox`'s right and bottom edges are what the removed
  `textsize` returned, so sizes and positions are unchanged (ADR-002).
- **Band sizes differ between songs** (1440 × 232, and 1500 × 241 or 243 in later sample images); taking the size
  from the sample image, as before, keeps that working.
- **Empty lines count in the file names**, so names have gaps; kept as before (plan Q6).

## 6. Open items

Answered by the owner on 2026-10-31:

- P0-1: Phase 0 is accepted.
- P0-2: the new caption images are fine.
- P0-3: the README keeps its link to audio-spectrum-app's GitHub page. The dependency switches to a Git dependency
  on a tag when the repositories are made public (added to ADR-001).
- Next: Phase 1, the design (title, caption band, credits and spectrum placement as configurable parts, two or three
  variants as stills over the owner's background and font), planned in `PHASE1_PLAN.md`.
