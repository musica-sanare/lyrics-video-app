[Docs index](../en/README.md)

# Phase 5 plan: spectrum settings on the page and named designs

Status: approved by the owner on 2026-11-01 with the recommended options (A1, B1, C1, D1) and every recommended
answer; the answers are recorded in the last section. The owner chose this scope the same day (spectrum settings and
named designs, before MusicXML and alignment). Delivered and accepted the same day
([Phase 5 acceptance](PHASE5_ACCEPTANCE.md)).

## Goal

Set up a lyrics video completely in this app, and reuse a look for other songs:

1. **Spectrum settings on the page.** Change the spectrum (position, height, style, colors, analysis, glow) in the
   `sync` page's Design mode, with the still updated at each change, instead of in audio-spectrum-app's own page.
   This is the owner's goal from Phase 4 (plan Q9): set up and render a video in this app alone.
2. **The spectrum as part of the design.** The design holds the spectrum's base preset and its changes, so one design
   describes the whole look of a video.
3. **Named designs.** Save the look of a song as a design with a name, and use it for another song by naming it in
   that song's file or choosing it on the page (Phase 4 plan C3).
4. **The first video with a design set on the page** (P4-1, carried over).

Not in this phase: MusicXML draft timing and automatic alignment, short full-size clips per line (Phase 4 plan A2),
the perspective spectrum look's camera settings, editing audio-spectrum-app's own presets.

Inputs: [Phase 4 acceptance](PHASE4_ACCEPTANCE.md) section 7, [Architecture](../en/ARCHITECTURE.md),
[Decisions](DECISIONS.md) ADR-001, ADR-008 and ADR-009, `design.py`, `config.py`, `web/`, and audio-spectrum-app's
public API (its `docs/en/EMBEDDING.md` §2 and `docs/en/USER_GUIDE.md` "Main keys": `preset_schema`, `load_preset`,
`override_preset`, `builtin_preset_names`, `user_preset_names`, `Preview`). audio-spectrum-app needs no change.

## What exists today

- The song file chooses the spectrum with `[spectrum] preset` (an audio-spectrum-app preset name or file, `default`
  by default) and `[spectrum] set`, overrides in audio-spectrum-app's `--set` syntax (`"look.max_height=0.4"`).
- A design has `spectrum.set` too, applied before the song file's. No built-in design uses it.
- The preset's `background` color is never seen: the backdrop is drawn instead of it.
- A preset has about 40 keys (`preset_schema()`): colors, `analysis` (bands, frequencies, levels, attack, release),
  `look` (flat or perspective, which cannot be changed with `--set`), `fill` (one color or a gradient) and `fx`
  (glow). The schema has types, ranges and English descriptions; audio-spectrum-app's page labels are internal and
  are not used here.

## Measured costs

A still on the owner's 279.1 s song (1920 × 1080, `soft` design), in the server, on the 8-core M1 with other work
running:

| Change | Time per still |
|---|---|
| None | 23 ms to 32 ms |
| A look or color key (`look.max_height`, `foreground`) | 26 ms to 39 ms |
| An analysis key (`analysis.bands`, `analysis.release_seconds`), new value | 336 ms to 552 ms (the song is analysed again) |
| An analysis setting used before | 23 ms (`Preview` keeps the last few analyses) |

So look and color settings can follow a slider as it moves; analysis settings are applied when the slider is
released.

## Options

