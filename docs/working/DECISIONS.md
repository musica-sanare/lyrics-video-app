[Docs index](../en/README.md)

# Decisions

Architecture decision records. Each one states the context, the decision and its consequences. Background for the
first ones: [Handoff](HANDOFF.md) and the [Phase 0 plan](PHASE0_PLAN.md).

## ADR-001: A separate repository that draws under audio-spectrum-app's spectrum

- Context: The owner makes lyrics videos by stacking a background image, caption images and a spectrum video in
  iMovie. audio-spectrum-app is meant to stay a reusable component (its ADR-008) and gained an additive API for this
  purpose in its version 0.5.0 (its ADR-013).
- Decision: Lyrics, captions, title, credits and layout live in this repository. Videos are made by implementing
  audio-spectrum-app's `Backdrop` (a picklable object returning the picture under the spectrum for frame `n` at time
  `n / fps`) and calling `render_video`, which handles sync, worker processes, progress, cancellation, parts of
  songs, audio and safe output. Only its public API (`audio_spectrum`) is used. It is a path dependency
  (`../audio-spectrum-app`, editable, `>=0.5.0`) while both repositories change.
- Consequences: One render path and one sync invariant for both apps; previews (`Preview.frames`) equal video
  frames. A checkout needs audio-spectrum-app next to it. Changes needed there are planned in its own workspace,
  never made from here. Pinning the tag `v0.5.0` (a Git dependency) is postponed until both repositories are
  public. Rejected: lyrics features inside audio-spectrum-app; a second render loop on its internals.

## ADR-002: Pillow for the caption PNGs

- Context: The old caption script (2022) uses Pillow and `ImageDraw.textsize`, removed in Pillow 10. The caption
  PNGs must keep working in iMovie until this app makes whole videos. Skia is available through audio-spectrum-app.
- Decision: The caption PNGs are drawn with Pillow, with the old fitting and layout rules and `textbbox` in place
  of `textsize`. A check with Pillow 13.0.0 gave the same font size and layout as the old output, with glyphs at most
  about 1 px apart ([Phase 0 plan](PHASE0_PLAN.md), "Feasibility check"). Text drawing stays in one module.
- Consequences: Pillow is a dependency next to Skia. Skia's metrics would have changed sizes and positions. Which
  library draws captions inside videos is decided in Phase 1 with the caption design.

## ADR-003: One TOML file per song; the old lyrics format

- Context: The old script reads one TOML file for all settings and a lyrics text file with one caption per line and
  `;` between two rows. Timing does not exist yet (Phase 2).
- Decision: Each song has one TOML file, validated with pydantic, with paths relative to it and `~` expanded; later
  phases add sections to the same file. The lyrics file keeps the old format. Colors are `#RRGGBB` or a path to an
  image whose center pixel is used, so old sample images still work. Only `*.example.toml` files are committed.
- Consequences: Settings shared by songs are repeated for now; shared defaults can be added later. The timing format
  is chosen in Phase 2.
