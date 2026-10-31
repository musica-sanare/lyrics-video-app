English | [日本語](README.ja.md) | [Español](README.es.md)

# lyrics-video-app

Makes lyrics videos for your own songs, fully offline on a Mac: a still background image, the song title, lyrics
captions that fade in and out at the bottom, credits, and an audio spectrum drawn by
[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), with the song's audio. It replaces a manual
workflow of caption images layered in a video editor.

**Status:** Phase 0 (foundation). The command is set up; making caption images from a lyrics file comes next. See
the [Phase 0 plan](docs/working/PHASE0_PLAN.md).

## Quick start

audio-spectrum-app must be checked out next to this repository (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
uv run lyrics-video --version
uv run pytest
```

## Documentation

- [Development](docs/en/DEVELOPMENT.md): setup, tests and conventions
- [Documentation index](docs/en/README.md): every doc, including decisions and phase records

## License

[MIT](LICENSE). Songs, lyrics, images and fonts are never part of this repository.
