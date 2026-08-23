# -*- coding: utf-8 -*-
"""
配信終了予定のキャプション文を、目立つ「文字だけの画像」にする。
TikTokは動画のキャプション欄が折りたたまれて読まれにくいため、
本文を画像化して動画内(スライドの1枚)として見せることで、
内容を確実に見てもらえるようにする。
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

from compose import _header_label, CTA, NETFLIX_HASHTAGS, PRIME_HASHTAGS

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansJP-Regular.ttf")

CANVAS_W = 1080
CANVAS_H = 1920

BAND_H = 320
FOOTER_H = 260
MARGIN = 70

ROW_GAP = 24
BADGE_D = 70
TITLE_FONT_SIZE = 40
TITLE_LINE_H = 52
TITLE_MAX_LINES = 2

THEME = {
    "netflix": {
        # 公式ブランドガイド(brand.netflix.com)の「100%ブラック背景 + Netflixレッド」
        # (コントラスト比4.4:1)の組み合わせに合わせる。帯は敷かず黒背景にロゴを直接乗せる。
        "band_fill": None,
        "bg": (0, 0, 0),
        "accent": (229, 9, 20),
        "label_color": (229, 9, 20),
        "text": (255, 255, 255),
        "muted": (170, 170, 170),
        "badge_text": (229, 9, 20),
        "label": "NETFLIX",
        "hashtags": NETFLIX_HASHTAGS,
    },
    "prime": {
        # 公式ブランドカラー(brandcolorcode.com/amazon-prime-video): Hex #0779FF
        "band_fill": (7, 121, 255),
        "bg": (6, 14, 26),
        "accent": (7, 121, 255),
        "label_color": (255, 255, 255),
        "text": (255, 255, 255),
        "muted": (190, 205, 225),
        "badge_text": (7, 121, 255),
        "label": "PRIME VIDEO",
        "hashtags": PRIME_HASHTAGS,
    },
}


def _font(size):
    return ImageFont.truetype(FONT_PATH, size)


def _center_text(draw, text, font, cx, y, fill, stroke_width=0, stroke_fill=None):
    w = draw.textlength(text, font=font)
    draw.text(
        (cx - w / 2, y), text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_fill or fill,
    )


def _wrap_text(draw, text, font, max_width, max_lines=2):
    """textをmax_width内に収まるよう複数行に分割する。入りきらなければ末尾を…で省略する。"""
    lines = []
    remaining = text
    while remaining and len(lines) < max_lines:
        lo, hi = 1, len(remaining)
        best = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if draw.textlength(remaining[:mid], font=font) <= max_width:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best >= len(remaining):
            lines.append(remaining)
            remaining = ""
        elif len(lines) == max_lines - 1:
            trunc = remaining[:best]
            while trunc and draw.textlength(trunc + "…", font=font) > max_width:
                trunc = trunc[:-1]
            lines.append(trunc + "…")
            remaining = ""
        else:
            lines.append(remaining[:best])
            remaining = remaining[best:]
    return lines


def _draw_wrapped_center(draw, text, font, cx, y, max_width, fill, max_lines=2, line_h=48):
    lines = _wrap_text(draw, text, font, max_width, max_lines)
    for i, line in enumerate(lines):
        _center_text(draw, line, font, cx, y + i * line_h, fill=fill)


def _mix(c1, c2, t):
    """c1とc2をtの割合(0=c1, 1=c2)で線形補間する"""
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _radial_glow(canvas, cx, cy, radius, inner_color, outer_color, steps=90):
    """中心が明るく、外側にいくほどouter_colorへ溶け込む放射状グラデーションを描く"""
    draw = ImageDraw.Draw(canvas)
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        color = _mix(inner_color, outer_color, t)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def _draw_corner_ribbon(canvas, text, band_color, text_color=(255, 255, 255)):
    """右上コーナーに斜めのリボンバッジ(「あと◯日」等)を貼り付ける"""
    band_w, band_h = 520, 76
    ribbon = Image.new("RGBA", (band_w, band_h), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(ribbon)
    rdraw.rectangle([0, 0, band_w, band_h], fill=band_color + (255,))

    font = _font(38)
    tw = rdraw.textlength(text, font=font)
    rdraw.text(
        ((band_w - tw) / 2, (band_h - 38) / 2 - 8), text, font=font, fill=text_color,
        stroke_width=1, stroke_fill=text_color,
    )

    rotated = ribbon.rotate(-45, expand=True, resample=Image.BICUBIC)
    rw, rh = rotated.size
    x = CANVAS_W - rw + 190
    y = -rh + 190
    canvas.paste(rotated, (x, y), rotated)


def make_text_card(items, service, mode="daily", reference_date=None, days_remaining=None):
    """
    items: [{"title": str, "date": "MM/DD", ...}, ...]
    service: "netflix" または "prime"
    days_remaining: 完全に見れなくなるまでの残り日数(右上の斜めリボンバッジに使う)
    戻り値: 1080x1920のPNG画像bytes。itemsが空ならNone。
    """
    if not items:
        return None

    theme = THEME[service]
    canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), theme["bg"])

    # ---- 背景の放射状グロー(単色ベタ塗りより奥行きを出す) ----
    glow_inner = _mix(theme["accent"], theme["bg"], 0.72)
    _radial_glow(
        canvas, CANVAS_W // 2, int(CANVAS_H * 0.34), radius=CANVAS_W * 0.95,
        inner_color=glow_inner, outer_color=theme["bg"],
    )

    draw = ImageDraw.Draw(canvas)
    cx = CANVAS_W // 2

    # ---- 上部の帯(サービス名 + 見出し) ----
    if theme["band_fill"]:
        draw.rectangle([0, 0, CANVAS_W, BAND_H], fill=theme["band_fill"])
    elif service == "netflix":
        # 公式ブランドガイド(brand.netflix.com)の「100%ブラック背景 + Netflixレッド」
        # (コントラスト比4.4:1)を守るため、ロゴ周りだけは確実に純黒にする。
        draw.rectangle([0, 0, CANVAS_W, BAND_H], fill=(0, 0, 0))

    label_font = _font(56)
    _center_text(
        draw, theme["label"], label_font, cx, 56, fill=theme["label_color"],
        stroke_width=2, stroke_fill=theme["label_color"],
    )

    # ---- 右上コーナーの斜めリボンバッジ(「あと◯日」で緊急性を演出) ----
    if days_remaining is not None:
        ribbon_bg = (255, 255, 255) if service == "netflix" else (255, 213, 0)
        ribbon_text = theme["accent"] if service == "netflix" else (20, 20, 20)
        _draw_corner_ribbon(canvas, f"あと{days_remaining}日", ribbon_bg, ribbon_text)
        draw = ImageDraw.Draw(canvas)

    header_text = _header_label(mode, reference_date)
    header_font = _font(38)
    _draw_wrapped_center(
        draw, header_text, header_font, cx, 160, CANVAS_W - MARGIN * 2,
        fill=theme["text"], max_lines=2, line_h=48,
    )

    # ---- 作品リスト(カード風の行を積み上げる) ----
    show_date = (mode == "weekend")
    list_y0 = BAND_H + 40
    list_y1 = CANVAS_H - FOOTER_H - 20
    available_h = list_y1 - list_y0

    title_font = _font(TITLE_FONT_SIZE)
    date_font = _font(28)
    badge_font = _font(32)

    text_max_w = CANVAS_W - MARGIN * 2 - BADGE_D - 24 - 140

    blocks = []
    total_h = 0
    for it in items:
        lines = _wrap_text(draw, it["title"], title_font, text_max_w, TITLE_MAX_LINES)
        block_h = max(BADGE_D, len(lines) * TITLE_LINE_H) + ROW_GAP
        if blocks and total_h + block_h > available_h - 90:
            break
        blocks.append((lines, it.get("date") if show_date else None))
        total_h += block_h

    remaining_count = len(items) - len(blocks)
    extra_note_h = 0 if remaining_count == 0 else 70
    y = list_y0 + max(0, (available_h - total_h - extra_note_h) // 2)

    for i, (lines, date_str) in enumerate(blocks):
        block_h = max(BADGE_D, len(lines) * TITLE_LINE_H)
        row_top = y

        card_bg = tuple(min(255, c + 16) for c in theme["bg"])
        draw.rounded_rectangle(
            [MARGIN - 20, row_top - 12, CANVAS_W - MARGIN + 20, row_top + block_h + 12],
            radius=20, fill=card_bg,
        )

        badge_cy = row_top + block_h / 2
        draw.ellipse(
            [MARGIN, badge_cy - BADGE_D / 2, MARGIN + BADGE_D, badge_cy + BADGE_D / 2],
            fill=(255, 255, 255),
        )
        _center_text(
            draw, str(i + 1), badge_font, MARGIN + BADGE_D / 2, badge_cy - 18,
            fill=theme["badge_text"],
        )

        text_x = MARGIN + BADGE_D + 24
        text_y = row_top + (block_h - len(lines) * TITLE_LINE_H) / 2
        for li, line in enumerate(lines):
            draw.text(
                (text_x, text_y + li * TITLE_LINE_H), line, font=title_font,
                fill=theme["text"], stroke_width=1, stroke_fill=theme["text"],
            )

        if date_str:
            date_label = f"{date_str}まで"
            dw = draw.textlength(date_label, font=date_font)
            draw.text(
                (CANVAS_W - MARGIN - 20 - dw, row_top + block_h / 2 - 16),
                date_label, font=date_font, fill=theme["muted"],
            )

        y = row_top + block_h + ROW_GAP

    if remaining_count > 0:
        note_font = _font(32)
        _center_text(
            draw, f"ほか {remaining_count} 件は本文参照", note_font, cx, y + 10,
            fill=theme["muted"],
        )

    # ---- フッター(CTA + ハッシュタグ) ----
    footer_y0 = CANVAS_H - FOOTER_H
    draw.line([MARGIN, footer_y0, CANVAS_W - MARGIN, footer_y0], fill=theme["accent"], width=4)

    cta_font = _font(46)
    _center_text(
        draw, CTA, cta_font, cx, footer_y0 + 40, fill=(255, 255, 255),
        stroke_width=2, stroke_fill=(255, 255, 255),
    )

    tag_font = _font(30)
    _center_text(draw, theme["hashtags"], tag_font, cx, footer_y0 + 130, fill=theme["muted"])

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
