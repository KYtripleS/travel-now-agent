# note_drafts — 日本語note記事ドラフト

このフォルダには、noteシリーズ「**会社員、AIでメディアを作る。**」の下書きが保存されます。

---

## シリーズ概要

**シリーズ名:** 会社員、AIでメディアを作る。  
**サブタイトル:** 1日40分で、英語サイト・X・note・アフィリエイト導線を育てる実験記  
**公開先:** note（手動投稿のみ）

---

## ファイル命名規則

```
YYYY-MM-DD-free-{slug}.md     無料記事
YYYY-MM-DD-paid-{slug}.md     有料記事
YYYY-MM-DD-free-{slug}-2.md   同日2本目（自動採番）
```

同じ日にすでにファイルが存在する場合は、`-2`, `-3` と自動採番されます。  
`--force` を使うと上書きします。

---

## 記事の種類

### 無料記事
- ストーリー性あり・共感できる・読んで面白い
- 全実装詳細は明かさない（有料記事へ自然に誘導）
- 目安: 1,000〜1,500文字

### 有料記事
- 実践的・詳細・フレームワーク・ワークフロー・チェックリスト含む
- 実際の公開サイト（Travel Now）の設計ロジックを紹介
- APIキー・認証情報・機密実装詳細は含まない
- 目安: 2,000〜3,500文字
- 推奨価格: ¥300 前後（Geminiが提案）

---

## 使い方

### ドラフト生成

```bash
# 乾燥走行（dry run）：内容確認のみ、API不使用
python generate_note_draft.py

# 実際に生成・保存
python generate_note_draft.py --write

# モード指定
python generate_note_draft.py --write --mode travel_prep

# トピック指定
python generate_note_draft.py --write \
  --topic-free "貧乏会社員がAIで副業メディアを作り始めた話" \
  --topic-paid "【実践編】AIで旅行メディアを作る最初の7日間"

# 同日ファイルを上書き
python generate_note_draft.py --write --force

# 利用可能なモード一覧
python generate_note_draft.py --list-modes
```

### 利用可能なモード

| モード | 内容 | 自動選択日 |
|---|---|---|
| `ai_side_hustle` | AIで副業・メディア構築の体験とノウハウ | 火・土 |
| `travel_prep` | 旅行メディアの構造・設計・アフィリエイト | 水 |
| `english_global` | 英語サイト・グローバル発信の実践 | 木 |
| `build_log` | 制作ログ・週次振り返り・作業記録 | 月・日 |
| `template_pack` | テンプレート・チェックリスト・フレームワーク | 金 |

---

## 投稿ワークフロー

```
generate_note_draft.py --write
        ↓
note_drafts/ にドラフト保存
        ↓
ドラフトを読んで手動で編集・修正
        ↓
noteにコピー貼り付け → 手動投稿
        ↓
（必要であれば）data/content_log.csv に記録
```

---

## 重要な制約

- **このスクリプトはnoteに自動投稿しません**
- **note非公式APIは使用しません**
- **ブラウザ自動操作は行いません**
- **ログイン処理は一切ありません**
- すべての投稿は手動で行ってください

---

## ファイル構成

各ドラフトのヘッダー（HTML comment）には以下のメタデータが含まれます：

```
<!--
type: free または paid
series: 会社員、AIでメディアを作る。
topic_mode: 使用したモード
recommended_price: ¥300（有料記事のみ）
date: 生成日
suggested_tags: タグ候補
-->
```

---

## daily_run.py との連携

`daily_run.py` を実行すると、その日のドラフトがまだ存在しない場合に自動生成されます。  
すでに存在する場合はスキップしてパスを表示します。

```bash
python daily_run.py
```
