[Docs index](../en/README.md)

# Phase 0 plan: a safe foundation and the caption images as a CLI

Status: approved by the owner on 2026-10-31 with every recommendation (A1, B1, C1, D1, E1); the answers to the
questions are recorded in the last section. Delivered the same day
([Phase 0 acceptance](PHASE0_ACCEPTANCE.md)).

## Goal

1. A repository that is safe to make public at any time: a `uv` project with audio-spectrum-app as a dependency,
   tests, an example configuration, a license, and READMEs and docs in English, Japanese and Spanish.
2. The old lyrics image script rebuilt as a CLI that runs on today's Python and Pillow and produces the same caption
   PNGs as before, so the owner's iMovie workflow keeps working until this app makes whole videos (Phase 3).

Not in this phase: captions drawn at video resolution, the title, credits, timing, the backdrop and video rendering
(Phases 1 to 3).

Inputs: [Handoff](HANDOFF.md), audio-spectrum-app's user guide §5, its ADR-008, ADR-012 and ADR-013, and its Phase 4
acceptance report, and the old script (read only; see `CLAUDE.local.md`).

## What the old script does (read on 2026-10-31)

Version 2.0 from 2022: about 300 lines of Python, settings in a TOML file, an interactive prompt that chooses
between two modes.

| Mode | Input | Output |
|---|---|---|
| Captions | A lyrics text file and one font | One PNG per non-empty line, named `lyrics_<line index>.png` (0-based, empty lines still count) |
| Font comparison | A text file and a list of fonts | One PNG per font and line, named `<font file name up to its first dot>_<line index>.png` |

Drawing one caption:

- The image has the size of a "background sample" PNG and is filled with that image's center pixel; the text color
  is the center pixel of a second sample PNG. Past songs used 1440 × 232 and 1500 × 241 or 243 samples in several
  colors.
- A line is one row, or two rows split at `;`; more than one `;` is an error.
- Font size: start at 80 and go down in steps of 2 until every row fits, with its measured width plus 50 px under
  the image width and its measured height plus 50 px under the image height. All rows share the size.
- Text is left-aligned at x = 20. One row is centered vertically; two rows are centered on the upper and lower
  quarter lines. Both use the height of the first row. The first face of a font collection (`index=0`) is used.
- Text size is measured with `ImageDraw.textsize`, which Pillow 10 removed.

### Feasibility check

`ImageDraw.textbbox((0, 0), ...)`'s right and bottom edges are what `textsize` returned. A throwaway script
(not in this repository) re-rendered the last font comparison with Pillow 13.0.0 and the two Hiragino system fonts
and compared the result with the old PNGs:

| Font | Chosen size | Pixels that differ | Where |
|---|---|---|---|
| Hiragino Sans W2 | 80, same as before | 16,977 of 334,080 (5 %) | Glyph edges in the right half of each row |
| Hiragino Mincho ProN | 80, same as before | 22,464 of 334,080 (7 %) | Same |

Side by side, old and new look the same; the differences are glyphs placed about 1 px apart, which grows towards the
end of a row (rounding of glyph advances in newer FreeType or Pillow). Size, colors, layout and file names can be
reproduced exactly.

## Options

### A. Text rendering for the caption PNGs (handoff §7)

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. Pillow (as before) | Same algorithm and measurements as the old script; checked above to give the same size and layout with only 1 px glyph offsets; small, well-known library | A new dependency next to Skia; no text shaping in the default wheel (not needed for Japanese, but proportional kana spacing is not available) | **Recommended for Phase 0** |
| A2. Skia (comes with audio-spectrum-app) | One drawing library for everything, also for the video frames later | Different font metrics: the fitting loop would choose different sizes and positions, so captions would visibly differ from the old ones; not measured | Not now; revisit in Phase 1 |

Captions in the video (Phase 1 onwards) are drawn once per caption and faded in the backdrop, so either library
works there; Phase 1 decides with the owner's chosen design. The caption code keeps the text drawing in one module so
the choice can change without touching the CLI.

