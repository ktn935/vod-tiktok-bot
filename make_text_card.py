# -*- coding: utf-8 -*-
"""
配信終了予定のキャプション文を、目立つ「文字だけの画像」にする。
TikTokは動画のキャプション欄が折りたたまれて読まれにくいため、
本文を画像化して動画内(スライドの1枚)として見せることで、
内容を確実に見てもらえるようにする。
"""
import io
import os
import re

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from compose import _header_label, CTA, NETFLIX_HASHTAGS, PRIME_HASHTAGS

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "NotoSansJP-Regular.ttf")
# 作品タイトルだけ、丸ゴシックでポップに目立つフォントに差し替える(M PLUS Rounded 1c, OFLライセンス)
TITLE_FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "MPLUSRounded1c-Black.ttf")

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
        "muted": (200, 200, 200),
        "badge_text": (229, 9, 20),
        "label": "NETFLIX",
        "hashtags": NETFLIX_HASHTAGS,
        # ヘッダーは純黒帯の上に乗るので、アクセントカラー(レッド)がそのまま映える
        "number_highlight": (229, 9, 20),
    },
    "prime": {
        # 公式ブランドカラー(brandcolorcode.com/amazon-prime-video): Hex #0779FF
        "band_fill": (7, 121, 255),
        "bg": (6, 14, 26),
        "accent": (7, 121, 255),
        "label_color": (255, 255, 255),
        "text": (255, 255, 255),
        "muted": (210, 222, 238),
        "badge_text": (7, 121, 255),
        "label": "PRIME VIDEO",
        "hashtags": PRIME_HASHTAGS,
        # ヘッダーは帯(アクセントカラーそのもの)の上に乗るため、同じ青だと消えてしまう。
        # リボンバッジと同じ黄色で代わりに強調する。
        "number_highlight": (255, 213, 0),
    },
}


def _font(size):
    return ImageFont.truetype(FONT_PATH, size)


def _title_font(size):
    return ImageFont.truetype(TITLE_FONT_PATH, size)


def _center_text(draw, text, font, cx, y, fill, stroke_width=0, stroke_fill=None):
    w = draw.textlength(text, font=font)
    draw.text(
        (cx - w / 2, y), text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_fill or fill,
    )


def _tracked_width(draw, text, font, tracking=0):
    """文字間隔(トラッキング)を加味した文字列の描画幅を計算する"""
    if not text:
        return 0
    return sum(draw.textlength(ch, font=font) for ch in text) + tracking * (len(text) - 1)


def _draw_tracked_text(draw, text, font, x, y, fill, tracking=0, stroke_width=0, stroke_fill=None):
    """1文字ずつ間隔を空けて描画する(大きい文字は詰め気味、小さい文字は開き気味にするため)"""
    cx = x
    for i, ch in enumerate(text):
        draw.text(
            (cx, y), ch, font=font, fill=fill,
            stroke_width=stroke_width, stroke_fill=stroke_fill or fill,
        )
        cx += draw.textlength(ch, font=font)
        if i < len(text) - 1:
            cx += tracking


