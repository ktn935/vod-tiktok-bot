# -*- coding: utf-8 -*-
"""
Netflixの「配信終了予定作品」を Get Freax (net-frx.com) から取得する。

このスクリプトは非公式ファンサイトのHTML構造に依存しています。
サイト側のデザインが変わると動かなくなる可能性があるため、
定期的に動作確認してください。
"""
import re
import html
import datetime
import requests

JST = datetime.timezone(datetime.timedelta(hours=9))

URL = "https://www.net-frx.com/p/netflix-expiring.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 日付見出しのパターン: 08/16 (日)
DATE_HEADER_RE = re.compile(r"(\d{1,2})/(\d{1,2})\s*\([日月火水木金土]\)")

# 作品タイトルリンクのパターン: <a href="https://www.netflix.com/jp/title/XXXX">タイトル</a>
TITLE_LINK_RE = re.compile(
    r'<a href="(https://www\.netflix\.com/[^"]*?/title/\d+)"[^>]*>\s*([^<]+?)\s*</a>'
)

# 作品サムネイル画像のパターン(タイトルリンクの少し後ろに出てくる)
THUMBNAIL_RE = re.compile(r'<img[^>]*class="pht-exl25"[^>]*src="([^"]+)"')


def fetch_netflix_expiring(target_days_ahead=1):
    """
    target_days_ahead: 今日から何日以内の終了予定を対象にするか
      0 = 今日終了する作品のみ
      1 = 今日・明日終了する作品
    戻り値: [{"title": str, "date": "MM/DD"}, ...]
    """
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    page_html = resp.text

    today = datetime.datetime.now(JST).date()
    target_dates = {
        (today + datetime.timedelta(days=i)).strftime("%m/%d")
        for i in range(target_days_ahead + 1)
    }

    # 日付見出しの出現位置を記録
    matches = list(DATE_HEADER_RE.finditer(page_html))
    results = []

    for i, m in enumerate(matches):
        month, day = m.group(1), m.group(2)
        date_str = f"{int(month):02d}/{int(day):02d}"
        if date_str not in target_dates:
            continue

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(page_html)
        section = page_html[start:end]

        seen_urls = set()
        title_matches = list(TITLE_LINK_RE.finditer(section))
        for ti, tm in enumerate(title_matches):
            title_url, title_text = tm.group(1), html.unescape(tm.group(2).strip())
            if title_url in seen_urls:
                continue
            seen_urls.add(title_url)

            # このタイトルの直後、次のタイトルが始まるまでの範囲でサムネイルを探す
            block_end = title_matches[ti + 1].start() if ti + 1 < len(title_matches) else len(section)
            block = section[tm.end():block_end]
            thumb_m = THUMBNAIL_RE.search(block)
            thumbnail = thumb_m.group(1) if thumb_m else None

            results.append({
                "title": title_text,
                "date": date_str,
                "thumbnail": thumbnail,
                "url": title_url,
            })

    return results


if __name__ == "__main__":
    items = fetch_netflix_expiring(target_days_ahead=1)
    for it in items:
        print(it["date"], it["title"])
    print(f"合計 {len(items)} 件")
