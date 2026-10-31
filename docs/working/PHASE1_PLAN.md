[Docs index](../en/README.md)

# Phase 1 plan: the design of a lyrics video as configurable parts

Status: approved by the owner on 2026-10-31 with the recommended options (A1, B1, C1, D1); the answers to the
questions are recorded in the last section. Still open: Q5 (materials for the drafts).

## Goal

Decide what a frame of the owner's lyrics videos looks like, by comparing concrete pictures:

1. The parts of a frame (background, title, lyrics caption, credits, spectrum) as configurable parts in the song
   file.
2. The picture under the spectrum built by this app as an audio-spectrum-app `Backdrop`, so stills are exactly the
   frames the video will have (ADR-001).
3. Two or three designs rendered as stills over the owner's own background and font, with the real spectrum on top;
   the owner chooses one (or a mix) as the default.

Not in this phase: timing of the lyrics (Phase 2) and rendering whole videos (Phase 3). Stills show a chosen caption
at a chosen moment instead.

Inputs: [Handoff](HANDOFF.md) §2 to §4, [Decisions](DECISIONS.md), [Phase 0 acceptance](PHASE0_ACCEPTANCE.md), and
audio-spectrum-app's preset schema (`preset_schema()`).

## Today's videos

From the handoff: the background image fills the 1920 × 1080 frame with the song title baked into it at the top; each
caption PNG (an opaque band in one color, about 1440 × 232) sits at the very bottom, full width, with about 2 s
fades; credits appear before and after the song; the spectrum video is keyed over everything, roughly centered, and
may cover the lyrics now and then.

What audio-spectrum-app offers for placement (preset `look`, `flat` kind): `baseline_y` (0.5 = centered),
`max_height` (0.3 of the frame height on each side), `margin_x`, `mirror`, styles, colors and glow. With the default
look the spectrum spans from 20 % to 80 % of the height, so it overlaps the top of a bottom caption band, as today.

## Frame model

Layers from bottom to top. Everything except the caption is the same in every frame of the song body, so it is
composed once per worker process and reused; only the caption (and its fade) changes from frame to frame.

| Layer | Content | Settings (song file) |
|---|---|---|
| Background | One image, scaled to cover the frame and cropped, never stretched; optional darkening or blur for readability | `[background] image`, `focus` (crop anchor), `dim`, `blur` |
| Title | Song title, optional subtitle (for example the artist); can be off when the title is baked into the image | `[title] text`, `subtitle`, `position`, `font` (overrides `[fonts] default`), `size`, `color` |
| Caption | The lyrics caption of the moment, in a band, panel or on its own, with its fade | `[caption] style`, `align`, `font`, `size`, colors, `band_height`, `fade_seconds` |
| Credits | Lines of credits shown at the start and the end | `[credits] lines`, `position`, `font`, `size`, `show_seconds` |
| Spectrum | Drawn by audio-spectrum-app over the backdrop | `[spectrum] preset`, `set = ["look.baseline_y=0.5", ...]` (the same overrides as its `--set`) |

Fonts (Q4): `[fonts] default` sets the font of every part at once; each part's own `font` overrides it, so the
title (or any other part) can use a different font.

Captions keep today's rules for now (Q9): left-aligned, at most two rows split at `;`. The caption part keeps
alignment and the row layout as settings with one value each today (`align = "left"`, rows from the lyrics line), so
centered text or automatic line breaks can be added later without changing the song file's structure.

The `captions` command of Phase 0 and its PNGs stay as they are.

## Options

### A. How a design is described

| Option | For | Against | Recommendation |
|---|---|---|---|
| A1. Named designs (built-in TOML files) made of the parts above, with every value overridable in the song file | Choosing a design is one line; tweaking stays possible; the same idea as audio-spectrum-app's presets, which the owner knows | A fixed set of parts: a layout outside them needs code | **Recommended** |
| A2. A free layout (boxes with positions, like a page layout) | Any layout | Much more to learn and to validate; too much for two or three designs | Not recommended |
| A3. Designs only in code | Least work now | Every tweak needs a code change | Not recommended |

### B. Drawing text for video frames (deferred from ADR-002)

