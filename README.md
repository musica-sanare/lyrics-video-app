English | [日本語](README.ja.md)

# lyrics-video-app

Makes lyrics videos for your own songs, fully offline on a Mac. A video has a still background image, the song
title, lyrics captions that fade in and out at the bottom, credits, and an audio spectrum drawn by
[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), with the song's audio. It replaces a manual
workflow of caption images layered in a video editor.

**Status:** Phase 2 (timing of the lyrics) accepted: captions are placed by time from an LRC file made with the
`sync` page. Whole videos come in Phase 3. See the [Phase 2 acceptance](docs/working/PHASE2_ACCEPTANCE.md).

## What it does today

- `lyrics-video captions` makes the caption images of the old lyrics image script from a lyrics file, for use in
  iMovie.
- `lyrics-video compare` shows a text in many fonts.
- `lyrics-video sync` opens a page in the browser to tap and adjust the times of the captions while the song plays.
- `lyrics-video still` renders frames of the future video (background, title, captions of the moment, credits and
  spectrum) in three designs, `soft` by default.

## Quick start

audio-spectrum-app must be checked out next to this repository (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # then set the font, colors and lyrics file
uv run lyrics-video captions work/my-song/song.toml         # one PNG per caption line
uv run lyrics-video compare work/my-song/song.toml          # the comparison text in several fonts
uv run lyrics-video sync work/my-song/song.toml             # time the captions in the browser
uv run lyrics-video still work/my-song/song.toml --time 60  # frames of the video at chosen times
```

Run `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, the commands, timing, the song file and moving from the old script
- [Development](docs/en/DEVELOPMENT.md): setup, tests and conventions
- [Architecture](docs/en/ARCHITECTURE.md): how the code is built and where new features fit
- [Documentation index](docs/en/README.md): every doc, including decisions and phase records

## License

[MIT](LICENSE). Songs, lyrics, images and fonts are never part of this repository.