def _center_tracked_text(draw, text, font, cx, y, fill, tracking=0, stroke_width=0, stroke_fill=None):
    total_w = _tracked_width(draw, text, font, tracking)
    _draw_tracked_text(
        draw, text, font, cx - total_w / 2, y, fill, tracking, stroke_width, stroke_fill,
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


_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002B00-\U00002BFF"
    "\U0001F1E6-\U0001F1FF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text):
    """絵文字グリフを持たないフォントで豆腐(□)化するのを防ぐため、絵文字を取り除く"""
    return _EMOJI_RE.sub("", text).strip()


_NUM_TOKEN_RE = re.compile(r"(\d{1,2}[:/]\d{1,2})")


def _split_number_tokens(text):
    """「08/23」「23:59」のような日付・時刻部分と、それ以外の文字列に分割する"""
    parts = _NUM_TOKEN_RE.split(text)
    return [(p, bool(_NUM_TOKEN_RE.fullmatch(p))) for p in parts if p]


def _draw_mixed_line_center(draw, tokens, font, cx, y, base_color, accent_color):
    """日付・時刻部分だけaccent_colorで強調しつつ、1行分を中央揃えで描く"""
    total_w = sum(draw.textlength(t, font=font) for t, _ in tokens)
    x = cx - total_w / 2
    for t, is_num in tokens:
        color = accent_color if is_num else base_color
        # 太字フォントを使っていないので、軽いstrokeで重みを足して存在感を出す
        draw.text((x, y), t, font=font, fill=color, stroke_width=1, stroke_fill=color)
        x += draw.textlength(t, font=font)


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


def _draw_drop_shadow(canvas, rect, radius, offset=(0, 10), blur=12, alpha=140):
    """rect([x0,y0,x1,y1])の角丸矩形の下に、ぼかした影を落として立体感を出す"""
    pad = blur * 2
    x0, y0, x1, y1 = rect
    dx, dy = offset
    sx0 = max(0, int(x0 - pad))
    sy0 = max(0, int(y0 - pad + dy))
    sx1 = min(CANVAS_W, int(x1 + pad))
    sy1 = min(CANVAS_H, int(y1 + pad + dy))
    if sx1 <= sx0 or sy1 <= sy0:
        return

    patch = Image.new("RGBA", (sx1 - sx0, sy1 - sy0), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(patch)
    pdraw.rounded_rectangle(
        [x0 - sx0 + dx, y0 - sy0 + dy, x1 - sx0 + dx, y1 - sy0 + dy],
        radius=radius, fill=(0, 0, 0, alpha),
    )
    patch = patch.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(patch, (sx0, sy0), patch)


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

    label_font = _font(60)
    _center_tracked_text(
        draw, theme["label"], label_font, cx, 54, fill=theme["label_color"],
        tracking=-3, stroke_width=2, stroke_fill=theme["label_color"],
    )

    # ---- 右上コーナーの斜めリボンバッジ(「あと◯日」で緊急性を演出) ----
    if days_remaining is not None:
        ribbon_bg = (255, 255, 255) if service == "netflix" else (255, 213, 0)
        ribbon_text = theme["accent"] if service == "netflix" else (20, 20, 20)
        ribbon_label = "本日ラスト" if days_remaining <= 0 else f"あと{days_remaining}日"
        _draw_corner_ribbon(canvas, ribbon_label, ribbon_bg, ribbon_text)
        draw = ImageDraw.Draw(canvas)

    header_text = _header_label(mode, reference_date)
    header_font = _font(38)
    header_max_w = CANVAS_W - MARGIN * 2
    header_tokens = _split_number_tokens(header_text)
    header_full_w = sum(draw.textlength(t, font=header_font) for t, _ in header_tokens)
    if header_full_w <= header_max_w:
        _draw_mixed_line_center(
            draw, header_tokens, header_font, cx, 160,
            theme["text"], theme["number_highlight"],
        )
    else:
        _draw_wrapped_center(
            draw, header_text, header_font, cx, 160, header_max_w,
            fill=theme["text"], max_lines=2, line_h=48,
        )

    # ---- 作品リスト(カード風の行を積み上げる) ----
    show_date = (mode == "weekend")
    list_y0 = BAND_H + 40
    list_y1 = CANVAS_H - FOOTER_H - 20
    available_h = list_y1 - list_y0

    title_font = _title_font(TITLE_FONT_SIZE)
    date_font = _font(28)
    badge_font = _title_font(32)

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
                fill=theme["text"],
            )

        if date_str:
            date_label = f"{date_str}まで"
            dw = _tracked_width(draw, date_label, date_font, tracking=1)
            _draw_tracked_text(
                draw, date_label, date_font,
                CANVAS_W - MARGIN - 20 - dw, row_top + block_h / 2 - 16,
                fill=theme["accent"], tracking=1,
                stroke_width=3, stroke_fill=(255, 255, 255),
            )

        y = row_top + block_h + ROW_GAP

    if remaining_count > 0:
        note_font = _font(32)
        _center_tracked_text(
            draw, f"ほか {remaining_count} 件は本文参照", note_font, cx, y + 10,
            fill=theme["muted"], tracking=1,
        )

    # ---- フッター(CTA + ハッシュタグ) ----
    footer_y0 = CANVAS_H - FOOTER_H
    draw.line([MARGIN, footer_y0, CANVAS_W - MARGIN, footer_y0], fill=theme["accent"], width=4)

    cta_font = _font(46)
    _center_text(
        draw, _strip_emoji(CTA), cta_font, cx, footer_y0 + 40, fill=(255, 255, 255),
        stroke_width=2, stroke_fill=(255, 255, 255),
    )

    tag_font = _font(30)
    _center_tracked_text(
        draw, _strip_emoji(theme["hashtags"]), tag_font, cx, footer_y0 + 130,
        fill=theme["muted"], tracking=1,
    )

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()