### B. Lyrics file format (handoff §7)

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. Keep the old format: one caption per line, `;` for two rows | Every existing lyrics file works unchanged; nothing to learn | Timing must be stored elsewhere later | **Recommended for Phase 0** |
| B2. LRC now (`[mm:ss.xx]` before each line) | Timing and text in one file; common format | Timing does not exist until Phase 2; files without times would be half-filled LRC | Decide in Phase 2 |
| B3. TOML or JSON with one entry per caption | Room for any per-caption setting | Tedious to write lyrics in | Not recommended |

With B1 the timing format is chosen in Phase 2, where the tap-to-sync tool will write it (likely an LRC or JSON file
next to the lyrics, keeping `;`).

### C. Caption images during the transition (handoff §7)

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. PNG bands like before (size from the configuration), for iMovie | The owner can use the new CLI right away; directly comparable with the old output | Becomes unnecessary after Phase 3 | **Recommended for Phase 0** |
| C2. Only captions at video resolution | No throw-away work | Needs the design (Phase 1) and the video (Phase 3) first; nothing usable in Phase 0 | Phase 1 and 3 |

### D. Configuration (handoff §7)

| Option | For | Against | Recommendation |
|---|---|---|---|
| D1. One TOML file per song, validated with pydantic | One place for everything about a song; easy to keep next to the song in `work/`; the same validation style as audio-spectrum-app's presets (its ADR-009) | Repeats the font and colors when songs share them | **Recommended** |
| D2. Shared defaults plus per-song overrides | Less repetition | Two files to look at; where the shared file lives is one more decision; little to share yet | Later, if repetition becomes a problem |

Phase 0's song file, as `examples/song.example.toml` (placeholders only):

```toml
# Paths are relative to this file; "~" is expanded.
lyrics = "lyrics.txt"

[captions]
output_dir = "captions"
size = [1440, 232]           # width, height of each PNG
background = "#000000"       # "#RRGGBB", or a path to an image whose center pixel is used
text_color = "#FFFFFF"       # same
font = "~/path/to/font.otf"  # file outside the repository
font_index = 0               # face in a .ttc collection
separator = ";"
file_prefix = "lyrics"

[compare]
text = "compare.txt"
output_dir = "compare"
fonts = ["/System/Library/Fonts/ヒラギノ角ゴシック W2.ttc"]
font_dirs = []               # every .ttf, .otf, .ttc in these folders is added
```

Colors may still be given as the old sample images (option "path"), so the owner's existing sample PNGs work.
Phases 1 to 3 add sections (title, credits, timing, video) to the same file. The fixed values of the old script
(start size 80, step 2, margins 50, left 20) stay constants in Phase 0 and are not in the file. (要確認 Q5)

### E. Dependency on audio-spectrum-app

audio-spectrum-app `v0.5.0` is tagged (its Phase 4 plan, P4-1). The handoff keeps a path dependency while both
repositories change and leaves pinning the tag for later.

| Option | For | Against | Recommendation |
|---|---|---|---|
| E1. Path dependency, editable (`../audio-spectrum-app`), requiring `audio-spectrum-app>=0.5.0` | Works offline; follows the sibling's `dev` branch; already planned | Not pinned to the tag; the sibling must be checked out next to this repository | **Recommended for Phase 0** |
| E2. Git dependency on the tag (`git+ssh://...@v0.5.0`) | Pinned and reproducible | Needs network and GitHub access at `uv sync`; while the sibling is private, a public checkout of this repository cannot install it | Later, when both are public |

Phase 0 uses the dependency only in a smoke test (rendering a still with a generated signal and a one-color
backdrop), so the setup is proven before Phase 1 relies on it.

## Design

### Package and command

- Package `lyrics_video` in `src/`, command `lyrics-video`, `argparse` like audio-spectrum-app. Python 3.13, `uv`.
- Runtime dependencies: `audio-spectrum-app` (path), `pillow`, `pydantic` (already used by the sibling). Dev:
  `pytest`.

```bash
uv run lyrics-video captions work/my-song/song.toml            # one PNG per caption
uv run lyrics-video compare work/my-song/song.toml             # one PNG per font and line, plus a contact sheet
uv run lyrics-video compare song.toml --font a.otf --font-dir ~/Fonts   # fonts from the command line
```

- No interactive prompt: the subcommand chooses the mode.
- The same output as the old script for the same inputs: sizes, colors, font size, positions, file names
  (`lyrics_<line index>.png`, 0-based, empty lines counted). (要確認 Q6)
