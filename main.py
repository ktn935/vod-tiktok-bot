# -*- coding: utf-8 -*-
"""
Netflix / Prime Videoの配信終了予定を取得し、TikTok投稿用の画像・文章を生成して
Telegram経由でスマホに送るスクリプト。
投稿自体はスマホから手動で行う(このスクリプトは投稿しない)。

投稿モードは2種類:
  daily   = 基準日(23:59まで)に配信終了する作品のみ
  weekend = 金曜(当日)〜日曜(23:59)までに配信終了する作品一覧

X本体の投稿タイミングより前倒しでTelegramに届けるため、--day-offset で
「実行日の何日後を基準日とみなすか」を指定できる(GitHub Actions側で自動設定)。
  daily   は 1 (毎日0時に実行し、1日後を基準日にすることで翌日終了分を対象にする)
  weekend は 1 (木曜0時に実行し、1日後の金曜を基準日にすることでFri〜Sunを対象にする)

ローカルでテストする場合:
  1. 環境変数 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID を設定
  2. python main.py --dry-run              で送信せず内容だけ確認(daily)
  3. python main.py --mode weekend --dry-run  で週末モードの内容を確認
  4. python main.py                        で実際にスマホへ送信
"""
import sys
import argparse
import datetime

from scrape_netflix import fetch_netflix_expiring
from scrape_prime import fetch_prime_expiring
from compose import build_netflix_tweet, build_prime_tweet, JST
from make_collage import make_collages
from telegram_notify import send_content


def _weekend_days_ahead(reference_date):
    """基準日(金曜想定)から日曜日までの日数(金曜が基準日なら2になる)"""
    return (6 - reference_date.weekday()) % 7


def _handle_send(label, text, items, service, dry_run):
    if text is None:
        print(f"[{label}] 対象の作品がありませんでした。送信をスキップします。")
        return

    images = make_collages(items, service)

    print(f"----- {label} 送信内容 -----")
    print(text)
    print(f"文字数: {len(text)}")
    print(f"まとめ画像: {len(images)}枚")
    print("----------------------------")

    if dry_run:
        print("(--dry-run のため実際の送信は行いません)")
        return

    send_content(text, images=images)
    print(f"[{label}] Telegramへ送信しました")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="送信せず、生成される内容を表示するだけ",
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekend"],
        default="daily",
        help="daily=本日終了分のみ、weekend=金〜日曜までの一覧",
    )
    parser.add_argument(
        "--days-ahead",
        type=int,
        default=None,
        help="対象日数を直接指定する(動作確認用。指定時はmodeの自動計算より優先)",
    )
    parser.add_argument(
        "--day-offset",
        type=int,
        default=0,
        help="基準日を実行日から何日後にずらすか(前倒し通知用。weekendをThursday実行する場合は1)",
    )
    args = parser.parse_args()

    reference_date = datetime.datetime.now(JST).date() + datetime.timedelta(days=args.day_offset)

    if args.days_ahead is not None:
        days_ahead = args.days_ahead
    else:
        days_ahead = 0 if args.mode == "daily" else _weekend_days_ahead(reference_date)

    try:
        netflix_items = fetch_netflix_expiring(target_days_ahead=days_ahead, reference_date=reference_date)
    except Exception as e:
        print(f"[警告] Netflix情報の取得に失敗しました: {e}", file=sys.stderr)
        netflix_items = []

    try:
        prime_items = fetch_prime_expiring(target_days_ahead=days_ahead, reference_date=reference_date)
    except Exception as e:
        print(f"[警告] Prime Video情報の取得に失敗しました: {e}", file=sys.stderr)
        prime_items = []

    _handle_send(
        "Netflix",
        build_netflix_tweet(netflix_items, mode=args.mode, reference_date=reference_date),
        netflix_items,
        "netflix",
        args.dry_run,
    )
    _handle_send(
        "Prime Video",
        build_prime_tweet(prime_items, mode=args.mode, reference_date=reference_date),
        prime_items,
        "prime",
        args.dry_run,
    )


if __name__ == "__main__":
    main()
