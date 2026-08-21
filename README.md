# Netflix / Prime Video 配信終了間近 TikTok用 素材Bot

Netflixの「配信終了予定」(Get Freax)、Amazon Prime Videoの「配信終了予定」(vedyro.com)を
毎日自動取得し、TikTok投稿用の**画像とキャプション文をTelegram経由でスマホに送る**ツールです。
投稿自体はこのツールでは行いません。スマホに届いた画像とテキストを使って、自分でTikTokに投稿してください。

`vod_x_bot`(X自動投稿版)とデータ取得・画像生成ロジックは共通で、送信先だけがTelegramになっています。

## ⚠️ 前提として知っておいてほしいこと

- ここで使っている情報源(Get Freax / vedyro.com)は、どちらも**非公式のファンサイト**です。
  情報が100%正確とは限りません。
- サイトのデザインが変わると、スクレイピング処理が動かなくなることがあります。
  その場合は `scrape_netflix.py` / `scrape_prime.py` の正規表現部分を調整してください。
- アクセス頻度は1日1回程度に抑えています(サイトに負荷をかけすぎないため)。

## 1. Telegramボットの準備(最初に一度だけ)

1. スマホでTelegramアプリをインストールし、アカウントを作成
2. Telegramで `@BotFather` を検索して開き、`/newbot` を送信
3. 案内に従ってボット名を決めると、**トークン**(`123456:ABC-DEF...`のような文字列)が発行される
   → これが `TELEGRAM_BOT_TOKEN`
4. 作成したボットを自分のTelegramで開き、何かメッセージ(例: `/start`)を送る
5. ブラウザで以下のURLを開く(`<トークン>`は3で発行されたもの)

   ```
   https://api.telegram.org/bot<トークン>/getUpdates
   ```

   返ってきたJSONの中の `"chat":{"id": ...}` の数字が **`TELEGRAM_CHAT_ID`**

## 2. ローカルでの動作確認(推奨)

Windows PCで、まず手元で正しく動くか確認します。

```bash
# 1. このフォルダに移動
cd vod_tiktok_bot

# 2. 必要なライブラリをインストール
pip install -r requirements.txt

# 3. 送信せず内容だけ確認(重要: 最初は必ずこちらで)
python main.py --dry-run
```

`--dry-run` を付けると実際には送信されず、生成される文章だけが表示されます。

### 環境変数をローカルで設定する場合

Windowsのコマンドプロンプトなら:

```
set TELEGRAM_BOT_TOKEN=ここにボットのトークン
set TELEGRAM_CHAT_ID=ここにchat_id
```

を実行してから `python main.py` を実行すると、実際にスマホへ送信されます。

## 3. GitHub Actionsでの自動実行セットアップ

### 3-1. GitHubリポジトリを作成

1. https://github.com で新規リポジトリを作成(Private推奨)
2. このフォルダの中身(README.mdやmain.pyなど全部)をアップロード

### 3-2. トークン類をGitHub Secretsに登録

1. リポジトリのページで `Settings` タブを開く
2. 左メニューの `Secrets and variables` → `Actions` を選択
3. `New repository secret` ボタンを押し、以下の2つを1つずつ登録:

| Name(名前) | Value(値) |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 1章で発行したトークン |
| `TELEGRAM_CHAT_ID` | 1章で確認したchat_id |

### 3-3. 動作確認

1. リポジトリの `Actions` タブを開く
2. `Daily VOD TikTok Notify` ワークフローを選択
3. `Run workflow` ボタンで手動実行してみる
4. 緑のチェックマークが付けば成功。スマホのTelegramに画像とテキストが届く

### 3-4. 送信タイミングについて

X本体の投稿タイミング(daily=朝8時、weekend=金曜18:30)より前倒しで、
「配信終了予定日の前日 日本時間0:00」にTelegramへ届くようにしてあります。

```yaml
- cron: "0 15 * * *"   # 毎日 日本時間0:00 (本日終了予定を前日0時に通知)
- cron: "0 15 * * 3"   # 毎週木曜 日本時間0:00 (金〜日曜分を木曜0時に通知)
```

タイミングを変えたい場合は `.github/workflows/daily_notify.yml` のこの2行を編集します。
時刻は **UTC(協定世界時)** で書くので、日本時間から9時間引いた値にしてください。

## 4. 投稿の流れ(スマホ側)

1. 決まった時間にTelegramへ通知が届く(画像 → 続けてキャプション文)
2. 画像を長押しして保存
3. TikTokアプリを開き、投稿画面で保存した画像を選択(静止画から動画化される)
4. Telegramのキャプション文をコピーして、TikTokの説明欄に貼り付け
5. 投稿

## 5. ファイル構成

```
vod_tiktok_bot/
├── main.py               # 実行の起点(取得→生成→Telegram送信)
├── scrape_netflix.py     # Netflixの配信終了情報を取得
├── scrape_prime.py       # Prime Videoの配信終了情報を取得
├── compose.py            # キャプション文を組み立てる
├── make_collage.py       # まとめ画像を生成する
├── telegram_notify.py    # Telegramへの送信処理
├── requirements.txt
└── .github/workflows/daily_notify.yml   # 自動実行の設定
```

## 6. うまく動かないときは

- `python main.py --dry-run` を実行してエラーメッセージを確認してください
- 「Netflix情報の取得に失敗しました」等のエラーが出る場合、サイト構造が
  変わった可能性があります。ブラウザで実際のページを開いて構造を見比べてください
- Telegramに届かない場合、`TELEGRAM_CHAT_ID` の取得時にボットへ`/start`等の
  メッセージを送信済みか確認してください(未送信だと`getUpdates`が空になります)