- Deliberate differences, each small:
  - A font comparison file name uses the whole file name without its extension (`example-font-2.04_0.png`,
    not `example-font-2_0.png`), so fonts whose names differ after a dot do not overwrite each other.
  - `compare` also writes `contact_sheet.png`: every font's rendering of the first line, stacked, with the font's
    name beside it, to choose a font at a glance. (要確認 Q7)
  - Existing PNGs are not overwritten unless `--overwrite` is given; the command lists them and exits with an
    error before writing anything. The old script overwrote silently and left old files behind when the lyrics got
    shorter. (要確認 Q8)
  - Clear errors (missing file, unreadable font, a line with two separators, with the line number) and documented
    exit codes; output is written to a temporary name and renamed, so a failure leaves no half-written PNG.

### Modules

| Module | Content |
|---|---|
| `lyrics.py` | Reading a lyrics file into captions (line index, one or two rows), separator check |
| `config.py` | The pydantic models of the song file, path resolution (relative to the file, `~`), colors from `#RRGGBB` or a sample image |
| `caption_image.py` | Fitting the font size and drawing one caption (the old algorithm, with `textbbox`); the only module that imports Pillow's drawing |
| `fonts.py` | Collecting fonts from paths and folders, opening collections by index, display names |
| `cli.py` | Subcommands, messages, exit codes, safe writing |

### Tests

Generated text and images only; fonts are macOS system fonts (Hiragino), and tests that need them are skipped where
they are missing.

- Lyrics: empty lines, one and two rows, the separator error with its line number, a custom separator.
- Configuration: relative and `~` paths, colors from hex and from a generated sample image, invalid values.
- Captions: the chosen size for short and long rows (80 for short text, smaller and even for long text), positions of
  one and two rows, colors, image size; the same result as a direct transcription of the old algorithm on current
  Pillow for a set of generated lines (the transcription lives in the test as the oracle).
- CLI: file names, `--overwrite`, no partial files on failure, exit codes, `compare` with paths and folders.
- audio-spectrum-app: a still rendered with a generated sine and a one-color backdrop has the expected size and the
  backdrop color away from the spectrum.

### Comparison with the old output (manual, local)

`tools/compare_images.py` (committed, takes two folders, no paths inside) reports for each pair of PNGs with the same
name: size, differing pixels, the largest difference, and writes a stacked old / new / difference image. The owner's
data stays in `work/`. Two sets still have their inputs: the last song's 18 captions (with a font from the owner's
font folder) and the last 11-font comparison. Results go into the acceptance report as numbers only, without lyrics,
song names or font paths.

### Repository and docs

| Path | Content |
|---|---|
| `README.md`, `README.ja.md`, `README.es.md` | Overview, status, quick start, links, license |
| `LICENSE` | MIT, as audio-spectrum-app (要確認 Q2) |
| `docs/{en,ja,es}/README.md` | Docs index |
| `docs/{en,ja,es}/USER_GUIDE.md` | Setup, the `captions` and `compare` commands, the song file, moving from the old script |
| `docs/{en,ja,es}/DEVELOPMENT.md` | Setup, tests, conventions, the repository's safety rules |
| `docs/working/DECISIONS.md` | ADR-001 separate repository and composition through audio-spectrum-app's backdrop; ADR-002 Pillow for the caption PNGs; ADR-003 one TOML file per song and the lyrics format |
| `docs/working/PHASE0_ACCEPTANCE.md` | The acceptance report |
| `examples/song.example.toml`, `examples/lyrics.example.txt` | Placeholders and made-up text only |
| `tools/compare_images.py` | The comparison above |

An architecture document starts in Phase 1, when there is more than one module chain to describe.

### Corrections to the drafted files

Made together with this plan, for the first commit:

- `.gitignore`: also ignore images (`*.png`, `*.jpg`, `*.jpeg`, `*.heic`, `*.webp`), more font types (`*.woff`,
  `*.woff2`, `*.otc`, `*.dfont`), LRC files and every `*.toml` except `pyproject.toml` and `*.example.toml`, so
  backgrounds, captions and real song files cannot be committed by accident outside `work/`. Images that docs need
  later get an explicit exception.
