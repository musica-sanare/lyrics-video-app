[Docs index](../en/README.md)

# Phase 4 plan: a preview of the video and design settings on the page

Status: approved by the owner on 2026-11-01 with the recommended options (A1, B1, C1) and every recommended
answer; the answers are recorded in the last section. Named designs (C3) and spectrum settings on the page are
wanted in a later phase. Delivered and accepted the same day ([Phase 4 acceptance](PHASE4_ACCEPTANCE.md)).

## Goal

Let the owner check a song's video and change its look before the long render, both on the `sync` page:

1. **Preview before rendering (P3-1).** A quick preview that shows the caption changes as in the video, with the
   design and the spectrum, so times can be checked and fixed before the whole render. Today the page shows a simple
   caption preview while playing and exact stills only when paused.
2. **Design settings with a preview (P3-2).** Change the look of each part on the page and see it at once: caption
   background color and opacity, title font, bold, italic and background color, and similar settings of the other
   parts. Bold, italic and a title background are new design keys; the rest already exist.
3. **Saving a design.** The changes are written to the song file's `[design]` overrides, so `still`, `render` and the
   page all use them.

Not in this phase (see "After this phase"): named designs for other songs and spectrum settings on the page (both
wanted later), MusicXML draft timing and automatic alignment (the handoff's old Phase 4), other output sizes.

Inputs: [Phase 3 acceptance](PHASE3_ACCEPTANCE.md) sections 6 and 7, [Architecture](../en/ARCHITECTURE.md),
[Decisions](DECISIONS.md) ADR-004 to ADR-007, `design.py`, `layers.py`, `web/`, and audio-spectrum-app's embedding
guide (its `docs/en/EMBEDDING.md` §2: `RenderJob` with `width`, `height`, `fps`, `start`, `duration`; `Preview`;
backdrops). audio-spectrum-app needs no change.

## Measured costs

Measured on the 8-core M1 on 2026-11-01 with a generated 60 s song (a sweeping tone), a generated 3000 × 2000
background, made-up two-row captions every 4 s, Hiragino Sans and the `soft` design. Other work was running (load
average 3 to 4 at the start), so absolute times are high; the ratios between rows are what matters.

| What | Time | Share of the song's length |
|---|---|---|
| Whole video, 1920 × 1080 at 30 fps (today's render) | 64.7 s for 60 s | 108 % |
| Whole video, 960 × 540 at 30 fps | 14.4 s | 24 % |
| Whole video, 960 × 540 at 15 fps | 8.3 s | 14 % |
| Whole video, 640 × 360 at 15 fps | 6.3 s | 10 % |
| 5 s clip, 1920 × 1080 at 30 fps, one process | 5.6 s | 112 % of the clip |
| 5 s clip, 1920 × 1080 at 30 fps, automatic workers | 5.9 s | 119 % of the clip |
| 5 s clip, 960 × 540 at 30 fps, one process | 1.8 s | 35 % of the clip |

| One frame drawn live (`Preview.frames` with the backdrop) | `soft` | `panel` |
|---|---|---|
| 1920 × 1080 | 30 ms | 27 ms |
| 960 × 540 | 13 ms | 8 ms |
| 640 × 360 | 5 ms | 4.5 ms |

`prepare` of the backdrop (scaling a 5000 × 3333 photo, drawing title and credits) takes about 220 ms at 1080p in
every built-in design; a caption's first frame then takes 5 ms to 12 ms.

Estimates for the owner's 279 s song, scaled from Phase 3's warm 1080p render (143 s) by the ratios above:

| Preview | Idle machine | Under load like the measurement |
|---|---|---|
| 960 × 540 at 15 fps | about 20 s | about 40 s |
| 960 × 540 at 30 fps | about 30 s | about 70 s |
| 640 × 360 at 15 fps | about 15 s | about 30 s |

The page's preview area is at most 40 % of the window's height, about 640 × 360 CSS pixels on a laptop, so a
960 × 540 video is about as sharp as that area can show on a Retina screen.

## Options

### A. The preview before rendering (P3-1)

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. A low-resolution preview video of the whole song (960 × 540 at 15 fps), rendered on request from the page's current times and design and played in the page in sync with the song | The real drawing path (design, captions by time, spectrum) for every caption change; about 20 s to 40 s; the whole song can then be watched or skipped through like the final video | A wait before watching; text and thin lines are softer than at 1080p; times changed afterwards need a new preview | **Recommended** |
| A2. Short clips around the selected line (like audio-spectrum-app's "Play 5-second clip"): full size, one process, from 1 s before the line's caption appears to 1 s after it leaves | Exact frames; a few seconds per line; cheap to redo after a correction | One line at a time: checking a whole song means many clicks and waits | Not now (Q3); added later if the whole-song preview is not enough |
| A3. Frames drawn live by the server while the song plays (960 × 540, about 13 ms each, sent as JPEG) | No wait | At most about 10 to 20 frames a second after encoding and transfer; frames lag and drift from the audio; holds the session's `Preview` (not thread-safe) so stills wait; one core busy | Not recommended |
| A4. Draw the design in the browser (canvas) while playing | Smooth and immediate | A second drawing path that differs from the video; breaks the rule that every preview goes through `LyricsBackdrop` | Rejected |

### B. Where design settings are edited (P3-2)

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. A "Design" panel on the `sync` page, next to the Tap and Adjust modes, with the page's still preview updated as settings change | One page for timing, look, preview and render; reuses the session, token, still route and preview video; a changed design shows in the preview video too | The page grows; more texts in four languages | **Recommended** |
| B2. A separate `lyrics-video design` command and page | A clean page for looks only | A second server, session and preview for the same song; switching pages to check timing with the new look | Not recommended |
| B3. Keep editing the song file by hand, with `still` to check | No work | What the owner asked to replace | Not recommended |

### C. Where a design is saved

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. In the song file's `[design]` table, as overrides of the base design (only the keys that differ), written with a TOML library that keeps the file's comments and layout, with a `.bak` copy | One file per song stays the single source; `still` and `render` read it already; nothing new to learn | A new dependency (`tomlkit`, MIT license, pure Python) to keep comments; the song file is now written by the page | **Recommended** |
| C2. A separate design file next to the song file, named once in the song file (`design = "my-design.toml"`) | The song file is never rewritten; a design file can be shared | Two files to keep together; the song file must be edited once anyway; the design file holds every key, not just changes | Not recommended |
| C3. In addition to C1, "Save as design" writes a named design to a user folder (`~/Library/Application Support/lyrics-video/designs/`), found by name after the built-in designs, like audio-spectrum-app's user presets | Reuse one look for every song by naming it | More code and texts; not needed for one song at a time | Later (Q7): wanted, in a later phase |

## Design

### The preview video (A1)

- A "Preview video" button on the page renders the whole song at the preview size (Q2) from the page's **current**
  lines and design, including unsaved edits. It is a check, not a result, so unlike "Render video" it does not need
  a saved timing file.
- It runs as a second kind of task in the session's `RenderTask` (one task at a time, preview or video), with the
  same progress bar and Cancel, automatic workers and H.264 at a fast setting, without audio. The backdrop and the spectrum scale
  with the frame height, so the same `LyricsBackdrop` and preset are used at 960 × 540.
- The file goes to a temporary folder of the session (not next to the song file), replaces the previous preview, and
  is removed when the server stops. The rule "nothing is written without an explicit command or Save" is about the
  user's files; the architecture doc states this exception.
- `GET /api/preview/video` serves it with range requests. A `<video>` element cannot send headers, so this route
  takes the token in the URL, as the audio route does.
- In the page, the preview video replaces the simple live preview while the song plays; paused, the exact still
  shows as before. It plays muted and follows the `<audio>` element, which stays the one clock for keys and the
  waveform: it seeks with the audio and is corrected when it drifts by more than 0.1 s (milestone 1 measured a steady
  20 ms to 30 ms, under half a preview frame).
- Changing a time or a design setting after the preview marks it out of date: the note above the preview says so,
  and the changed lines are marked in the table, until "Preview video" is pressed again. The preview is not
  rebuilt automatically, so a render never starts while the owner is still tapping.

### Design keys: what exists and what is new

Existing keys, which the page only exposes:

| Part | Existing keys |
|---|---|
| Background | `focus`, `dim`, `blur` |
| Title | `enabled`, `position`, `font`, `size`, `color`, `margin`, `letter_spacing`, `rule`, `shadow` |
| Caption | `style`, `font`, `text_color`, `size`, `line_spacing`, margins, `lead_seconds`, `fade_seconds`, `transition`, `shadow`; background per style: `band_color`, `band_opacity`, `band_height`; `gradient.color`, `gradient.opacity`, `gradient.height`; `panel.color`, `panel.opacity`, `panel.blur`, `panel.radius`, `panel.padding` |
| Credits | `enabled`, `position`, `font`, `size`, `color`, `dim`, `panel`, `show_seconds`, `fade_seconds`, `shadow` |

The caption's "background color and opacity" therefore already exists, under a different key for each caption style;
the page shows the keys of the selected style.

New keys, for every text part (title, caption, credits) unless noted:

| Key | Type, default | Drawn by |
|---|---|---|
| `font_face` | integer, 0 | The face inside a font collection (`.ttc`); `fonts.load_font` already takes the index. A real bold or other weight is chosen this way or with another `font` file (Hiragino has a file per weight) |
| `bold` | boolean, false | Synthetic bold: Pillow's `stroke_width` on the text mask, about 3 % of the font size (Q4). Text is measured with the stroke, so fitting and centering stay right |
| `italic` | boolean, false | Synthetic slant: the text mask sheared by about 12° around the baseline, since Japanese fonts have no italic face (Q4). The extra width is counted when text is fitted |
| `title.panel` | a `Panel` or none, none | A box behind the title, as `credits.panel`: `color`, `opacity`, `blur` (0 gives a plain see-through color, more gives frosted glass), `radius`, `padding` (Q5) |

The `band` caption style draws text through `caption_image.draw_caption` (the old script's rules), so `bold` and
`italic` are passed through to it too. Shadows are drawn from the bolded and slanted mask, so they match the text.
All new keys default to today's look: existing song files and the built-in designs render the same pictures, which a
test checks.

### The Design panel (B1)

- A third mode, "Design", next to Tap and Adjust. The table of lines stays visible; the right side shows the preview
  and, below it, the settings grouped by part: Background, Title, Caption, Credits.
- The panel shows a chosen set of keys, not all of them: those listed above except the margins and line spacing,
  which stay editable in the song file. The base design (`soft`, `classic`, `panel`) is a choice at the top;
  changing it keeps the overrides.
- Each field shows whether it is the design's value or changed, and has "Reset" to remove the override.
- Colors use the browser's color picker plus a `#RRGGBB` field; opacities and sizes use a slider with a number
  field.
- Fonts: a list of the font files in macOS's font folders (`/System/Library/Fonts`, `/Library/Fonts`,
  `~/Library/Fonts`) and in the folders of fonts the song file already names (which covers the owner's own font
  folder), with each face's name from Pillow; a path field for any other file (Q8). Font paths are written to the
  song file only, which is never committed.
- Every change sends the page's current design overrides with the still request: the server validates them with
  `Design` (errors appear next to the field) and draws the still at the selected time. `LyricsBackdrop.set_design`
  keeps the pictures whose settings did not change (the scaled background above all), so a title or caption change
  costs tens of milliseconds instead of a full `prepare` (about 220 ms).
- Design edits are unsaved edits like times: Save writes both (timing file and song file), and "Render video" stays
  disabled while either is unsaved, so the video always matches files on disk.

### Saving the design (C1)

- `POST /api/design` (part of Save) writes only the keys that differ from the base design into the song file's
  `[design]` table, as nested tables (`[design.title]`, `[design.title.panel]`). A song file with
  `design = "soft"` becomes `[design]` with `name = "soft"`. Other sections, comments and key order stay as they
  were; a `.bak` copy of the previous song file is kept, and the file is written through a temporary file and a
  rename.
- Before writing, the server loads the result with `load_song`, so a song file the page writes always loads.
- After Save the session reloads the song file, so `still`, `render` and the page agree.

### Tests

Generated tones, images and made-up lyrics; system fonts, skipped where missing; video tests skipped without ffmpeg.

- Preview: a few seconds of a generated song render at 15 fps from unsaved lines; the file is in the session's
  temporary folder, has the expected size and frame count and no audio; decoded frames are close to the stills of the
  same times (the test song is smaller than 540 pixels, so no scaling); the route needs the token; the folder is gone
  after `close`.
- One task at a time: a preview refuses to start during a render and the other way round.
- Design keys: defaults give the same pixels as before; `bold` widens the text mask; `italic` shifts the top of a
  glyph to the right of its bottom; `font_face` opens another face of a `.ttc`; `title.panel` draws a box of the
  given color under the title; fitted captions with `bold` and `italic` stay inside the margins.
- `set_design`: a title change keeps the same background array (no new `prepare` of it); the result equals a backdrop
  built from scratch with the new design.
- Saving: only changed keys are written; comments and other sections survive; `design = "soft"` becomes a table; a
  `.bak` is kept; an invalid override is refused before anything is written; the saved song file loads to the same
  `Design`.
- Page texts complete in four languages (the existing test).

### Documentation

- User guide (English and Japanese): the preview video, the Design mode, every new design key in the design key
  reference.
- Architecture (English and Japanese): the preview task and its temporary folder, `set_design`, the page writing the
  song file; the sync page diagram gains the preview and design routes.
- ADR-008: the preview video (A1). ADR-009: design settings on the page and saved in the song file (B1, C1), the
  new text keys.
- README: status.

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 4 plan` | This plan |
| 1. Preview video | `feat: preview the video on the sync page` | Preview task, temporary folder, route, video following the audio, out-of-date marks, texts in four languages; tests; user guide and architecture; preview time measured on the owner's song |
| 2. Text faces and title box | `feat: add bold, italic and a title box` | `font_face`, `bold`, `italic` for title, caption and credits; `title.panel`; `band` captions too; tests; user guide design key reference |
| 3. Design panel | `feat: edit the design on the sync page` | Design mode, fields, font list, `set_design`, saving to `[design]` with `tomlkit`, texts in four languages; tests; user guide and architecture |
| 4. Owner's check | none | The owner sets the look of a song on the page, checks the timing with the preview video, renders it, and notes what was still missing; results go into the acceptance report |
| 5. Acceptance | `docs: accept Phase 4` | ADR-008, ADR-009, `PHASE4_ACCEPTANCE.md`, version 0.3.0 |

The `httpx2` warning (carried over) is looked at in milestone 1. If it needs a dependency or test setting change,
that change gets its own commit (name proposed once the cause is known), not mixed into a feature commit.

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| A preview of the whole song with design, captions and spectrum is ready in less than a quarter of the song's length on an idle M1 | Measured on the owner's song; the time under load is recorded too |
| The preview shows the same captions at the same times as the final video | Test (scaled 1080p still against a preview frame); the owner compares the preview with the rendered video |
| A time corrected after watching the preview shows in the next preview and in the video | The owner tries it |
| The owner can set caption background color and opacity, title font, bold, italic and background color, and the same kinds of settings of the other parts on the page, and sees each change in the still at once (well under a second) | The owner tries it; still time measured |
| Saved settings are in the song file's `[design]`, only the changed keys, with comments and other sections kept; `still` and `render` use them | Tests; the owner reads the song file |
| Existing song files and built-in designs render exactly as before | Test with the default values of the new keys |
| The page writes only on Save, Render video and Preview video (the preview into a temporary folder removed at the end); the final render uses saved files only | Server tests; by hand |
| Docs in English and Japanese, nothing private committed (no font paths, songs or lyrics) | Hash check, file review, `gitleaks` |

## Carried over from Phase 3

- The Mermaid diagrams changed in Phase 3 (user guide flowchart, architecture layers and sync page) need a look on
  GitHub after the next push; the owner pushes, so the owner checks or tells Claude when they are pushed. The
  diagrams changed in this phase join that list.
- Tests print Starlette's deprecation warning asking for `httpx2` instead of `httpx`; looked at in milestone 1 (see
  above).

## After this phase

The handoff's old Phase 4 moves to Phase 5, after P3-1 and P3-2, as the owner decided on 2026-11-01:

- MusicXML draft timing: a reader that returns `TimedLine`s from the score's lyrics and note times (Architecture
  §5, "Another timing source"), written as LRC and corrected on the `sync` page, where the preview video of this phase
  helps check it.
- Automatic alignment of lyrics to the sung audio, offline only.

Also wanted in a later phase (owner, 2026-11-01); their order against MusicXML and alignment is decided when that
phase is planned:

- Named designs (C3): "Save as design" writes the full design to a user folder
  (`~/Library/Application Support/lyrics-video/designs/`), found by name after the built-in designs, so another song
  file uses it with `design = "<name>"`.
- Spectrum settings on the page. The owner's goal is to set up and render a video in this app alone, without
  audio-spectrum-app's own page. audio-spectrum-app's public API already offers what such a panel needs
  (`preset_schema`, `override_preset`, `preset_to_toml`, `save_user_preset`); whether anything is missing is checked
  when that phase is planned, and any change there is planned in its own repository.
- Short full-size clips of the selected line (A2), only if the whole-song preview turns out not to be enough.

## Questions for the owner

Answers (2026-11-01): the owner accepted every recommendation.

- Q1: A1, B1 and C1.
- Q2: 960 × 540 at 15 fps, the lighter load.
- Q3: no line clips in this phase; considered later only if the preview is not enough.
- Q4: bold and italic as on/off switches with fixed strengths.
- Q5: a box around the title, plain or frosted.
- Q6: `tomlkit` is added, with a `.bak` copy on each save.
- Q7: named designs are wanted, in a later phase.
- Q8: macOS's font folders, the folders of fonts the song file names, and a path field.
- Q9: spectrum settings are wanted on the page in a later phase, so that a video can finally be set up and rendered
  in this app alone.

The questions as asked:

- Q1. Options A to C: are the recommendations (A1 a low-resolution preview video of the whole song, B1 a Design mode
  on the `sync` page, C1 saving to the song file's `[design]`) fine?
- Q2. Preview size and frame rate: 960 × 540 at 15 fps (about 20 s for your song on an idle machine; caption fades
  look a little stepped) is recommended. 960 × 540 at 30 fps takes about 30 s and is smooth. Which one?
- Q3. Also short full-size clips of the selected line (A2, "Play this line as video")? They show exact frames in a
  few seconds but add work. Recommended: not now; add them if the whole-song preview is not enough.
- Q4. Bold and italic: synthetic bold (about 3 % of the font size) and slant (about 12°) as on/off switches, plus
  choosing a real heavier font file or face. Are fixed strengths fine, or should their strength be adjustable?
- Q5. The title background: a box around the title, plain or frosted (like the panel captions and credits), is
  recommended. Or should it be a band across the whole width, like the `classic` caption band?
- Q6. Saving to the song file needs the `tomlkit` library (free, MIT license) to keep the file's comments and layout,
  with a `.bak` copy of the previous file. Fine to add it?
- Q7. Named designs for other songs (C3, a user design folder like audio-spectrum-app's user presets): in this phase,
  or later (recommended: later)?
- Q8. Fonts listed on the page: macOS's font folders plus the folders of fonts your song file already names, and a
  path field for any other file. Enough, or should a song file setting name more font folders?
- Q9. Spectrum settings stay out of the page (audio-spectrum-app's page edits presets; the song file names the
  preset). Fine for this phase?
