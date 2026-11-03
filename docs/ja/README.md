<!-- source: docs/en/README.md blob ed272bf226b83e51271705f128a298a5d6d1acac -->
[English](../en/README.md) | 日本語 · [リポジトリの README](../../README.ja.md)

> この文書は[英語版](../en/README.md)の翻訳。内容が異なる場合は英語版が優先する。

# lyrics-video-app ドキュメント

オフラインの歌詞動画メーカー lyrics-video-app の全文書を、1 行の説明付きで並べる。曲にタイミングを付けて動画を作るなら[ユーザーガイド](USER_GUIDE.md)から、コードを触るなら[開発](DEVELOPMENT.md)から読む。作業用ドキュメントには設計判断と各フェーズの記録がある。

## ガイド

| 文書 | 説明 |
|---|---|
| [ユーザーガイド](USER_GUIDE.md) | セットアップ、Dock からの普段の使い方（新しい曲、次の曲）、ページでの字幕のタイミング付け、`still` での静止画、`render` かページからの動画全体の書き出し、デザイン、曲ファイル。 |
| [開発](DEVELOPMENT.md) | セットアップ、テスト、規約、リポジトリを公開しても安全に保つためのルール。 |
| [アーキテクチャ](ARCHITECTURE.md) | 層の分け方、曲ファイルから静止画と動画までの流れ、sync ページ、どの変更でも守る決まり、性能、新しい機能の置き場所。 |
| [Security policy](../../SECURITY.md)（英語のみ） | 脆弱性を非公開で報告する方法と、対象になるアプリの部分。 |

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
| [Phase 2 acceptance](../working/PHASE2_ACCEPTANCE.md)（英語のみ） | Phase 2 の受け入れ報告：オーナーが選んだ字幕の切り替え方、基準、backdrop の計測時間、リポジトリの安全性、未決事項。 |
| [Phase 3 plan](../working/PHASE3_PLAN.md)（英語のみ） | 歌詞動画全体を一度に作る：audio-spectrum-app の `render_video` を使う `render` コマンド、`sync` ページからのレンダリング、字幕画像コマンドの削除。 |
| [Phase 3 acceptance](../working/PHASE3_ACCEPTANCE.md)（英語のみ） | Phase 3 の受け入れ報告：オーナーの最初の完成動画、基準、書き出し時間の計測、リポジトリの安全性、未決事項。 |
| [Phase 4 plan](../working/PHASE4_PLAN.md)（英語のみ） | `sync` ページでの動画プレビューとデザイン設定：低解像度のプレビュー動画、太字・斜体・タイトルの背景ボックス、曲ファイルに保存するデザインモード。 |
| [Phase 4 acceptance](../working/PHASE4_ACCEPTANCE.md)（英語のみ） | Phase 4 の受け入れ報告：オーナーの確認、基準、プレビューと静止画の計測時間、リポジトリの安全性、未決事項。 |
| [Phase 5 plan](../working/PHASE5_PLAN.md)（英語のみ） | `sync` ページでのスペクトラム設定と名前付きデザイン：デザインの一部としてのスペクトラム、選んだスペクトラム設定、ユーザーフォルダに名前で保存するデザイン。 |
| [Phase 5 acceptance](../working/PHASE5_ACCEPTANCE.md)（英語のみ） | Phase 5 の受け入れ報告：オーナーの確認、基準、静止画の計測時間、リポジトリの安全性、未決事項。 |
| [Phase 6 plan](../working/PHASE6_PLAN.md)（英語のみ） | 日常の運用：Dock からのアプリ起動、最近の曲を並べる開始ページ、どのフォルダのファイルからでも作る新しい曲、ページでの曲の設定。 |
| [Phase 6 acceptance](../working/PHASE6_ACCEPTANCE.md)（英語のみ） | Phase 6 の受け入れ報告：オーナーの確認とそこから出た二つの修正、基準、起動時間の計測、リポジトリの安全性、未決事項。 |
| [Phase 7 plan](../working/PHASE7_PLAN.md)（英語のみ） | コードで描くアプリアイコンと、リポジトリ公開の準備：アイコン、公開前チェックリスト、タグ指定の audio-spectrum-app、`SECURITY.md`。 |
| [Phase 7 acceptance](../working/PHASE7_ACCEPTANCE.md)（英語のみ） | Phase 7 の受け入れ報告：オーナーが選んだアイコン、基準、新しい clone での確認、アイコン作成時間の計測、リポジトリの安全性、未決事項。 |
| [Public release checklist](../working/PUBLIC_RELEASE.md)（英語のみ） | 公開前のすべての確認と結果・日付、公開の切り替えと直後の GitHub 設定のオーナー手順。 |
