<!-- source: docs/en/DEVELOPMENT.md blob b511d034d978d85813301132bfececc1bd48b98d -->
[English](../en/DEVELOPMENT.md) | 日本語 | [Español](../es/DEVELOPMENT.md) · [目次に戻る](README.md)

> この文書は[英語版](../en/DEVELOPMENT.md)の翻訳です。内容が異なる場合は英語版が優先されます。

# 開発

コードを扱うためのセットアップ、確認方法、規約です。

## 1. セットアップ

```bash
brew install uv ffmpeg
git clone <audio-spectrum-app のリポジトリ> ../audio-spectrum-app   # 最初に一度だけ、このリポジトリの隣に
uv sync
```

Python 3.13 とすべての依存は `uv` で管理します（`pyproject.toml`、`uv.lock`）。audio-spectrum-app はパス依存
（`../audio-spectrum-app`、editable、バージョン 0.5.0 以上）なので、向こうの変更は再インストールなしで反映されます
（[ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum)、英語のみ）。
使ってよいのは公開 API、つまり `audio_spectrum` がエクスポートする名前だけです。依存の追加は `uv add <package>` で行い、
依存は少なく、広く使われているものにとどめます。

## 2. テスト

```bash
uv run pytest
```

- テストは生成したテキスト・画像・信号（`tests/signals.py`）だけを使い、実際の曲、歌詞、第三者のフォントは使いません。
  フォントが必要なテストは macOS のシステムフォントを使い、ない環境ではスキップされます。

| ファイル | 対象 |
|---|---|
| `test_cli.py` | コマンドのバージョン表示とモジュールとしての起動 |
| `test_spectrum_dependency.py` | audio-spectrum-app が入っていること、渡した背景（backdrop）の上に静止画が描かれること |

## 3. ローカルのファイル

曲、歌詞、背景画像、フォント、実際の曲ごとの設定ファイル、書き出したものはすべて `work/`（Git の対象外）か
リポジトリの外に置きます。`.gitignore` は、ツリー内のどこにあっても、メディア・画像・フォントのファイルと、
`pyproject.toml` と `*.example.toml` 以外のすべての `*.toml` も除外します。コミットの前には、ファイル一覧にこれらが
含まれていないこと、ユーザー名を含む絶対パスがないこと（`~/...` と書く）を確認します。

## 4. 規約

- コード、コメント、コミットメッセージ、ドキュメントは英語で書きます。日本語とスペイン語は翻訳
  （`docs/ja/`、`docs/es/`、`README.ja.md`、`README.es.md`）にだけ現れます。
- フレーム `n` は時刻 `n / fps` の音声を表します。字幕とクレジットは時刻で配置します。
- 普段の利用は完全にオフラインです。
- 安定した文書は `docs/en/` に置き、日本語版を `docs/ja/`、スペイン語版を `docs/es/` に置きます。各翻訳は 1 行目に
  英語版の blob ハッシュ（`git hash-object docs/en/<FILE>.md`）を記録し、英語版と同じコミットで更新します。
  作業用ドキュメント（計画、設計判断、受け入れ報告）は `docs/working/` に英語のみで置きます。
- 作業はフェーズ単位で進めます。`docs/working/PHASE<N>_PLAN.md` の計画をオーナーが承認したら実装し、
  マイルストーンごとにコミットし、最後に受け入れ報告を書きます。
- リポジトリを公開する前に、履歴全体をシークレットスキャナー（例：`gitleaks`）で検査します。
