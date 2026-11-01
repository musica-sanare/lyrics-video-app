<!-- source: README.md blob 8bbaed4b86cd064ee8cdce4c785c2efca3ae830b -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳。内容が異なる場合は英語版が優先する。

# lyrics-video-app

自作曲の歌詞動画を、Mac 上で完全にオフラインで作る。動画は背景の静止画、曲名、画面下でフェードイン・アウトする歌詞の字幕、
クレジット、[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app) が描くオーディオスペクトラムと、
曲の音声でできている。動画編集ソフトで字幕画像を重ねていた手作業を、これで置き換える。

**状況：** Phase 2（歌詞のタイミング）は受け入れ済み。`sync` ページで作った LRC ファイルの時刻に合わせて字幕を出す。
動画全体の書き出しは Phase 3 で加わる。詳しくは [Phase 2 acceptance](docs/working/PHASE2_ACCEPTANCE.md)（英語のみ）を参照。

## 今できること

- `lyrics-video captions`：歌詞ファイルから、旧歌詞画像スクリプトと同じ字幕画像を作る。iMovie で使う。
- `lyrics-video compare`：テキストを多くのフォントで並べて見せる。
- `lyrics-video sync`：ブラウザでページを開き、曲を再生しながら字幕の時刻をタップして調整する。
- `lyrics-video still`：将来の動画のフレーム（背景、曲名、その時点の字幕、クレジット、スペクトラム）を 3 つのデザインで描く。
  既定のデザインは `soft`。

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
```

テストは `uv run pytest` で走らせる。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md)：セットアップ、コマンド、タイミング、曲ファイル、旧スクリプトからの移行
- [開発](docs/ja/DEVELOPMENT.md)：セットアップ、テスト、規約
- [アーキテクチャ](docs/ja/ARCHITECTURE.md)：コードの作りと、新しい機能の置き場所
- [ドキュメント目次](docs/ja/README.md)：設計判断や各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)。曲、歌詞、画像、フォントはこのリポジトリに一切含めない。
