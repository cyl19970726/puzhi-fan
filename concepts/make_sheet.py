#!/usr/bin/env python3
"""make_sheet.py — 把 concept_1..5.png 拼成一张选型对比图 concepts/selection_sheet.png"""
import os
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
files = [os.path.join(BASE, f"concept_{i}.png") for i in range(1, 6)]
missing = [f for f in files if not os.path.exists(f)]
if missing:
    print("MISSING:", missing)
    raise SystemExit(1)

titles = ["1 鹅卵石极简塔", "2 复古收音机风", "3 无印日式极简", "4 未来机甲风", "5 氛围灯二合一"]

W, H = 1000, 1000
sheet = Image.new("RGBA", (W * 5 + 40 * 6, H + 130), (255, 255, 255, 255))
d = ImageDraw.Draw(sheet)
d.text((40, 30), "LiteCool S1 桌面制冷风扇 — 设计方向选型（选定后我按此方向建 3D）", fill=(40, 40, 45, 255))
for i, (f, t) in enumerate(zip(files, titles)):
    img = Image.open(f).convert("RGBA")
    img.thumbnail((W, H))
    x = 40 + i * (W + 40)
    sheet.paste(img, (x, 80))
    d.text((x + 10, 40 + H - 2), t, fill=(40, 40, 45, 255))
out = os.path.join(BASE, "selection_sheet.png")
sheet.save(out)
print("SHEET:", out)
