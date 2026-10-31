# Handoff: starting lyrics-video-app

Written on 2026-10-31 in the audio-spectrum-app workspace, where this repository was proposed and agreed with the
owner. It records what was decided there so work here can start without that conversation. Items still open are
marked `要確認`.

## 1. Purpose

Make the owner's lyrics videos from a song with as little manual work as possible. The ideal is "audio, background
image and lyrics in, finished video out"; the hard part is the timing of the lyrics (section 4).

## 2. Today's manual workflow

1. A Python script (2022, see `CLAUDE.local.md`) turns a lyrics text file into one PNG per caption: one line of the
   file is one caption; `;` splits it into two rows. Each image is a band (1440 × 232; later songs 1500 × 241 or 243) filled with a background color,
   with left-aligned text in a text color (both taken from the center pixel of two small sample images) and a font
   size shrunk until the text fits with a margin. Settings live in a TOML file. It also renders one caption in many
   fonts side by side to compare them.
2. In iMovie: the background image fills the frame; the song title is part of that image (placed at its top); each
   caption image is placed at the very bottom, full width, with about 2 s fades, timed by hand; credits appear before
   and after the song.
3. The result is exported, and the spectrum video from audio-spectrum-app is laid over it with a chroma key, centered.
   The spectrum may cover the lyrics now and then; that is fine.

Notes on the old script: it uses `ImageDraw.textsize`, which Pillow removed in version 10, so it probably no longer
runs as is; its configuration holds absolute font paths that include the user name.

## 3. The owner's answers

| Topic | Answer |
|---|---|
| Lyrics timing | Many songs are not sung by NEUTRINO (the owner sings some). MusicXML scores exist but may not match the audio exactly |
| Backgrounds | Still images only so far |
| Layout | Spectrum roughly centered, over the lyrics; lyrics band at the bottom; credits before and after the song |
| Title and design | Title is baked into the background image today; the owner is open to a modern but simple, readable design and wants to compare concrete images before choosing |
| Fonts | One font per song; fonts must not be redistributed through the repository |
| Output | 1920 × 1080 for YouTube |
| Repository | Name `lyrics-video-app`; private at first, but always safe to make public. The owner creates the GitHub remote and links it by hand |
| Old script | Kept untouched as reference |

## 4. Decisions and direction

- **Separate repository** for the lyrics video app; audio-spectrum-app stays a reusable component (its ADR-008).
- **Dependency:** audio-spectrum-app as a path dependency (`../audio-spectrum-app`, editable) while both change.
  Its release `v0.5.0` (the backdrop API) is tagged, so the dependency can later pin that tag instead.
- **Composition:** this app implements an audio-spectrum-app `Backdrop`: a picklable object whose
  `frame(index, seconds, width, height)` returns the RGB picture under the spectrum (background, title, the caption of
  that time with its fade, credits). `render_video(RenderJob(..., backdrop=...))` then draws the spectrum on top in its
  worker processes and handles exact sync, progress, cancellation, parts of songs (`start`/`duration`), audio and safe
  output. Previews use `Preview.frames(..., backdrop=...)` and are identical to video frames. See that repository's
  ADR-013 and Phase 4 reports.
- **Measured costs there** (M1, 1080p): drawing the spectrum about 20 ms per frame; blending a picture in NumPy in the
  main process about 46 ms per frame (avoid; draw or blend inside the backdrop, which runs in the workers); a 317.7 s
  song over a still photo rendered in 182.1 s (57 % of its length).
- **Backgrounds** are scaled to cover the frame and cropped, never stretched (the minimal example in
  audio-spectrum-app's user guide stretches; do not copy that part).
- **Timing** (proposed): first a tap-to-sync page (play the song, press a key at the start of each line, then adjust
  with a waveform and previews; store as LRC or JSON). MusicXML import as a rough first draft for songs that have a
  score, later. Automatic alignment from the audio (vocal separation plus speech alignment) only as a later
  experiment: accuracy on sung Japanese is uncertain and the dependencies are large.
- **Interface:** a CLI first, then a local web GUI in the style of audio-spectrum-app (FastAPI, plain HTML/JS, pages
  in Japanese, English and Spanish), possibly showing the spectrum settings through audio-spectrum-app's public API.

## 5. Proposed phases (to be planned and approved one at a time)

| Phase | Content |
|---|---|
| 0 | Repository foundation that is safe to publish (README in three languages, docs structure, example config, tests, `uv` project with the path dependency); the lyrics image generator rebuilt as a CLI that runs on current Pillow (or Skia, which comes with audio-spectrum-app) and reproduces today's PNG captions closely enough to keep the iMovie workflow working |
| 1 | Design: title, lyrics band, credits and spectrum placement as configurable parts; two or three variants rendered as stills over the owner's own background and font, chosen by the owner |
| 2 | Timing: tap-to-sync and fine adjustment, stored next to the lyrics |
| 3 | The whole video in one step (backdrop plus audio-spectrum-app), CLI and GUI |
| 4 | Optional: MusicXML draft timing, automatic alignment experiments |

## 6. Public-repository safety specific to this repository

- Never commit: lyrics, songs, background or title images, fonts, rendered captions or videos, real configuration
  files, or absolute paths with the user name. `.gitignore` already covers `work/`, media, image and font files,
  every `*.toml` except `pyproject.toml` and `*.example.toml`, and `CLAUDE.local.md`.
- Commit only `*.example.toml` configuration with placeholder paths.
- Tests use generated text and images and macOS system fonts (skipped where missing).
- Before the repository is made public: scan the whole history with a secret scanner and report the result.
- Song and project names in docs and tests: use made-up examples.

## 7. Questions for Phase 0 (要確認)

- Text rendering: Pillow (as the old script) or Skia (already a dependency through audio-spectrum-app, and used for
  every other drawing)? How closely must new captions match the old PNGs?
- Lyrics file format: keep the old one (one caption per line, `;` for two rows) and add timing separately, or move
  to a format that holds both (for example LRC)?
- Caption band: keep 1440 × 232 PNGs for the iMovie workflow during the transition, or go straight to captions drawn
  at video resolution?
- Configuration: one file per song (background, font, colors, lyrics, timing) or a shared default plus per-song
  overrides?
