# -*- coding: utf-8 -*-
"""
Telegramボットへスマホ通知として画像・文章を送る処理。
投稿は行わず、スマホで手動投稿しやすいように内容を届けるだけ。

必要な環境変数:
  TELEGRAM_BOT_TOKEN  BotFatherで発行したボットのトークン
  TELEGRAM_CHAT_ID    通知を受け取るchat_id(自分のアカウントのID)
"""
import json
import os

import requests

API_BASE = "https://api.telegram.org"
MAX_MEDIA_GROUP_SIZE = 10  # Telegramの1アルバムあたりの上限


def _credentials():
    return (
        os.environ["TELEGRAM_BOT_TOKEN"].strip(),
        os.environ["TELEGRAM_CHAT_ID"].strip(),
    )


def _send_single_photo(token, chat_id, image_bytes):
    resp = requests.post(
        f"{API_BASE}/bot{token}/sendPhoto",
        data={"chat_id": chat_id},
        files={"photo": ("collage.png", image_bytes, "image/png")},
        timeout=30,
    )
    resp.raise_for_status()


def _send_media_group(token, chat_id, images_chunk):
    media = []
    files = {}
    for i, image_bytes in enumerate(images_chunk):
        name = f"photo{i}"
        media.append({"type": "photo", "media": f"attach://{name}"})
        files[name] = (f"{name}.png", image_bytes, "image/png")

    resp = requests.post(
        f"{API_BASE}/bot{token}/sendMediaGroup",
        data={"chat_id": chat_id, "media": json.dumps(media)},
        files=files,
        timeout=60,
    )
    resp.raise_for_status()


def send_content(text: str, images=None):
    """
    imagesが1枚ならそのまま画像として送信、2枚以上ならアルバム(まとめて表示)として送信する。
    その後、全文を別のテキストメッセージとして送る。
    (Telegramの画像キャプションは1024文字までのため、全文は常に別メッセージで送る)
    imagesが空なら画像は送らずテキストのみ送信する。
    """
    token, chat_id = _credentials()
    images = images or []

    if len(images) == 1:
        _send_single_photo(token, chat_id, images[0])
    elif len(images) > 1:
        for i in range(0, len(images), MAX_MEDIA_GROUP_SIZE):
            _send_media_group(token, chat_id, images[i:i + MAX_MEDIA_GROUP_SIZE])

    resp = requests.post(
        f"{API_BASE}/bot{token}/sendMessage",
        data={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
