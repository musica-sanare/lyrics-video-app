<!-- source: README.md blob 8e56cd39e8e913cb8318dd2d518c1f3909959bc8 -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳。内容が異なる場合は英語版が優先する。

# lyrics-video-app

自作曲の歌詞動画を、Mac 上で完全にオフラインで作る。動画は背景の静止画、曲名、画面下でフェードイン・アウトする歌詞の字幕、
クレジット、[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app) が描くオーディオスペクトラムと、
曲の音声でできている。動画編集ソフトで字幕画像を重ねていた手作業を、これで置き換える。

**状況：** Phase 3（動画全体を一度に作る）を進行中。`render` でタイミング済みの曲から動画全体を作れる。
詳しくは [Phase 3 plan](docs/working/PHASE3_PLAN.md)（英語のみ）を参照。

## 今できること

- `lyrics-video captions`：歌詞ファイルから、旧歌詞画像スクリプトと同じ字幕画像を作る。iMovie で使う。
- `lyrics-video compare`：テキストを多くのフォントで並べて見せる。
- `lyrics-video sync`：ブラウザでページを開き、曲を再生しながら字幕の時刻をタップして調整する。
- `lyrics-video still`：将来の動画のフレーム（背景、曲名、その時点の字幕、クレジット、スペクトラム）を 3 つのデザインで描く。
  既定のデザインは `soft`。
- `lyrics-video render`：曲の音声付きの歌詞動画全体を書き出す。

## クイックスタート

audio-spectrum-app をこのリポジトリの隣（`../audio-spectrum-app`）に置いておく必要がある。

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # このあとフォント、色、歌詞ファイルを設定する
uv run lyrics-video captions work/my-song/song.toml         # 字幕 1 行につき 1 枚の PNG
uv run lyrics-video compare work/my-song/song.toml          # 比較用テキストを複数のフォントで
uv run lyrics-video sync work/my-song/song.toml             # ブラウザで字幕にタイミングを付ける
uv run lyrics-video still work/my-song/song.toml --time 60  # 指定した時刻の動画のフレーム
uv run lyrics-video render work/my-song/song.toml           # 動画全体（work/my-song/videos/ に書き出す）
```

テストは `uv run pytest` で走らせる。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md)：セットアップ、コマンド、タイミング、曲ファイル、旧スクリプトからの移行
- [開発](docs/ja/DEVELOPMENT.md)：セットアップ、テスト、規約
- [アーキテクチャ](docs/ja/ARCHITECTURE.md)：コードの作りと、新しい機能の置き場所
- [ドキュメント目次](docs/ja/README.md)：設計判断や各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)。曲、歌詞、画像、フォントはこのリポジトリに一切含めない。
