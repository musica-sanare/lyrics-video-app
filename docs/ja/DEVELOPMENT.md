<!-- source: docs/en/DEVELOPMENT.md blob d32e5b193467b33f32f42cc6904df05a215fe6ab -->
[English](../en/DEVELOPMENT.md) | 日本語 · [目次に戻る](README.md)

> この文書は[英語版](../en/DEVELOPMENT.md)の翻訳。内容が異なる場合は英語版が優先する。

# 開発

lyrics-video-app のコードを扱うためのセットアップ、確認方法、規約をまとめる。コードやドキュメントを変える前に読む。
曲に使うだけなら[ユーザーガイド](USER_GUIDE.md)を見る。

## 1. セットアップ

```bash
brew install uv ffmpeg
git clone https://github.com/musica-sanare/audio-spectrum-app ../audio-spectrum-app   # 最初に一度だけ、このリポジトリの隣に
uv sync
```

- Python 3.13 とすべての依存は `uv` で管理する（`pyproject.toml`、`uv.lock`）。
- audio-spectrum-app はパス依存（`../audio-spectrum-app`、editable、バージョン 0.5.0 以上）なので、向こうの変更は
  再インストールなしで反映される
  （[ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum)、英語のみ）。
  使ってよいのは公開 API、つまり `audio_spectrum` がエクスポートする名前だけ。
- 依存は `uv add <package>` で追加する。数は少なく、広く使われているものにとどめる。

## 2. テスト

```bash
uv run pytest
```

テストには生成したテキスト・画像・信号（`tests/signals.py`）だけを使い、実際の曲、歌詞、第三者のフォントは使わない。
フォントが要るテストは macOS のシステムフォントを使い、フォントがない環境ではスキップする。動画のテストは ffmpeg がなければスキップする。
`sync` のページ自体（`src/lyrics_video/web/static/`）はブラウザで手で確かめる。

| ファイル | 対象 |
|---|---|
| `test_lyrics.py` | 歌詞ファイル：行番号、行の分割、区切り文字、エラー |
| `test_config.py` | 曲ファイル：既定値、パス、見本画像からの色、検証、例のファイル |
| `test_fonts.py` | フォントファイルの収集と表示名 |
| `test_caption_image.py` | 字幕画像：旧スクリプトを書き写したものとピクセル単位で一致すること、大きさ、配置 |
| `test_cli.py` | `captions` と `compare`：ファイル名、上書き、エラー時にファイルを残さないこと、コマンドラインからのフォント指定 |
| `test_design.py` | 組み込みデザイン、上書き、デザインファイル、不正な値 |
| `test_layers.py` | 背景の拡大と切り取り（引き伸ばさない）、focus、dim、blur。曲名（字間、線）、字幕の帯・陰・枠、クレジット（位置、枠）、重ね合わせ |
| `test_timing.py` | タイミングファイル（LRC）：読み込み、書き出し、往復、終わりの行、不正なファイル、変わった歌詞ファイルとの突き合わせ |
| `test_backdrop.py` | フェード、時刻ごとの字幕（先行、クロスフェード、順番の切り替え、歌の途切れ、短い字幕、同時に 2 つまで）、クレジット、pickle と別プロセス、静止画がスペクトラムの下の backdrop と一致すること |
| `test_still.py` | `still` コマンド：ファイル名、時刻ごとまたは指定した字幕、曲ファイルからのデザインとスペクトラム、複数のデザインと比較画像、エラー |
| `test_render.py` | `render` コマンド：音声付きの動画、静止画と同じフレーム、コンソールスクリプト経由の複数ワーカー、曲の一部、ファイル名、処理前の拒否、キャンセルと Ctrl+C、進捗表示 |
| `test_web.py` | `sync` のサーバー：トークンとホストの検査、URL のトークンは音声だけで有効、範囲リクエスト、読み込み、保存（バックアップ、不正な時刻）、`still` と同じ静止画、ページからの書き出し（保存済みのタイミングだけ、一度に 1 つ、置き換え、キャンセル、停止、Finder で表示）、4 言語のページ用メッセージがそろっていること |
| `test_spectrum_dependency.py` | audio-spectrum-app が入っていること、渡した背景（backdrop）の上に静止画が描かれること |

## 3. ローカルのファイル

曲、歌詞、背景画像、フォント、実際の曲ファイル、書き出したものはすべて `work/`（Git の対象外）かリポジトリの外に置く。

`.gitignore` は、ツリーのどこにあっても次のものも除外する。

- メディア、画像、フォントのファイル
- `pyproject.toml` と `*.example.toml` を除くすべての `*.toml`

コミットの前に、ファイル一覧にこれらが紛れていないか確かめる。ユーザー名を含む絶対パスがないかも確かめる（`~/...` と書く）。

## 4. ツール

### 字幕画像の比較：`compare_images.py`

字幕画像が変わってはいけない変更をしたら、そのたびに使う。

```bash
uv run python tools/compare_images.py OLD_FOLDER NEW_FOLDER
```

- 2 つのフォルダの PNG をファイル名で組にする。たとえば旧歌詞画像スクリプトの出力とこのアプリの出力。
- 組ごとに、差のあるピクセルの割合、最大の差、差のある場所を表示する。
- 旧・新・差を縦に並べた画像を `work/compare_images/` に書き出す。
- ファイル名ではなく番号を表示する（`--names` を付けると名前を表示）。そのため曲名やフォント名を出さずに、出力を報告に貼れる。

### backdrop の計測：`time_backdrop.py`

スペクトラムの下に敷く絵を作る時間を、デザインごとに 1 フレーム単位で計る。曲ファイルの背景、フォント、動画の大きさを使う。

```bash
uv run python tools/time_backdrop.py work/my-song/song.toml --design classic soft panel
```

字幕なし、字幕あり、字幕のフェードイン中、2 つの字幕のクロスフェード中、クレジットのフェードイン中の、それぞれ 1 フレームあたりの平均時間を表示する。
1080p のフレーム 1 枚あたりの目標は、字幕ありで 10 ms 未満
（[ADR-004](../working/DECISIONS.md#adr-004-text-for-video-frames-drawn-with-pillow-composed-in-numpy-in-the-render-workers)、英語のみ）、
クロスフェード中で 20 ms 未満（[Phase 2 plan](../working/PHASE2_PLAN.md)、英語のみ）。

## 5. 規約

- コード、コメント、コミットメッセージ、ドキュメントは英語で書く。日本語は翻訳
  （`docs/ja/`、`README.ja.md`）にだけ使う。
- フレーム `n` は時刻 `n / fps` の音声を映す。字幕とクレジットは時刻で配置する。
- 普段の利用は完全にオフライン。
- 安定した文書は `docs/en/` に置き、日本語版を `docs/ja/` に置く。
  - 各翻訳は 1 行目に英語版の blob ハッシュ（`git hash-object docs/en/<FILE>.md`）を記録する。
  - 翻訳は英語版と同じコミットで更新する。
  - 作業用ドキュメント（計画、設計判断、受け入れ報告）は `docs/working/` に英語だけで置く。
- 作業はフェーズ単位で進める。
  1. `docs/working/PHASE<N>_PLAN.md` に計画を書き、オーナーの承認を得る
  2. 実装し、マイルストーンごとにコミットする
  3. 受け入れ報告を書く
- リポジトリを公開する前に、履歴全体をシークレットスキャナー（例：`gitleaks`）で検査する。