### A. Where the spectrum settings live

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. In the design: a new `spectrum.preset` and the preset changes as tables (option D), saved in the song file's `[design.spectrum]` like the other design keys | One design is the whole look, so a named design (C) carries the spectrum; the Design mode edits one thing; saving reuses Phase 4's `write_design` | Two places can now set the spectrum (the design and the song file's `[spectrum]`), so their order must be clear | **Recommended** |
| A2. In the song file's `[spectrum]` only | Already exists; per song | Named designs would not carry the spectrum; the page would save two tables in two ways | Not recommended |
| A3. As an audio-spectrum-app user preset (`save_user_preset`), named by the song file | Shared with audio-spectrum-app's own page | Writes into another app's folder; the look is split between a preset and a design; nothing gained for videos made here | Not recommended |

Order with A1, from the base to the most specific: the preset (the song file's `[spectrum] preset` when the song file
sets it, else the design's `spectrum.preset`, else `default`), then the design's changes, then the song file's
`[spectrum] set`. A song file that sets the spectrum itself therefore keeps winning; the page says so next to the
spectrum settings (Q5).

### B. Which spectrum settings the page shows

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. A chosen set of about 18 keys of the flat look, with labels in four languages (list in "Design") | Readable, with sensible ranges; covers what changes a lyrics video's look | Other keys stay in files; every key added later needs four labels | **Recommended** |
| B2. Every key, generated from `preset_schema()` with its English description as help | Complete; nothing to add when audio-spectrum-app adds keys | English only; ranges are open-ended; analysis internals (FFT sizes, crossover) and the perspective camera are hard to use | Not recommended |

### C. Where named designs are kept

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. A user folder, `~/Library/Application Support/lyrics-video/designs/<name>.toml` (`$LYRICS_VIDEO_DESIGN_DIR` for tests), found by name after the built-in designs, like audio-spectrum-app's user presets | Any song names a design the same way as a built-in one; outside the repository and every song folder | A folder to find in the Finder (the page can show it) | **Recommended** |
| C2. A `designs/` folder next to the song folders (for example `work/designs/`) | Visible next to the songs | Songs name it by a relative path that breaks when a folder moves; the repository's `work/` is only one place songs live | Not recommended |

### D. How the design writes preset changes

| Option | For | Against | Recommendation |
|---|---|---|---|
| D1. Tables that mirror the preset, for example `[design.spectrum.look]` with `max_height = 0.4`; turned into `--set` overrides when the preset is built | Reads like the rest of the design and like a preset file; the page edits it like other design keys | A second way to write the same change (`set` stays for old files) | **Recommended** |
| D2. The existing `spectrum.set` list of `"key=value"` strings | Already exists | Hard to read and to edit key by key; values need quoting rules | Kept for compatibility only |

## Design

### The spectrum in the design (A1, D1)

```toml
[design.spectrum]
preset = "default"          # an audio-spectrum-app preset name or file; the song file's [spectrum] preset wins

[design.spectrum.look]
baseline_y = 0.55
max_height = 0.25

[design.spectrum.fill]
mode = "frequency"
colors = ["#FFFFFF", "#FFD84A"]
```

- `SpectrumStyle` gains `preset` (none by default) and free tables `analysis`, `look`, `fill`, `fx` and the
  top-level `foreground`. They are not checked by this app's model; they are turned into `--set` overrides and
  checked by `override_preset` when the song file loads, so an invalid key fails at once with audio-spectrum-app's
  message and the song file's name.
- `look.kind` cannot be overridden (audio-spectrum-app refuses it); the preset decides between the flat and the
  perspective look.
- `config` builds the preset once: base, design changes, song file `set`. `still`, `render`, the preview and the
  page all use that function, so they cannot disagree.
- Existing song files and designs give the same preset as before (test).

### Spectrum settings in the Design mode (B1)

A "Spectrum" group after Credits:

| Setting | Key | Control |
|---|---|---|
| Preset | `preset` | The built-in presets and audio-spectrum-app's user presets |
| Position (height of the baseline) | `look.baseline_y` | Slider 0 to 1 |
| Height | `look.max_height` | Slider 0 to 1 |
| Side margin | `look.margin_x` | Slider 0 to 0.3 |
| Mirrored | `look.mirror` | Checkbox |
| Style | `look.style` | Bars or blocks |
| Bar width | `look.bar_fill` | Slider |
| Block height, gap | `look.block_height_px`, `look.block_gap_px` | Sliders, blocks only |
| Response | `look.response` | Slider 0.5 to 3 |
| Color | `fill.mode` | One color or a gradient |
| Line color | `foreground` | Color, one color only |
| Gradient colors | `fill.colors` | Two to four colors, gradient only |
| Glow | `fx.glow_radius_px`, `fx.glow_strength` | Sliders |
| Bands | `analysis.bands` | Slider 16 to 1024 |
| Lowest and highest frequency | `analysis.min_frequency`, `analysis.max_frequency` | Sliders |
| Level | `analysis.gain` | Slider |
| Rise and fall | `analysis.attack_seconds`, `analysis.release_seconds` | Sliders |

- Defaults shown next to each field come from the chosen preset (`load_preset(name)`), as the design's values do in
  Phase 4.
- With a perspective preset (`unity-classic`), the look settings are hidden; colors, glow and analysis stay.
- Analysis sliders send their value when released (about 0.4 s for a new value); the others while they move.
- When the song file's `[spectrum]` sets the preset or `set`, a note above the group says that those win over the
  page.
- Stills and the preview video use the page's spectrum settings, saved or not, as for the rest of the design.

### Named designs (C1)

- `design.py` finds a design name in this order: built-in designs, then the user folder, then a file path relative to
  the song file. Built-in names cannot be saved as user designs.
- "Save as design" in the Design mode asks for a name and writes the whole look as it is on the page (base design,
  changes, spectrum) to `<name>.toml` in the user folder. Only keys that differ from the defaults are written, like
  audio-spectrum-app's user presets. An existing name is replaced only after a confirmation; the previous file is kept
  as `.bak`.
- Font paths are written as absolute paths (with `~` for the home folder), so the design works from any song folder.
  Fonts are not copied; a song on a Mac without the font gets the usual error naming the file.
- Names: any name that is a valid file name, not starting with a dot and without `/`; Japanese names are allowed
  (Q6).
- After saving, the page offers to use the new design for this song: the base becomes the new name and the changes
  are cleared, which the next Save writes to the song file.
- The base design list in the Design mode, `still --design` and `render --design` all accept user designs.
- The page has a "Show designs folder" button for renaming and deleting in the Finder.

### Tests

Generated tones, images and made-up lyrics; system fonts; user designs in a temporary folder through
`$LYRICS_VIDEO_DESIGN_DIR`.

- The spectrum: design tables become the expected overrides; the order preset, design, song file `set`; the song
  file's `[spectrum] preset` wins over the design's; `look.kind` and invalid keys fail with clear messages when the
  song file loads; old song files give the same preset as before.
- The page: stills follow unsaved spectrum settings; saving writes `[design.spectrum]` tables; the preview uses them.
- Named designs: save, list, load by name from another song folder; built-in names refused; invalid names refused;
  replacing needs the flag and keeps a `.bak`; fonts written as absolute paths; a user design and a file of the same
  name resolve to the user design.
- Page texts complete in four languages (the existing test).

### Documentation

- User guide (English and Japanese): spectrum settings on the page, `[design.spectrum]` and the order of spectrum
  settings, named designs and their folder.
- Architecture (English and Japanese): the spectrum in the design, the order of preset changes, user designs in the
  design lookup.
- ADR-010: the spectrum as part of the design (A1, B1, D1). ADR-011: named designs in a user folder (C1).
- README: status.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 5 plan` | This plan |
| 1. Spectrum in the design | `feat: keep the spectrum settings in the design` | `spectrum.preset` and preset tables in designs, one preset builder for every path, tests, user guide |
| 2. Spectrum on the page | `feat: edit the spectrum on the sync page` | Spectrum group in the Design mode, preset list, note when the song file wins, texts in four languages, tests, user guide and architecture |
| 3. Named designs | `feat: save designs for other songs` | User design folder, design lookup, Save as design, use for this song, Show designs folder, texts in four languages, tests, docs |
| 4. Owner's check | none | The owner sets the look of a song with the spectrum on the page, saves it as a named design, renders the video and compares it with the preview (P4-1), and tries the design on a second song |
| 5. Acceptance | `docs: accept Phase 5` | ADR-010, ADR-011, `PHASE5_ACCEPTANCE.md`, version 0.4.0 |

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| The owner sets the spectrum's position, height, style, colors and glow on the page, sees each change in the still at once, and renders the video without opening audio-spectrum-app's page | The owner tries it; still times measured |
| The design holds the spectrum: a song with a named design renders the same spectrum as the song it was saved from | Test; the owner tries the design on a second song |
| Existing song files and designs give the same preset and the same pixels as before | Test of the preset; frames of the built-in designs compared before and after |
| A named design is found by name from any song folder, by `still`, `render` and the page; built-in names cannot be overwritten | Tests |
| The page writes only on Save, Save as design (after a confirmation to replace), Render video and Preview video | Server tests; by hand |
| The preview matches the rendered video (P4-1) | The owner compares them |
| Docs in English and Japanese, nothing private committed (no font paths, songs or designs with the owner's paths) | Hash check, file review, `gitleaks` |

## Carried over

- P4-1: the first video with a design saved from the page (milestone 4).
- The Mermaid diagrams changed in Phases 3 and 4 need a look on GitHub after the next push; this phase's changes join
  that list.

## After this phase

- MusicXML draft timing and automatic alignment. Phase 3 showed that tapping a whole song takes about its length with
  almost no corrections, so these save little time; alignment would also need large speech models (downloaded once,
  then offline) with uncertain accuracy on sung Japanese. They are planned only if the owner still wants them.
- Short full-size clips of the selected line (Phase 4 plan A2), only if the preview is not enough.

## Questions for the owner

Answers (2026-11-01): the owner accepted every recommendation.

- Q1: A1, B1, C1 and D1.
- Q2: the chosen set of spectrum settings is enough.
- Q3: `~/Library/Application Support/lyrics-video/designs/`.
- Q4: a named design holds the whole look, spectrum included.
- Q5: a song file's own `[spectrum]` wins over the design, and the page shows a note.
- Q6: any valid file name, Japanese included.
- Q7: the second song is chosen by the owner at milestone 4.

The questions as asked:

- Q1. Options A to D: are the recommendations (A1 the spectrum in the design, B1 a chosen set of spectrum settings,
  C1 a user folder for named designs, D1 preset changes written as tables) fine?
- Q2. The spectrum settings on the page (table in "Spectrum settings in the Design mode"): is anything missing that
  you change today in audio-spectrum-app's page?
- Q3. The folder for named designs, `~/Library/Application Support/lyrics-video/designs/`: fine, or somewhere easier
  to reach (for example a folder in Documents)?
- Q4. A named design holds the whole look, spectrum included (recommended). Or should the spectrum stay per song?
- Q5. When a song file sets `[spectrum]` itself, it wins over the design and the page shows a note (recommended, so
  old song files keep their look). Or should the page's settings always win?
- Q6. Design names: any valid file name, Japanese included (recommended), or only letters, digits, `-` and `_`?
- Q7. Milestone 4 includes P4-1 (rendering a video with a design saved from the page and comparing it with the
  preview) and trying a named design on a second song. Which second song can you use?
