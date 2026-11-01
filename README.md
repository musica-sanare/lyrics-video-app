English | [日本語](README.ja.md)

# lyrics-video-app

Makes lyrics videos for your own songs, fully offline on a Mac. A video has a still background image, the song
title, lyrics captions that fade in and out at the bottom, credits, and an audio spectrum drawn by
[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), with the song's audio. It replaces a manual
workflow of caption images layered in a video editor.

**Status:** Phase 4 (a preview of the video and design settings on the page) accepted, version 0.3.0: the `sync`
page times the song, sets its design, previews the whole video in seconds and renders it. See the
[Phase 4 acceptance](docs/working/PHASE4_ACCEPTANCE.md).

## What it does today

- `lyrics-video sync` opens a page in the browser to tap and adjust the times of the captions while the song plays,
  change the design with a live still, check both in a quick preview video, and render the video from there.
- `lyrics-video still` renders frames of the future video (background, title, captions of the moment, credits and
  spectrum) in three designs, `soft` by default.
- `lyrics-video render` renders the whole lyrics video with the song's audio.

## Quick start

audio-spectrum-app must be checked out next to this repository (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # then set the song, image, font and lyrics
uv run lyrics-video sync work/my-song/song.toml             # time the captions in the browser
uv run lyrics-video still work/my-song/song.toml --time 60  # frames of the video at chosen times
uv run lyrics-video render work/my-song/song.toml           # the whole video, in work/my-song/videos/
```

Run `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, timing, stills, the whole video, designs and the song file
- [Development](docs/en/DEVELOPMENT.md): setup, tests and conventions
- [Architecture](docs/en/ARCHITECTURE.md): how the code is built and where new features fit
- [Documentation index](docs/en/README.md): every doc, including decisions and phase records

## License

[MIT](LICENSE). Songs, lyrics, images and fonts are never part of this repository.
