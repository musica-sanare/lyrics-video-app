# Project instructions for Claude Code

## Product
lyrics-video-app makes lyrics videos for the owner's songs, fully offline on the owner's Mac: a still background
image, the song title, lyrics captions at the bottom that fade in and out, credits, and an audio spectrum drawn by
the owner's audio-spectrum-app (a sibling repository), with the song's audio. It replaces a manual workflow (a lyrics
image script plus layering in iMovie).

## Read first
Before changing code or docs, read:
- [docs/working/HANDOFF.md](docs/working/HANDOFF.md) (why this repository exists, decisions so far, proposed phases)
- `docs/en/README.md` (docs index), once it exists
- [docs/en/ARCHITECTURE.md](docs/en/ARCHITECTURE.md) (layers, invariants, where new features fit)
- `docs/working/DECISIONS.md` and the current phase plan (`docs/working/PHASE<N>_PLAN.md`), once they exist
- `CLAUDE.local.md` if present (local paths, never committed)

If any path does not exist, report it rather than silently inventing its contents.

## Project principles
- Frame `n` shows the audio at time `n / fps`; captions and credits are placed by time, never by real-time playback.
- Songs, lyrics, background images, fonts, rendered images and videos never enter the repository. Keep them in the
  ignored `work/` directory or outside the repository. Fonts are third-party files and are not redistributed.
- Only example configuration files (`*.example.toml`) are committed; real configuration stays local. Paths in tracked
  files are relative or start with `~/`.
- Normal use is fully offline: no network connection.
- The spectrum comes from audio-spectrum-app's public API only (`audio_spectrum`), in particular
  `RenderJob.backdrop`, which draws the spectrum over this app's frames. Never copy its internals here and never edit
  that repository from this one; changes it needs are planned in its own workspace.
- The old lyrics image script is local reference material only (see `CLAUDE.local.md`): read it, do not modify it,
  and do not bring its Git history or configuration into this repository.

## Engineering
- Python 3.13 managed with `uv`; ffmpeg is an external tool (`brew install ffmpeg`).
- audio-spectrum-app is a path dependency (`../audio-spectrum-app`, editable) while both change; it can later pin a
  tagged release (the first is `v0.5.0`).
- Automated tests use generated text, images and signals only, never real songs, lyrics or third-party fonts. Tests
  that need a font use macOS system fonts and are skipped where they are missing.

## Workflow
- Work in phases: write a plan in `docs/working/PHASE<N>_PLAN.md`, get the owner's approval, then implement, measure and
  propose a commit per milestone. Each phase ends with `docs/working/PHASE<N>_ACCEPTANCE.md`.
- Commit on `main` until the owner creates a `dev` branch after the first push.
- The repository starts private but must be safe to make public at any time; scan the full history with a secret
  scanner (for example gitleaks) before it is made public.

## Overrides of shared rules
None.
