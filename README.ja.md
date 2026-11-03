<!-- source: README.md blob fe9ac2711487ca72a960e253e93b4b653f729396 -->
[English](README.md) | 日本語

> この文書は[英語版](README.md)の翻訳。内容が異なる場合は英語版が優先する。

# lyrics-video-app

自作曲の歌詞動画を、Mac 上で完全にオフラインで作る。動画は背景の静止画、曲名、画面下でフェードイン・アウトする歌詞の字幕、
クレジット、[audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app) が描くオーディオスペクトラムと、
曲の音声でできている。動画編集ソフトで字幕画像を重ねていた手作業を、これで置き換える。

**状況：** Phase 7 は受け入れ済みで、バージョンは 0.6.0。専用のアイコンで Dock からアプリを起動し、どのフォルダのファイルからでも新しい曲を
作れる。タイミング付け、スペクトラムを含む見た目の設定、動画全体の数十秒でのプレビュー、書き出しまで、一つのページで済む。
clone したら `uv sync` だけでインストールできる。詳しくは [Phase 7 acceptance](docs/working/PHASE7_ACCEPTANCE.md)（英語のみ）を参照。

## 今できること

- Lyrics Video.app（`lyrics-video install-app` で作る）で Dock からアプリを起動できる。開始ページに最近の曲が並び、どのフォルダにある音声・
  背景画像・歌詞テキストからでも新しい曲を作れる。
- `lyrics-video sync`：ブラウザでページを開き、曲を再生しながら字幕の時刻をタップして調整する。静止画を見ながらデザインとスペクトラムを変え、
  見た目を名前付きデザインとしてほかの曲用に保存し、簡易のプレビュー動画で確かめて、そこから動画も書き出せる。
- `lyrics-video still`：将来の動画のフレーム（背景、曲名、その時点の字幕、クレジット、スペクトラム）を 3 つのデザインで描く。
  既定のデザインは `soft`。
- `lyrics-video render`：曲の音声付きの歌詞動画全体を書き出す。

## クイックスタート

```bash
brew install uv ffmpeg
git clone https://github.com/musica-sanare/lyrics-video-app
cd lyrics-video-app
uv sync                           # audio-spectrum-app 0.5.0 も GitHub から取得する
uv run lyrics-video install-app   # ~/Applications に Lyrics Video.app ができる。Dock にドラッグする
```

アプリをクリックして「新しい曲…」を選び、音声、背景画像、歌詞を選ぶ。1 曲の流れは[ユーザーガイド](docs/ja/USER_GUIDE.md)の 2 節にある。
ターミナルからも同じことができる。

```bash
uv run lyrics-video sync path/to/song.toml               # ブラウザで字幕にタイミングを付け、見た目を決める
uv run lyrics-video still path/to/song.toml --time 60    # 指定した時刻の動画のフレーム
uv run lyrics-video render path/to/song.toml             # 動画全体（曲ファイルの隣の videos/ に書き出す）
```

テストは `uv run pytest` で走らせる。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md)：セットアップ、タイミング、静止画、動画全体、デザイン、曲ファイル
- [開発](docs/ja/DEVELOPMENT.md)：セットアップ、テスト、規約
- [アーキテクチャ](docs/ja/ARCHITECTURE.md)：コードの作りと、新しい機能の置き場所
- [ドキュメント目次](docs/ja/README.md)：設計判断や各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)。曲、歌詞、画像、フォントはこのリポジトリに一切含めない。
