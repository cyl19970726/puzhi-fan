#!/usr/bin/env python3
"""make_sheet_v2.py — 把 concepts_v2 的成品拼成一张选型对比图 concepts_v2/contact_sheet.png"""
import os
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
entries = [
    ("A_1.png", "A-1 桌面挂机"),
    ("A_2.png", "A-2 桌面挂机(变体)"),
    ("B_cream.png", "B 复古收音机·奶油白胡桃木"),
    ("B_green.png", "B 复古收音机·墨绿黄铜"),
    ("D_1.png", "D-1 塔·认真版"),
    ("D_2.png", "D-2 塔·认真版(变体)"),
    ("W1.png", "W1 野卡·氛围灯"),
    ("W2.png", "W2 野卡·精工铝unibody"),
]
entries = [(f, t) for f, t in entries if os.path.exists(os.path.join(BASE, f))]
missing = [f for f, _ in entries]
if not entries:
    print("NO IMAGES")
    raise SystemExit(1)

COLS = 4
CELL_W, CELL_H = 760, 560
PAD = 24
TITLE_H = 90
rows = (len(entries) + COLS - 1) // COLS
sheet = Image.new("RGBA", (COLS * (CELL_W + PAD) + PAD, rows * (CELL_H + TITLE_H + PAD) + PAD), (245, 244, 242, 255))
d = ImageDraw.Draw(sheet)
for i, (f, t) in enumerate(entries):
    r, c = divmod(i, COLS)
    x = PAD + c * (CELL_W + PAD)
    y = PAD + r * (CELL_H + TITLE_H + PAD)
    img = Image.open(os.path.join(BASE, f)).convert("RGBA")
    img.thumbnail((CELL_W, CELL_H))
    sheet.paste(img, (x + (CELL_W - img.width) // 2, y + (CELL_H - img.height) // 2))
    d.text((x + 6, y + CELL_H + 24), t, fill=(40, 40, 45, 255))
out = os.path.join(BASE, "contact_sheet.png")
sheet.save(out)
print("SHEET:", out, "cells:", len(entries))
