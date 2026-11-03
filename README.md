English | [日本語](README.ja.md)

# lyrics-video-app

Makes lyrics videos for your own songs, fully offline on a Mac. A video has a still background image, the song
title, lyrics captions that fade in and out at the bottom, credits, and an audio spectrum drawn by
[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), with the song's audio. It replaces a manual
workflow of caption images layered in a video editor.

**Status:** Phase 6 (everyday use) accepted, version 0.5.0: the app starts from the Dock, makes a new song from files
in any folder, times it, sets its whole look including the spectrum, previews the whole video in seconds and renders
it, all on one page. See the [Phase 6 acceptance](docs/working/PHASE6_ACCEPTANCE.md).

## What it does today

- Lyrics Video.app (made by `lyrics-video install-app`) starts the app from the Dock: a start page with recent songs,
  and new songs made from an audio file, a background image and a lyrics text in any folder.
- `lyrics-video sync` opens a page in the browser to tap and adjust the times of the captions while the song plays,
  change the design and the spectrum with a live still, save the look as a named design for other songs, check
  everything in a quick preview video, and render the video from there.
- `lyrics-video still` renders frames of the future video (background, title, captions of the moment, credits and
  spectrum) in three designs, `soft` by default.
- `lyrics-video render` renders the whole lyrics video with the song's audio.

## Quick start

```bash
brew install uv ffmpeg
git clone https://github.com/musica-sanare/lyrics-video-app
cd lyrics-video-app
uv sync                           # also fetches audio-spectrum-app 0.5.0 from GitHub
uv run lyrics-video install-app   # Lyrics Video.app in ~/Applications; drag it to the Dock
```

Click the app, choose "New song…" and pick your audio, background image and lyrics. The
[User guide](docs/en/USER_GUIDE.md) §2 walks through a whole song. The same works from the terminal:

```bash
uv run lyrics-video sync path/to/song.toml               # time the captions and set the look in the browser
uv run lyrics-video still path/to/song.toml --time 60    # frames of the video at chosen times
uv run lyrics-video render path/to/song.toml             # the whole video, in videos/ next to the song file
```

Run `uv run pytest` for the tests.

## Documentation

- [User guide](docs/en/USER_GUIDE.md): setup, timing, stills, the whole video, designs and the song file
- [Development](docs/en/DEVELOPMENT.md): setup, tests and conventions
- [Architecture](docs/en/ARCHITECTURE.md): how the code is built and where new features fit
- [Documentation index](docs/en/README.md): every doc, including decisions and phase records

## License

[MIT](LICENSE). Songs, lyrics, images and fonts are never part of this repository.
