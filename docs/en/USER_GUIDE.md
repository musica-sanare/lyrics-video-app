English | [日本語](../ja/USER_GUIDE.md) | [Español](../es/USER_GUIDE.md) · [Docs index](README.md)

# User guide

How to set up lyrics-video-app and make caption images for a song. Whole videos come in later phases.

## 1. Setup

```bash
brew install uv ffmpeg
uv sync
```

audio-spectrum-app must be checked out next to this repository (`../audio-spectrum-app`); see
[Development](DEVELOPMENT.md) §1. Everything runs offline.

## 2. A folder per song

Keep each song in its own folder inside `work/`, which Git ignores, or anywhere outside the repository:

```text
work/my-song/
  song.toml      the song file: lyrics, colors, font, output folders
  lyrics.txt     one caption per line
  compare.txt    a line or two to try in several fonts (optional)
```

Start from the examples: copy `examples/song.example.toml` to `work/my-song/song.toml` and
`examples/lyrics.example.txt` to `work/my-song/lyrics.txt`, then edit them.

### The lyrics file

- UTF-8 text, one caption per line.
- `;` splits a caption into two rows (`first row;second row`). A line with more than one `;` is an error. Another
  separator can be set in the song file.
- Empty lines are skipped, but they still count for the numbers in the file names, as before.

## 3. Caption images: `captions`

```bash
uv run lyrics-video captions work/my-song/song.toml
```

Writes one PNG per caption into the output folder (`captions/` next to the song file by default), named
`lyrics_<line index>.png`, where the line index counts from 0 and includes empty lines. Each image is a band in the
background color with the caption in the text color, left-aligned:

- The font size starts at 80 and shrinks in steps of 2 until every row fits with a margin of 50 px in each
  direction. Both rows of a caption use the same size.
- One row is centered vertically; two rows sit in the upper and lower halves.

These are the rules of the old lyrics image script, so the images can be used in iMovie as before: the background
image fills the frame and each caption image goes at the bottom, full width, with fades.

Existing images are never replaced silently: if any output file exists, nothing is written and the files are listed.
Add `--overwrite` to replace them. If the new lyrics have fewer lines, delete the old folder first so no stale images
remain.

## 4. Choosing a font: `compare`

```bash
uv run lyrics-video compare work/my-song/song.toml
uv run lyrics-video compare work/my-song/song.toml --font-dir ~/path/to/fonts --font /System/Library/Fonts/ヒラギノ明朝\ ProN.ttc
```

Draws every line of the comparison text (`compare.txt`) in every font, with the song's size and colors, into the
comparison folder (`compare/` by default):

- `<font file name>_<line index>.png` for each font and line;
- `contact_sheet.png`: the first line in all fonts, one under the other, each under its font's name.

The fonts are `compare.fonts` and every font file in `compare.font_dirs` (searched in subfolders too). `--font` and
`--font-dir` (each repeatable) replace both lists for one run. Font files are `.ttf`, `.otf`, `.ttc` and `.otc`; the
first face of a collection is used. `--overwrite` works as for `captions`.

## 5. The song file

A TOML file. Paths are relative to the song file; `~` is the home folder. Every key is optional except
`captions.font` for `captions`.

| Key | Default | Meaning |
|---|---|---|
| `lyrics` | `"lyrics.txt"` | The lyrics file |
| `captions.output_dir` | `"captions"` | Folder for the caption images |
| `captions.size` | size of the background image, else `[1440, 232]` | Width and height of each image |
| `captions.background` | `"#000000"` | Background color: `"#RRGGBB"`, or an image file whose center pixel is the color |
| `captions.text_color` | `"#FFFFFF"` | Text color, the same way |
| `captions.font` | none | The font file |
| `captions.font_index` | `0` | The face in a `.ttc` collection |
| `captions.separator` | `";"` | Splits a caption into two rows |
| `captions.file_prefix` | `"lyrics"` | Start of the file names |
| `compare.text` | `"compare.txt"` | The text to compare fonts with |
| `compare.output_dir` | `"compare"` | Folder for the comparison images |
| `compare.fonts` | `[]` | Font files to compare |
| `compare.font_dirs` | `[]` | Folders whose fonts are all compared |

Fonts are not part of this repository and are never copied into it; the song file only points to them. Real song
files stay in `work/` or outside the repository.

## 6. Moving from the old lyrics image script

| Old `conf.toml` | Song file |
|---|---|
| `input.background_color` (a sample PNG) | `captions.background = "back.png"` (the same PNG, or its color as `"#RRGGBB"`); the image size becomes the caption size |
| `input.text_color` (a sample PNG) | `captions.text_color` |
| `input.lyrics_text_single` | `lyrics` |
| `input.lyrics_text_multi` | `compare.text` |
| `output.output_dir_single`, `output_dir_multi` | `captions.output_dir`, `compare.output_dir` |
| `font.font_path_single`, `font_path_multi` | `captions.font`, `compare.fonts` |
| `separator.separator` | `captions.separator` |
| `prefix.prefix_image_num` | `captions.file_prefix` |
| `margin.margin_text_x`, `margin_text_y` | Fixed at 50 |

Instead of the old prompt (0 or 1), choose the command: `captions` or `compare`.

Differences from the old script:

- The same inputs give the same sizes, colors, font sizes, layout and file names. Glyphs may sit about 1 px apart
  in places, from changes in the font libraries; the images look the same.
- A comparison image is named after the whole font file name (`my-font-2.04_0.png`, where the old script cut the
  name at the first dot), and the contact sheet is new.
- Existing images are not overwritten without `--overwrite`, and an error in a song file, lyrics file or font
  writes no images.

## 7. Errors

| Exit code | Meaning |
|---|---|
| 0 | Done |
| 1 | Failed; the message on stderr says why (song file, lyrics file, font, a caption that does not fit, existing output) |
| 2 | Wrong command-line usage |

Errors name the file and, for the lyrics, the line number. All images are drawn before any is written, so these
errors write nothing; each file is written completely or not at all.