- `HANDOFF.md`: band sizes of past songs (also 1500 × 241 and 243), and the new `.gitignore` coverage in §6.

`CLAUDE.md` needs no change: it already says the path dependency can later pin `v0.5.0`.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add handoff, project rules and Phase 0 plan` | `.gitignore`, `CLAUDE.md`, `docs/working/HANDOFF.md`, this plan (approved) |
| 1. Foundation | `chore: set up the uv project and docs` | `pyproject.toml`, `uv.lock`, package skeleton with `--version`, the smoke test, `LICENSE`, READMEs and docs indexes and `DEVELOPMENT.md` in three languages, `DECISIONS.md` |
| 2. Captions CLI | `feat: render caption images from a lyrics file` | `captions` and `compare`, configuration, examples, tests, `USER_GUIDE.md` in three languages |
| 3. Acceptance | `docs: accept Phase 0` | `tools/compare_images.py`, the comparison with the old output, `PHASE0_ACCEPTANCE.md`, status in the READMEs |

Each commit is proposed with its message and file list and made only after approval. Before each, the staged files
are checked for lyrics, media, fonts, real configuration and paths with a user name.

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| `uv sync` and `uv run pytest` succeed on a fresh clone next to audio-spectrum-app, offline once dependencies are cached | Run in a temporary clone |
| For the two sets that still have inputs, every new PNG has the old size, colors and chosen font size, and differs only at glyph edges by at most about 1 px of position | `tools/compare_images.py` numbers and stacked images, checked by the owner |
| The owner can make the caption PNGs of a new song with one command and use them in iMovie as before | The owner tries it |
| Nothing private is tracked: no lyrics, media, fonts, real configuration or user-name paths in any commit | Review of every commit; a `gitleaks` scan of the history at the end of the phase, reported in the acceptance report |
| Docs exist in three languages with matching blob hashes | Hash check |

## Questions for the owner

Answers (2026-10-31): Q1 all recommendations; Q2 MIT; Q3 no environment named, so the comparison uses the two sets
that still have inputs; Q4 older lyrics files are not kept (each song overwrote the last), so the same two sets;
Q5 the values stay fixed in Phase 0; Q6 old file names; Q7 yes, the contact sheet is wanted; Q8 yes, `--overwrite`;
Q9 not in Phase 0; Q10 yes.

- Q1. Options A to E: are the recommendations (A1 Pillow, B1 old lyrics format, C1 PNG bands, D1 one TOML per song,
  E1 path dependency) fine?
- Q2. License: MIT, like audio-spectrum-app? Fonts and lyrics are never in the repository, so the license covers
  only code and docs.
- Q3. The handoff says the old script probably no longer runs on Pillow 10 or later, but its last outputs are dated
  2026-08-16. Is there an environment where it still runs (for example an older Pillow in pyenv)? If so, the
  comparison could use fresh old outputs for any text, not only the two sets that still have their inputs.
- Q4. Which past songs' captions matter for the comparison? Only the last song's lyrics and the last comparison text
  are still in the input folder; for older songs only the PNGs remain. If the owner has older lyrics files, they
  can be added in `work/`.
- Q5. Should the fixed values (start size 80, step 2, margins 50, left 20) become settings now, or stay fixed until
  Phase 1 designs the caption band?
- Q6. File names: keep the old `lyrics_<0-based line index>.png` exactly (empty lines leave gaps), or number captions
  without gaps with zero padding (`lyrics_01.png`), which sorts correctly everywhere? Recommendation: keep the old
  names in Phase 0, since the iMovie workflow is used to them.
- Q7. Is a contact sheet of all fonts (in addition to one PNG per font) useful?
- Q8. Refuse to overwrite existing PNGs unless `--overwrite` is given? Recommendation: yes.
- Q9. Should the owner's font folder be reachable without writing its path in every song file, for example through an
  environment variable or a user settings file outside the repository? Recommendation: not in Phase 0; each song
  file names its font, and `compare --font-dir` takes the folder on the command line.
- Q10. The handoff's §7 asked how closely new captions must match the old PNGs. Proposed: the same size, colors,
  font size, layout and file names, and glyph positions within about 1 px (the feasibility check above). Is that
  close enough?
