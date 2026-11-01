[Docs index](../en/README.md)

# Phase 5 acceptance: spectrum settings on the page and named designs

Status: accepted by the owner on 2026-11-01. Version 0.4.0.

Plan: [PHASE5_PLAN.md](PHASE5_PLAN.md). Machine: Apple M1 (8 cores), Python 3.13, Pillow 13.0.0,
audio-spectrum-app 0.5.0, FastAPI 0.162.0, uvicorn 0.54.0, tomlkit 0.15.2, gitleaks 8.30.1.

## 1. Delivered

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `5ede2c7`, `7b24495` | Plan; scope chosen by the owner, approved with every recommendation (A1, B1, C1, D1, Q1 to Q7) |
| 1. Spectrum in the design | `dd9c01d` | `spectrum.preset`, `foreground` and preset tables in designs; one preset builder, `config.spectrum_preset`, for every path; checked when the song file loads |
| 2. Spectrum on the page | `5c78c55` | Spectrum group in the Design mode: preset, look, colors and gradients, glow, analysis on release; note when the song file's `[spectrum]` wins |
| 3. Named designs | `4b9f5d8` | User design folder, lookup by name, Save as design, Show designs folder |
| 4. Owner's check | none | The owner set a look with the spectrum on the page, saved it as a named design, rendered, compared with the preview and used the design for a second song (section 2) |
| 5. Acceptance | this commit | ADR-010, ADR-011, this report, version 0.4.0 |

## 2. The owner's results

- **Everything worked.** The owner reported every step of milestone 4 as fine: the look and the spectrum set on the
  page, a named design saved and used for a second song, and a rendered video that matches the preview (P4-1, carried
  over from Phase 4).
- **Render time.** About the song's length on the owner's machine, which the owner finds acceptable. It is slower than
  Phase 3's 51 % to 55 % on an idle machine; other load on the machine and a heavier spectrum (glow, more bands) both
  add time. Not measured in detail in this phase.
- **Not recorded here.** The owner's design names, song files and videos stay outside the repository; this report
  records the owner's statements only.

## 3. Acceptance criteria

| Criterion | Result | Evidence |
|---|---|---|
| The owner sets the spectrum's position, height, style, colors and glow on the page, sees each change in the still at once, and renders the video without opening audio-spectrum-app's page | Met | The owner's check (section 2); a still follows a look change in about 0.4 s and an analysis change in about 0.5 s (section 4) |
| The design holds the spectrum: a song with a named design renders the same spectrum as the song it was saved from | Met | `test_saving_a_user_design_for_other_songs`, `test_the_designs_spectrum`; by hand on two generated songs; the owner's second song |
| Existing song files and designs give the same preset and the same pixels as before | Met | `test_without_spectrum_settings_the_default_preset`, `test_the_song_files_spectrum_as_before`; the owner's song file gives the default preset as before; the 24 reference frames of Phase 4 are still identical at the end of this phase |
| A named design is found by name from any song folder, by `still`, `render` and the page; built-in names cannot be overwritten | Met | `test_a_user_design_is_found_by_name`, `test_a_user_design_by_name` (`still`), `test_saving_the_page_design_as_a_named_design`, `test_built_in_names_are_not_saved`, `test_names_a_named_design_cannot_have` |
| The page writes only on Save, Save as design (after a confirmation to replace), Render video and Preview video | Met | `test_a_named_design_is_replaced_only_when_asked`, `test_saving_the_page_design_as_a_named_design` (the song file changes only on Save); Phase 4's tests |
| The preview matches the rendered video (P4-1) | Met | The owner compared them (section 2) |
| Docs in English and Japanese, nothing private committed (no font paths, songs or designs with the owner's paths) | Met | Translation hashes match; every commit's file list reviewed; section 5. The Mermaid diagrams changed in Phases 3 to 5 still need a look on GitHub (section 7) |

Test suite: 255 tests, all passing (222 at the end of Phase 4). Every test uses its own empty folder of named
designs. The page was checked by hand on generated songs with a design folder in a temporary place: the Spectrum group
with a flat and a perspective preset, gradients, analysis on release, the song-file note, Save, Save as design with
the replace confirmation, and a second song using the saved design.

## 4. Measurements

On the 8-core M1, with other work running.

A still after a spectrum change on the owner's 279.1 s song, in the server:

| Change | Time per still |
|---|---|
| None | 23 ms to 32 ms |
| A look or color key | 26 ms to 39 ms |
| An analysis key, new value | 336 ms to 552 ms (the song is analysed again) |
| An analysis setting used before | 23 ms |

In the page on a generated song, a look change shows about 0.4 s after the input (0.25 s of it is the page's pause
between quick inputs), an analysis change about 0.5 s after the slider is released.

## 5. Repository safety

- `gitleaks git --redact .` over the whole history (38 commits) before this commit: no leaks found.
  `gitleaks dir --redact .` over the working tree, including the ignored `work/`: no leaks found.
- History searched for home paths: none. The only author is the owner's GitHub no-reply address.
- Named designs live in the user folder, outside the repository; tests never read or write the owner's folder
  (`$LYRICS_VIDEO_DESIGN_DIR` points each test at a temporary folder). Tests use generated tones, images and made-up
  lyrics, and system fonts.

## 6. Findings

- **A perspective preset cannot use gradients.** audio-spectrum-app refuses `fill` gradients with the perspective
  look. The page hides the flat look's settings and gradients for a perspective preset and drops them when switching.
- **The page's script must define everything the settings list uses first.** A setting list that used a function
  defined later as a `const` stopped the whole page from loading; it was found in the first manual check and fixed.
  Plain function declarations are used for such helpers.
- **Defaults dumped by the model are enough for a design file.** Only keys that differ from the defaults are written,
  with colors as `#RRGGBB` and paths with `~`, so a named design reads like a hand-written design file.
- **Render time depends on the machine's load and the spectrum.** The owner's renders take about the song's length.

## 7. Open items

- MusicXML draft timing and automatic alignment: planned only if the owner still wants them (Phase 5 plan, "After this
  phase").
- Short full-size clips of the selected line (Phase 4 plan A2), only if the preview is not enough.
- A measured render time with a heavier spectrum, if render time becomes a concern.
- The Mermaid diagrams changed in Phases 3 to 5 (user guide overview and flowchart, architecture layers and sync page)
  need a look on GitHub after the next push.
