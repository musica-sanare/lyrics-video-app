<!-- source: README.md blob 4dd19aaf5edcf1280df49df2c65b02861a7e1156 -->
[English](README.md) | 日本語 | [Español](README.es.md)

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# lyrics-video-app

自作曲の歌詞動画を、Mac 上で完全にオフラインで作ります。背景の静止画、曲名、画面下でフェードイン・アウトする歌詞の字幕、
クレジット、そして [audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app) が描くオーディオスペクトラムを、
曲の音声とともに 1 本の動画にします。動画編集ソフトで字幕画像を重ねていた手作業を置き換えるものです。

**状況:** Phase 0。`lyrics-video captions` が歌詞ファイルから旧歌詞画像スクリプトと同じ字幕画像を作り（iMovie 用）、
`lyrics-video compare` がテキストを多くのフォントで並べて見せます。動画全体の書き出しは後のフェーズで加わります。
Phase 0 は受け入れ済みです。[Phase 0 acceptance](docs/working/PHASE0_ACCEPTANCE.md)（英語のみ）を参照してください。

## クイックスタート

audio-spectrum-app をこのリポジトリの隣（`../audio-spectrum-app`）に置いておく必要があります。

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # フォント、色、歌詞ファイルを設定する
uv run lyrics-video captions work/my-song/song.toml         # 字幕 1 行につき 1 枚の PNG
uv run lyrics-video compare work/my-song/song.toml          # 比較用テキストを複数のフォントで
```

テストは `uv run pytest` で実行します。

## ドキュメント

- [ユーザーガイド](docs/ja/USER_GUIDE.md)：セットアップ、コマンド、曲ファイル、旧スクリプトからの移行
- [開発](docs/ja/DEVELOPMENT.md)：セットアップ、テスト、規約
- [ドキュメント目次](docs/ja/README.md)：設計判断や各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)。曲、歌詞、画像、フォントはこのリポジトリには一切含まれません。
