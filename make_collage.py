# -*- coding: utf-8 -*-
"""
複数作品のサムネイル画像とタイトルを1枚にまとめた「コラージュ画像」を生成する。
TikTok投稿を想定し、画像は常に9:16(1080x1920)の縦型キャンバスで出力する。
"""
import io
import os

import requests
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansJP-Regular.ttf")

CANVAS_W = 1080
CANVAS_H = 1920
COLS = 1
ROWS = 4
MAX_ITEMS = COLS * ROWS  # 4
CELL_W = CANVAS_W // COLS
CELL_H = CANVAS_H // ROWS
TITLE_H = 80
THUMB_H = CELL_H - TITLE_H
FONT_SIZE = 34
TEXT_STROKE_WIDTH = 2  # 文字を太く見せるための縁取り幅(フォントサイズは変えない)

COLORS = {
    "netflix": {"bg": (20, 20, 20), "text": (255, 255, 255)},
    "prime": {"bg": (5, 30, 60), "text": (255, 255, 255)},
}


def _download_image(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGB")


def _fit_thumbnail(img, w, h):
    """トリミングせず、アスペクト比を保ったまま指定枠に収まる最大サイズにリサイズする"""
    src_w, src_h = img.size
    scale = min(w / src_w, h / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    return img.resize((new_w, new_h))


def _truncate_text(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    while text and draw.textlength(text + "…", font=font) > max_width:
        text = text[:-1]
    return text + "…"


def make_collages(items, service):
    """
    items: [{"title": str, "thumbnail": str, ...}, ...]
    service: "netflix" または "prime"(背景色の切り替えに使用)
    戻り値: 1080x1920(9:16)のPNG画像bytesのリスト。1枚につきサムネイル最大4枚(MAX_ITEMS)で、
            5枚以上ある場合は複数枚に分割する。有効なサムネイルが1枚もなければ空リスト。
    """
    valid_items = [it for it in items if it.get("thumbnail")]
    chunks = [valid_items[i:i + MAX_ITEMS] for i in range(0, len(valid_items), MAX_ITEMS)]
    return [_render_collage(chunk, service) for chunk in chunks]


def _render_collage(valid_items, service):
    colors = COLORS[service]
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), colors["bg"])
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    n = len(valid_items)
    cols_used = min(COLS, n)
    rows_used = (n + cols_used - 1) // cols_used
    grid_h = rows_used * CELL_H
    y_offset = (CANVAS_H - grid_h) // 2
    # アイテムが1行に収まる場合のみ横方向も中央寄せする
    x_offset = (CANVAS_W - cols_used * CELL_W) // 2 if rows_used == 1 else 0

    for i, it in enumerate(valid_items):
        col = i % cols_used
        row = i // cols_used
        x = x_offset + col * CELL_W
        y = y_offset + row * CELL_H

        try:
            thumb = _fit_thumbnail(_download_image(it["thumbnail"]), CELL_W, THUMB_H)
            thumb_x = x + (CELL_W - thumb.width) // 2
            thumb_y = y + (THUMB_H - thumb.height) // 2
            canvas.paste(thumb, (thumb_x, thumb_y))
        except Exception:
            pass  # 画像が取得できなければ背景色の枠だけ残す

        title = _truncate_text(draw, it["title"], font, CELL_W - 24 - TEXT_STROKE_WIDTH * 4)
        draw.text(
            (x + 12, y + THUMB_H + 20),
            title,
            font=font,
            fill=colors["text"],
            stroke_width=TEXT_STROKE_WIDTH,
            stroke_fill=colors["text"],
        )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
