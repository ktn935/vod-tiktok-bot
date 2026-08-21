# -*- coding: utf-8 -*-
"""
Amazon Prime Videoの「配信終了予定作品」を vedyro.com から取得する。

このページにはNext.jsのデータとして、各作品の
  id / title / leaving_date / prime_url(Amazon商品ページ) / thumbnail_url(Amazon商品画像)
がJSON形式で埋め込まれている。これを正規表現で直接取り出す方式にしている。
サイト側の実装が変わると動かなくなる可能性があるため、定期的に動作確認してください。
"""
import re
import html
import datetime
import requests

JST = datetime.timezone(datetime.timedelta(hours=9))

URL = "https://vedyro.com/prime-video/leaving-soon"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# あなた自身のAmazonアソシエイト・トラッキングID
AMAZON_ASSOCIATE_TAG = "nomissvod-22"

# ページ内に埋め込まれたJSONデータから1作品分の情報を取り出すパターン
# 例: \"id\":\"3839\",\"title\":\"...\",\"leaving_date\":\"2026-08-23\",
#     \"prime_url\":\"https://www.amazon.co.jp/dp/XXXX?tag=vedyro-22\",
#     \"thumbnail_url\":\"https://m.media-amazon.com/images/...jpg\"
ITEM_RE = re.compile(
    r'\\"id\\":\\"(\d+)\\",\\"title\\":\\"(.*?)\\",\\"leaving_date\\":\\"(\d{4}-\d{2}-\d{2})\\",'
    r'\\"prime_url\\":\\"(https://www\.amazon\.co\.jp/dp/[^\\]+?)\\",'
    r'\\"thumbnail_url\\":\\"(https://m\.media-amazon\.com/[^\\]+?)\\"'
)

TAG_PARAM_RE = re.compile(r"tag=[^&]+")


def _with_own_tag(amazon_url):
    """AmazonリンクについているアソシエイトタグをGET自分のものに差し替える。"""
    return TAG_PARAM_RE.sub(f"tag={AMAZON_ASSOCIATE_TAG}", amazon_url)


def fetch_prime_expiring(target_days_ahead=1):
    """
    target_days_ahead: 今日から何日以内の終了予定を対象にするか
    戻り値: [{"title": str, "date": "MM/DD", "url": str, "thumbnail": str}, ...]
    """
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    page_html = resp.text

    today = datetime.datetime.now(JST).date()
    target_dates = {
        (today + datetime.timedelta(days=i)).strftime("%Y-%m-%d"):
            (today + datetime.timedelta(days=i)).strftime("%m/%d")
        for i in range(target_days_ahead + 1)
    }

    results = []
    seen_ids = set()
    for m in ITEM_RE.finditer(page_html):
        item_id, title_text, iso_date, prime_url, thumbnail_url = m.groups()
        if iso_date not in target_dates:
            continue
        if item_id in seen_ids:
            continue
        seen_ids.add(item_id)
        results.append({
            "title": html.unescape(title_text),
            "date": target_dates[iso_date],
            "url": _with_own_tag(prime_url),
            "thumbnail": thumbnail_url,
        })

    return results


if __name__ == "__main__":
    items = fetch_prime_expiring(target_days_ahead=1)
    for it in items:
        print(it["date"], it["title"], it["url"])
    print(f"合計 {len(items)} 件")
