<!-- source: docs/en/README.md blob b79354b6dc474414413bf5b1742b26abc5bb362d -->
[English](../en/README.md) | 日本語 · [リポジトリの README](../../README.ja.md)

> この文書は[英語版](../en/README.md)の翻訳。内容が異なる場合は英語版が優先する。

# lyrics-video-app ドキュメント

オフラインの歌詞動画メーカー lyrics-video-app の全文書を、1 行の説明付きで並べる。曲の字幕や静止画を作るなら[ユーザーガイド](USER_GUIDE.md)から、コードを触るなら[開発](DEVELOPMENT.md)から読む。作業用ドキュメントには設計判断と各フェーズの記録がある。

## ガイド

| 文書 | 説明 |
|---|---|
| [ユーザーガイド](USER_GUIDE.md) | セットアップ、`captions`・`compare`・`still` コマンド、`sync` ページでの字幕のタイミング付け、デザイン、曲ファイル、旧歌詞画像スクリプトからの移行。 |
| [開発](DEVELOPMENT.md) | セットアップ、テスト、規約、リポジトリを公開しても安全に保つためのルール。 |

## 作業用ドキュメント（英語のみ）

| 文書 | 説明 |
|---|---|
| [Handoff](../working/HANDOFF.md)（英語のみ） | このリポジトリができた経緯、オーナーの回答、決定事項、フェーズ案。 |
| [Decisions](../working/DECISIONS.md)（英語のみ） | 設計判断の記録（ADR）。 |
| [Phase 0 plan](../working/PHASE0_PLAN.md)（英語のみ） | リポジトリの土台と、字幕画像生成の CLI 化。 |
| [Phase 0 acceptance](../working/PHASE0_ACCEPTANCE.md)（英語のみ） | Phase 0 の受け入れ報告：基準、旧字幕画像との比較、リポジトリの安全性、未決事項。 |
| [Phase 1 plan](../working/PHASE1_PLAN.md)（英語のみ） | 歌詞動画のデザインを設定可能な部品にする：フレームの構成、backdrop、比較するデザイン、`still` コマンド。 |
| [Phase 1 acceptance](../working/PHASE1_ACCEPTANCE.md)（英語のみ） | Phase 1 の受け入れ報告：オーナーが選んだデザイン、基準、backdrop の計測時間、リポジトリの安全性、未決事項。 |
| [Phase 2 plan](../working/PHASE2_PLAN.md)（英語のみ） | 歌詞のタイミング：LRC ファイル、キーで時刻を付けて調整するページ、先出しとクロスフェードを含む時刻での字幕表示、アーキテクチャ文書。 |
