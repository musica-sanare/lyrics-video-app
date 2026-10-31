English | [日本語](README.ja.md) | [Español](README.es.md)

# lyrics-video-app

Makes lyrics videos for your own songs, fully offline on a Mac: a still background image, the song title, lyrics
captions that fade in and out at the bottom, credits, and an audio spectrum drawn by
[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), with the song's audio. It replaces a manual
workflow of caption images layered in a video editor.

**Status:** Phase 0. `lyrics-video captions` makes the caption images of the old lyrics image script from a lyrics
file, for use in iMovie, and `lyrics-video compare` shows a text in many fonts. Whole videos come in later phases.
Phase 0 is delivered and waits for the owner's acceptance: see the [Phase 0 acceptance](docs/working/PHASE0_ACCEPTANCE.md).

## Quick start

audio-spectrum-app must be checked out next to this repository (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # then set the font, colors and lyrics file
uv run lyrics-video captions work/my-song/song.toml         # one PNG per caption line
uv run lyrics-video compare work/my-song/song.toml          # the comparison text in several fonts
```

Run `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, the commands, the song file and moving from the old script
- [Development](docs/en/DEVELOPMENT.md): setup, tests and conventions
- [Documentation index](docs/en/README.md): every doc, including decisions and phase records

## License

[MIT](LICENSE). Songs, lyrics, images and fonts are never part of this repository.
