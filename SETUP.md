# セットアップ手順

## 所要時間: 約30〜40分（初回のみ）

---

## Step 1: Google Cloud でサービスアカウントを作成

1. [Google Cloud Console](https://console.cloud.google.com/) を開く
2. 新しいプロジェクトを作成（例: `todo-scheduler`）
3. 左メニュー → **APIとサービス** → **ライブラリ**
4. 以下の2つのAPIを検索して「有効にする」:
   - `Google Sheets API`
   - `Google Calendar API`
5. **認証情報** → **認証情報を作成** → **サービスアカウント**
   - 名前: `todo-scheduler` など任意
   - ロール: 「オーナー」または「編集者」
6. 作成したサービスアカウントをクリック → **キー** タブ → **鍵を追加** → **JSON**
7. ダウンロードされた JSON ファイルを `credentials.json` という名前で保存（このフォルダに置く）

---

## Step 2: Google Sheetsを準備

1. [Google Sheets](https://sheets.google.com) で新規スプレッドシートを作成
2. シート名を `タスク` に変更
3. 1行目にヘッダーを入力:

```
A1: タスク名
B1: 重要度
C1: 緊急度
D1: タスク種別
E1: 所要時間（分）
F1: 期日
G1: ステータス
H1: メモ
```

4. サンプルデータを2行目以降に入力:

```
プレゼン資料の最終確認 | 高 | 高 | 思考系 | 60 | 2026/03/15 | 未着手 |
月次レポート数値確認   | 高 | 中 | 単純作業 | 30 | 2026/03/17 | 未着手 |
```

5. スプレッドシートのURLからIDをコピー:
   `https://docs.google.com/spreadsheets/d/【ここがID】/edit`

6. `config.py` の `SPREADSHEET_ID` に貼り付ける

7. サービスアカウントのメールアドレス（`credentials.json` 内の `client_email`）を
   スプレッドシートの**共有**に追加（閲覧権限でOK）

---

## Step 3: Googleカレンダーにサービスアカウントを追加

1. [Google Calendar](https://calendar.google.com) を開く
2. 左サイドバーの自分のカレンダー → **設定と共有**
3. **特定のユーザーとの共有** → サービスアカウントのメールアドレスを追加
4. 権限: **「予定の変更および共有の管理」** を選択

---

## Step 4: ローカルでテスト実行

```bash
cd /Users/sakaiyohei/src/todo-calendar-sync
pip install -r requirements.txt
python scheduler.py
```

カレンダーにイベントが登録されれば成功です。

---

## Step 5: GitHubに登録して自動実行

1. GitHubで新しいリポジトリを作成（**Private** 推奨）

2. このフォルダをプッシュ:
```bash
cd /Users/sakaiyohei/src/todo-calendar-sync
git init
git add .
git commit -m "初期設定"
git remote add origin https://github.com/あなたのユーザー名/todo-calendar-sync.git
git push -u origin main
```

3. GitHub → リポジトリ → **Settings** → **Secrets and variables** → **Actions**

4. **New repository secret** をクリック:
   - Name: `GOOGLE_CREDENTIALS_JSON`
   - Value: `credentials.json` の中身をそのまま貼り付け

5. **Actions** タブ → ワークフローを確認 → **Run workflow** で手動テスト

6. 毎朝4:30（JST）に自動実行されます。

---

## ⚠️ 注意事項

- `credentials.json` は **絶対にGitHubにコミットしない**こと
- `.gitignore` に `credentials.json` を追加済み（自動で除外されます）
- GitHub Free プランでも Actions は月2,000分まで無料（このスクリプトは1回1〜2分）