| Option | For | Against | Recommendation |
|---|---|---|---|
| B1. Pillow draws each text layer once (RGBA); frames are composed from cached layers | The same text engine and metrics as the caption PNGs; soft shadows with `GaussianBlur`; layers are drawn once per worker, not per frame | Composing still costs time per frame; to be measured | **Recommended** |
| B2. Skia (comes with audio-spectrum-app) | Fast composing, blur and shadows built in | A second text engine with different metrics from the caption PNGs | Fallback if B1 is too slow |

Per frame, only the caption region (about a quarter of the frame) is blended over a cached base. Phase 1 measures the
backdrop's time per frame at 1080p; the target is under 10 ms in a worker, so a video stays under its song's length
(audio-spectrum-app measured 57 % with a still photo).

### C. Credits before and after the song

| Option | For | Against | Recommendation |
|---|---|---|---|
| C1. Shown over the first and last seconds of the song (for example during the intro and outro) | The video is exactly the song; nothing changes in audio-spectrum-app or in sync | Credits share the screen with the music's start and end | **Recommended** to start |
| C2. Silent lead-in and tail added to the video (for example 4 s each) | Credits alone on screen, as with iMovie titles before the song | The audio must be padded (a temporary file in this app) and the spectrum is flat there | Not wanted (Q3) |

### D. How the owner compares designs

