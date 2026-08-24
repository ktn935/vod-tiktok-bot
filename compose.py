# -*- coding: utf-8 -*-
"""
取得した作品リストから、Xに投稿する文章を組み立てる。
Netflix / Prime Videoはそれぞれ別のツイートとして投稿する。

投稿モードは2種類:
  daily   = 本日(23:59まで)に配信終了する作品のみ(毎朝8時に投稿)
  weekend = 金曜(当日)〜日曜(23:59)までに配信終了する作品一覧(毎週金曜18:30に投稿)
"""
import datetime

JST = datetime.timezone(datetime.timedelta(hours=9))

NETFLIX_HASHTAGS = (
    "#Netflix #NetflixJP #配信終了予定 #映画好きと繋がりたい #ドラマ好きと繋がりたい "
    "#おすすめ映画 #サブスク #Netflixおすすめ #ネトフリ"
)
PRIME_HASHTAGS = (
    "#AmazonPrimeVideo #プライムビデオ #配信終了予定 #映画好きと繋がりたい #ドラマ好きと繋がりたい "
    "#おすすめ映画 #サブスク #プライムビデオおすすめ #アマプラ"
)
CTA = "👉今のうちにマイリスト追加"


def _today():
    return datetime.datetime.now(JST).date()


def _this_sunday(today):
    return today + datetime.timedelta(days=(6 - today.weekday()) % 7)


def _header_label(mode, reference_date=None):
    today = reference_date or _today()
    if mode == "weekend":
        sunday = _this_sunday(today)
        return f"【週末に見よう】{today.strftime('%m/%d')}(金)〜{sunday.strftime('%m/%d')}(日) 配信終了予定"
    return f"【本日 配信終了予定】{today.strftime('%m/%d')} 23:59まで"


def _format_titles(items, with_link=False, show_date=False):
    if not items:
        return None
    lines = []
    for it in items:
        line = f"・{it['title']}"
        if show_date:
            line += f" ({it['date']}まで)"
        if with_link and it.get("url"):
            line += f"\n{it['url']}"
        lines.append(line)
    return "\n".join(lines)


def build_netflix_tweet(netflix_items, mode="daily", reference_date=None):
    nf_line = _format_titles(netflix_items, with_link=True, show_date=(mode == "weekend"))
    if not nf_line:
        return None
    header = _header_label(mode, reference_date)
    return f"🟥{header}\n{CTA}\n🟥Netflix\n{nf_line}\n\n{NETFLIX_HASHTAGS}"


def build_prime_tweet(prime_items, mode="daily", reference_date=None):
    pv_line = _format_titles(prime_items, with_link=True, show_date=(mode == "weekend"))
    if not pv_line:
        return None
    header = _header_label(mode, reference_date)
    return f"🟦{header}\n{CTA}\n🟦Prime Video\n{pv_line}\n\n{PRIME_HASHTAGS}"


if __name__ == "__main__":
    sample_nf = [{"title": "サンプル作品A", "date": "08/22", "url": "https://www.netflix.com/jp/title/XXXX"}]
    sample_pv = [{"title": "サンプル作品B", "date": "08/22", "url": "https://www.amazon.co.jp/dp/XXXX?tag=nomissvod-22"}]
    print(build_netflix_tweet(sample_nf, mode="daily"))
    print()
    print(build_prime_tweet(sample_pv, mode="weekend"))
