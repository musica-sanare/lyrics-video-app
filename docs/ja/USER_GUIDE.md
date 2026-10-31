<!-- source: docs/en/USER_GUIDE.md blob 517778fd4a7bdef2a55c879358818038d0f4fbc1 -->
[English](../en/USER_GUIDE.md) | 日本語 | [Español](../es/USER_GUIDE.md) · [目次に戻る](README.md)

> この文書は[英語版](../en/USER_GUIDE.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# ユーザーガイド

lyrics-video-app のセットアップ、曲の字幕画像の作り方、動画のフレームの確認方法です。動画全体の書き出しは後のフェーズで加わります。

## 1. セットアップ

```bash
brew install uv ffmpeg
uv sync
```

audio-spectrum-app をこのリポジトリの隣（`../audio-spectrum-app`）に置いておく必要があります。
[開発](DEVELOPMENT.md) §1 を参照してください。すべてオフラインで動きます。

## 2. 曲ごとのフォルダ

曲ごとに、Git の対象外の `work/` の中か、リポジトリの外にフォルダを作ります。

```text
work/my-song/
  song.toml      曲ファイル：歌詞、色、フォント、出力先
  lyrics.txt     1 行に 1 字幕
  compare.txt    いくつかのフォントで試す 1〜2 行（任意）
```

例から始めるのが簡単です。`examples/song.example.toml` を `work/my-song/song.toml` に、
`examples/lyrics.example.txt` を `work/my-song/lyrics.txt` にコピーして編集します。

### 歌詞ファイル

- UTF-8 のテキストで、1 行が 1 つの字幕です。
- `;` で字幕を 2 行に分けます（`1 行目;2 行目`）。`;` が 2 つ以上ある行はエラーです。区切り文字は曲ファイルで変えられます。
- 空行は飛ばしますが、これまでどおりファイル名の番号には数えます。

## 3. 字幕画像：`captions`

```bash
uv run lyrics-video captions work/my-song/song.toml
```

字幕ごとに 1 枚の PNG を出力先（既定では曲ファイルの隣の `captions/`）に書き出します。ファイル名は
`lyrics_<行番号>.png` で、行番号は 0 から数え、空行も含みます。各画像は背景色の帯で、字幕が文字色で左寄せに描かれます。

- 文字の大きさは 80 から始め、どの行も縦横それぞれ 50 px の余白を残して収まるまで 2 ずつ小さくします。
  2 行の字幕は両方の行が同じ大きさです。
- 1 行は上下の中央に、2 行は上半分と下半分に置きます。

これは旧歌詞画像スクリプトと同じ決まりなので、これまでどおり iMovie で使えます。背景画像を画面いっぱいに置き、
各字幕画像を画面の一番下に横幅いっぱいでフェード付きで置きます。

既存の画像を黙って置き換えることはありません。出力先のファイルが 1 つでも存在すると、何も書き出さずにその一覧を
表示します。置き換えるには `--overwrite` を付けます。新しい歌詞の行数が減った場合は、古い画像が残らないよう、
先に古いフォルダを削除してください。

## 4. フォント選び：`compare`

```bash
uv run lyrics-video compare work/my-song/song.toml
uv run lyrics-video compare work/my-song/song.toml --font-dir ~/path/to/fonts --font /System/Library/Fonts/ヒラギノ明朝\ ProN.ttc
```

比較用テキスト（`compare.txt`）のすべての行を、曲と同じ大きさと色で、すべてのフォントで比較用フォルダ
（既定では `compare/`）に描きます。

- フォントと行ごとに `<フォントのファイル名>_<行番号>.png`
- `contact_sheet.png`：1 行目を全フォントで縦に並べ、それぞれの上にフォント名を添えた一覧画像

対象のフォントは、`compare.fonts` と、`compare.font_dirs` の中（サブフォルダも含む）のすべてのフォントファイルです。
`--font` と `--font-dir`（どちらも繰り返し指定可）を付けると、その回だけ両方の一覧を置き換えます。フォントファイルは
`.ttf`、`.otf`、`.ttc`、`.otc` で、コレクションは最初のフェイスを使います。`--overwrite` は `captions` と同じです。

## 5. 動画の静止画とデザイン：`still`

```bash
uv run lyrics-video still work/my-song/song.toml --time 3 62.5 --caption 4
```

指定した時刻（曲の秒数）に動画が映すフレームを、曲ファイルの隣の `stills/` に `<デザイン>_<時刻>s.png` として書き出します。
背景画像、曲名、字幕、クレジット、その時点のスペクトラムを重ねたもので、動画のフレームとまったく同じです。歌詞に
タイミングが付くまでは、静止画には字幕を 1 つだけ表示します。`--caption` で行番号（字幕画像の名前と同じ数え方）を指定し、
省略すると最初の字幕、`--no-caption` で字幕なしになります。`--overwrite` は `captions` と同じです。

デザインを見比べるには `--design` で名前を並べます。曲ファイルのデザインの上書き（曲名のフォントなど）はどのデザインにも
適用され、`compare_<時刻>s.png` に半分の大きさで縦に並べて書き出します。

```bash
uv run lyrics-video still work/my-song/song.toml --time 62.5 --design classic soft panel
```

フレームは下から順に次の部品でできています。

| 部品 | 内容 |
|---|---|
| 背景 | `background_image`。画面を覆うように拡大して切り取り、引き伸ばしません。画像がなければ黒 |
| 曲名 | `title` と `subtitle`。アプリが描きます |
| 字幕 | その時点の字幕。フェードイン・アウトします |
| クレジット | `credits` の各行。曲の最初と最後の数秒に、暗くした画面の上に表示します |
| スペクトラム | `[spectrum]` のプリセットと上書き設定で audio-spectrum-app が描きます |

部品の見た目をまとめたものが**デザイン**です。組み込みのデザイン：

| デザイン | 曲名 | 字幕 | クレジット |
|---|---|---|---|
| `classic` | 大きく、上部中央 | 画面下端の不透明な帯。旧字幕画像の決まりで描きます | 暗くした画面の中央 |
| `soft` | 小さく、左上。細い線付き | 下から立ち上がる柔らかい陰の上 | 小さく、右下 |
| `panel` | 字間を広げて、上部中央 | 下寄りの、すりガラス風の角丸の枠の中（背景をぼかしています） | 中央、同じ種類の枠の中 |

どのデザインでも、字幕は今と同じく左寄せで 2 行までです。`design = "classic"` で選ぶか、自分のデザイン
ファイルを `design = "my-design.toml"` で指定します。一部の値だけ変えるには、デザインの `name` と変えたい部品を
`[design]` テーブルに書きます。

```toml
[design]
name = "classic"

[design.title]
font = "~/path/to/title-font.otf"   # 曲名だけ fonts.default と別のフォントにする
size = 96

[design.caption]
band_color = "#101820"
```

| 部品 | キー（大きさは高さ 1080 ピクセルの画面でのピクセル数で、動画の高さに合わせて拡大縮小します） |
|---|---|
| `background` | `focus`（`[x, y]`、0〜1。切り取るときに残す位置）、`dim`（0〜1）、`blur` |
| `title` | `enabled`、`position`（`"top-center"`、`"top-left"`）、`font`、`size`、`subtitle_size`、`color`、`margin`、`gap`、`letter_spacing`、`rule`、`rule_thickness`、`rule_gap`、`shadow` |
| `caption` | `style`（`"band"`、`"gradient"`、`"panel"`）、`align`（`"left"`）、`font`、`text_color`、`fade_seconds`。帯：`band_color`、`band_opacity`、`band_height`。陰と枠：`size`（最大の文字の大きさ）、`line_spacing`、`margin_x`、`margin_bottom`、`gradient`、`panel`、`shadow` |
| `credits` | `enabled`、`font`、`size`、`color`、`line_spacing`、`position`（`"center"`、`"bottom-right"`）、`margin_x`、`margin_bottom`、`dim`、`panel`、`show_seconds`、`fade_seconds`、`shadow` |
| `spectrum` | `set`：曲ファイルの `[spectrum] set` より先に適用するプリセットの上書き |
| `shadow`（`title`、`caption`、`credits` の中） | `blur`（0 で影なし）、`offset`、`color`、`opacity` |
| `gradient`（`caption` の中） | `height`、`color`、`opacity`（下端での不透明度） |
| `panel`（`caption`、`credits` の中） | `color`、`opacity`（色の濃さ）、`blur`（背後のぼかし）、`radius`、`padding`（`[x, y]`） |

どの部品も、自分の `font` を指定しない限り `fonts.default` を使います。色は `"#RRGGBB"` で書きます。

## 6. 曲ファイル

TOML ファイルです。パスは曲ファイルからの相対パスで、`~` はホームフォルダです。`captions` で使う `captions.font`
と `still` で使う `audio` 以外のキーはすべて省略できます。

| キー | 既定値 | 意味 |
|---|---|---|
| `lyrics` | `"lyrics.txt"` | 歌詞ファイル |
| `audio` | なし | 曲の音声（スペクトラム用、`still`） |
| `background_image` | なし | 動画の背景画像 |
| `title`、`subtitle` | `""` | 曲名と、その下の 1 行 |
| `credits` | `[]` | クレジットの各行 |
| `design` | `"classic"` | デザイン名かデザインファイル、または `name` と上書きを書いた `[design]` テーブル（5 節） |
| `fonts.default` | なし | 自分のフォントを指定しない、動画のすべての部品のフォント |
| `spectrum.preset` | `"default"` | audio-spectrum-app のプリセット名かプリセットファイル |
| `spectrum.set` | `[]` | プリセットの上書き（audio-spectrum-app の `--set` と同じ） |
| `video.width`、`video.height`、`video.fps` | `1920`、`1080`、`30` | フレームの大きさとフレームレート |
| `captions.output_dir` | `"captions"` | 字幕画像の出力先 |
| `captions.size` | 背景画像の大きさ、なければ `[1440, 232]` | 各画像の幅と高さ |
| `captions.background` | `"#000000"` | 背景色：`"#RRGGBB"`、または中心のピクセルの色を使う画像ファイル |
| `captions.text_color` | `"#FFFFFF"` | 文字色（指定方法は同じ） |
| `captions.font` | なし | フォントファイル |
| `captions.font_index` | `0` | `.ttc` コレクション内のフェイス番号 |
| `captions.separator` | `";"` | 字幕を 2 行に分ける文字 |
| `captions.file_prefix` | `"lyrics"` | ファイル名の先頭 |
| `compare.text` | `"compare.txt"` | フォント比較に使うテキスト |
| `compare.output_dir` | `"compare"` | 比較画像の出力先 |
| `compare.fonts` | `[]` | 比較するフォントファイル |
| `compare.font_dirs` | `[]` | 中のフォントをすべて比較するフォルダ |

フォントはこのリポジトリに含まれず、コピーもされません。曲ファイルはその場所を指すだけです。実際の曲ファイルは
`work/` かリポジトリの外に置きます。

## 7. 旧歌詞画像スクリプトからの移行

| 旧 `conf.toml` | 曲ファイル |
|---|---|
| `input.background_color`（見本 PNG） | `captions.background = "back.png"`（同じ PNG、またはその色を `"#RRGGBB"` で）。画像の大きさが字幕の大きさになります |
| `input.text_color`（見本 PNG） | `captions.text_color` |
| `input.lyrics_text_single` | `lyrics` |
| `input.lyrics_text_multi` | `compare.text` |
| `output.output_dir_single`、`output_dir_multi` | `captions.output_dir`、`compare.output_dir` |
| `font.font_path_single`、`font_path_multi` | `captions.font`、`compare.fonts` |
| `separator.separator` | `captions.separator` |
| `prefix.prefix_image_num` | `captions.file_prefix` |
| `margin.margin_text_x`、`margin_text_y` | 50 で固定 |

旧版の入力（0 か 1）の代わりに、コマンド `captions` か `compare` を選びます。

旧スクリプトとの違い：

- 同じ入力からは、同じ大きさ、色、文字の大きさ、配置、ファイル名になります。フォントライブラリの変更により、
  ところどころで字が 1 px ほどずれることがありますが、見た目は同じです。
- 比較画像の名前にはフォントのファイル名全体を使います（`my-font-2.04_0.png`。旧版は最初のドットで切っていました）。
  一覧画像は新しく加わりました。
- `--overwrite` なしでは既存の画像を上書きしません。曲ファイル、歌詞ファイル、フォントにエラーがあると、画像は
  1 枚も書き出されません。

## 8. エラー

| 終了コード | 意味 |
|---|---|
| 0 | 完了 |
| 1 | 失敗。理由は標準エラー出力のメッセージに出ます（曲ファイル、歌詞ファイル、フォント、画像、曲、収まらない字幕、既存の出力） |
| 2 | コマンドラインの使い方の誤り |

エラーにはファイル名と、歌詞の場合は行番号が出ます。すべての画像を描き終えてから書き出すので、これらのエラーでは何も
書き出されません。各ファイルは完全に書き出されるか、まったく書き出されないかのどちらかです。
