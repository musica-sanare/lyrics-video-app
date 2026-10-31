<!-- source: README.md blob 08b24fae74baa6c53c8b1bb7c2a44429c7dda7b7 -->
[English](README.md) | 日本語 | [Español](README.es.md)

> この文書は[英語版](README.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# lyrics-video-app

自作曲の歌詞動画を、Mac 上で完全にオフラインで作ります。背景の静止画、曲名、画面下でフェードイン・アウトする歌詞の字幕、
クレジット、そして [audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app) が描くオーディオスペクトラムを、
曲の音声とともに 1 本の動画にします。動画編集ソフトで字幕画像を重ねていた手作業を置き換えるものです。

**状況:** Phase 0（土台づくり）。コマンドの枠組みができたところで、次は歌詞ファイルから字幕画像を作る機能です。
[Phase 0 plan](docs/working/PHASE0_PLAN.md)（英語のみ）を参照してください。

## クイックスタート

audio-spectrum-app をこのリポジトリの隣（`../audio-spectrum-app`）に置いておく必要があります。

```bash
brew install uv ffmpeg
uv sync
uv run lyrics-video --version
uv run pytest
```

## ドキュメント

- [開発](docs/ja/DEVELOPMENT.md)：セットアップ、テスト、規約
- [ドキュメント目次](docs/ja/README.md)：設計判断や各フェーズの記録を含む全文書

## ライセンス

[MIT](LICENSE)。曲、歌詞、画像、フォントはこのリポジトリには一切含まれません。
