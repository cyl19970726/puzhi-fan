#!/usr/bin/env python3
"""拼三稿截图为 contact sheet：纵向堆叠，每稿顶部加标注条。"""
from PIL import Image, ImageDraw, ImageFont
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = [
    ("shot_jia.png", "甲 · 工程极简（Linear / Vercel 式）"),
    ("shot_yi.png", "乙 · 产品画廊（Apple 产品页式）"),
    ("shot_bing.png", "丙 · 文档排印（Notion / 学术文档式）"),
]
LABEL_H = 64
GAP = 24
BG = (233, 233, 236)

imgs = [(Image.open(os.path.join(BASE, f)).convert("RGB"), label) for f, label in SHOTS]
W = max(im.width for im, _ in imgs)
H = sum(im.height + LABEL_H for im, _ in imgs) + GAP * (len(imgs) - 1)

sheet = Image.new("RGB", (W, H), BG)
try:
    font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 26)
except Exception:
    font = ImageFont.load_default()

y = 0
d = ImageDraw.Draw(sheet)
for im, label in imgs:
    d.rectangle([0, y, W, y + LABEL_H], fill=(24, 24, 27))
    d.text((28, y + LABEL_H // 2), label, font=font, fill=(250, 250, 250), anchor="lm")
    sheet.paste(im, (0, y + LABEL_H))
    y += LABEL_H + im.height + GAP

out = os.path.join(BASE, "contact_sheet.png")
sheet.save(out, optimize=True)
print(out, sheet.size)