| Option | For | Against | Recommendation |
|---|---|---|---|
| D1. A `still` command: PNGs for chosen moments and captions, one per design, plus a side-by-side sheet | Simple; exact frames of the future video; works now | Changing a value means running the command again | **Recommended** |
| D2. A local web page with live previews (like audio-spectrum-app's GUI) | Instant feedback | A GUI before the design is settled; planned for Phase 3 | Phase 3 |

## The designs to compare

All share the frame model; the differences are in the title, caption and credits parts. Values are starting points
to adjust after the first stills.

| Design | Title | Caption | Credits | Idea |
|---|---|---|---|---|
| `classic` | Drawn large at the top center (as today's baked titles) | Opaque band at the bottom, full width, one color, left-aligned text, as today's PNGs scaled to 1920 wide | Centered lines on a dimmed frame | Today's videos, made automatically |
| `soft` | Top left, medium size, with a thin rule under it | No band: a soft dark gradient rising from the bottom, centered white text with a light shadow | Small, bottom right | Modern and quiet; the background stays visible |
| `panel` | Top center, letter-spaced | A rounded, semi-transparent panel near the bottom with the background blurred behind it ("frosted glass"), centered text | Inside the same kind of panel | Readable over busy backgrounds |

Because the background is still, the blurred area behind the panel is computed once, not per frame.

The spectrum stays roughly centered in all three; each design may suggest its own `baseline_y` and `max_height` so
the spectrum and the caption overlap as little or as much as the owner likes. Its look (preset, colors, glow) stays
the owner's choice in `[spectrum]`.

## Design of the code

| Module | Content |
|---|---|
| `design.py` | Pydantic models of the parts; built-in designs as TOML files in the package; merging a design with the song file's overrides |
| `layers.py` | Drawing each layer once: background (cover, crop, dim, blur), title, caption styles, credits; text with Pillow (B1) |
| `backdrop.py` | `LyricsBackdrop`: picklable (paths and settings only), builds its layers lazily in each worker; `frame(index, seconds, width, height)` composes base + caption with its fade |
| `still.py` | The `still` command on `audio_spectrum.render_stills(..., backdrop=...)` and the comparison sheet |

In Phase 1 the caption of a still is chosen by its line index; Phase 2 adds timing, and the same `frame` then looks
the caption up by time.

```bash
uv run lyrics-video still work/my-song/song.toml --time 62.0 --caption 4 --design classic soft panel
# writes work/my-song/stills/<design>_62.0s.png for each design and stills/compare.png side by side
```

The song file gains `audio` (the song, for the spectrum), `design`, and the sections above. Real song files and
images stay in `work/`; `examples/song.example.toml` grows with placeholders.

### Tests

Generated images, text and signals; system fonts (Hiragino), skipped where missing.

- Background: cover and crop for wide, tall and square images, never stretched; focus point; dim and blur.
- Layers: each part's position and size inside the frame and its safe margins; text that is too long shrinks or
  wraps as the part's settings say; parts that are off draw nothing.
- Backdrop: picklable; the same frames in one and in several processes; fade values at the start, middle and end of
  a fade; a still from `render_stills` equals the backdrop with the spectrum drawn over it.
- Designs: every built-in design loads and renders; song-file overrides win over the design.
- Time per frame of the backdrop at 1080p, reported (not a pass/fail test).

## Milestones and commits

| Milestone | Commit | Content |
|---|---|---|
| 0. Plan | `docs: add Phase 1 plan` | This plan (approved) |
| 1. Frame model | `feat: compose frames under the spectrum` | Parts, layers, `LyricsBackdrop`, `still` for one design, tests, user guide section |
| 2. Designs | `feat: add built-in designs and a comparison sheet` | `classic`, `soft`, `panel`, comparison sheet, measured backdrop time, ADR on text drawing for video (B) |
| 3. Choice | `docs: accept Phase 1` | Stills over the owner's background and font in `work/` (not committed), the owner's choice as the default design, `PHASE1_ACCEPTANCE.md` |

## Acceptance criteria

| Criterion | How it is checked |
|---|---|
| The owner has chosen a default design from stills over their own background, font and song | The owner's answer, recorded in the acceptance report |
| A still equals the video frame it stands for: backdrop and spectrum, at the same time | Test against `render_stills`; the same backdrop object will be used by `render_video` in Phase 3 |
| Backgrounds of any aspect ratio are covered and cropped, never stretched | Tests with generated wide, tall and square images |
| The backdrop is fast enough for Phase 3: under 10 ms per 1080p frame in a worker, or a plan to get there | Measurement in the acceptance report |
| Docs in three languages, nothing private committed | Hash check, file review, `gitleaks` |

## Questions for the owner

Answers (2026-10-31):

- Q1: the recommended options A1, B1, C1 and D1.
- Q2: the designs are checked with titles drawn by the app; a title baked into the background stays possible by
  turning the title part off.
- Q3: credits are shown over the song's first and last seconds; no silence is added. What the credits say is set in
  the song file (`[credits] lines`); the drafts use made-up lines.
- Q4: one font for everything by default, and a separate font per part where wanted, in particular for the title.
- Q5: still open (要確認): the background image, font and song for the drafts, needed by milestone 3. Milestones 1
  and 2 use generated images, system fonts and generated signals.
- Q6: the spectrum stays centered as today and may overlap the caption; designs may suggest small changes.
- Q7, Q8: no reference video or outside designs for now.
- Q9: captions stay as today (left-aligned, up to two rows), with the caption part designed so that alignment and
  row layout can be extended later.

The questions as asked:


- Q1. Options A to D: are the recommendations (A1 named designs with overrides, B1 Pillow, C1 credits over the
  song's start and end, D1 a `still` command) fine?
- Q2. Title: should the app draw the title (and maybe the artist or a subtitle), or do you prefer to keep baking it
  into the background image? Both will be possible; which one should the designs show?
- Q3. Credits: what do they say (for example music, lyrics, vocals, illustration, each with a name), how long are
  they shown, and is showing them over the first and last seconds of the song acceptable, or do you want silence
  before and after (C2)?
- Q4. Fonts: one font for everything in a song, or separate fonts for the title and credits?
- Q5. For the drafts, which background image, font and song should be used? Please put copies in `work/` (for
  example `work/design/`), or name the files. Real names and images stay out of the repository.
- Q6. Spectrum: keep it centered as today and allow it to overlap the caption, or should the designs move it up
  (for example `baseline_y` 0.45) so captions stay clear? Which preset and colors do you use today?
- Q7. Is there a past video (or a screenshot of one) to put in `work/` as a reference for `classic`?
- Q8. Are there designs you like elsewhere (for example other lyrics videos) to add as a fourth variant, or anything
  to avoid?
- Q9. Caption details: keep left alignment as today, or centered? Up to two rows as today?
