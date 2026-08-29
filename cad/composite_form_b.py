#!/usr/bin/env python3
"""composite_form_b.py — renders_form_b/{cream,green} (透明底) → renders_form_b_white/{cream,green} (白底 RGBA + 软接触投影)
思路复用 composite_form_a.py（不改原文件）：白底合成 + alpha 并集 + 每套五视图 contact sheet。
"""
import os
import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
WHITE = (255, 255, 255, 255)
VIEWS = ["front", "three_quarter", "side", "back", "top"]
TITLES = {
    "cream": "LiteCool S1 - Form B Retro Radio | CMF1 cream white + walnut (W200 x H150 x D120)",
    "green": "LiteCool S1 - Form B Retro Radio | CMF2 deep green + brass (W200 x H150 x D120)",
}

def add_soft_shadow(raw):
    ra = np.asarray(raw.convert("RGBA")).astype(np.int16)
    alpha = ra[..., 3]
    H, W = alpha.shape
    ys, xs = np.where(alpha > 10)
    shadow_alpha = np.zeros((H, W), dtype=np.float32)
    if len(ys) > 0:
        x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
        w, h = x1 - x0, y1 - y0
        cx = (x0 + x1) / 2
        cy = y1 + max(4, h * 0.02)
        rx = w * 0.40
        ry = max(6, h * 0.05)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        d2 = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        m = d2 <= 1
        a_sh = np.clip((1 - np.clip(d2, 0, 1)) ** 1.2, 0, 1) * 90
        shadow_alpha = np.where(m, a_sh, 0.0)
    shadow = np.zeros((H, W, 4), dtype=np.uint8)
    shadow[..., 0] = 95
    shadow[..., 1] = 95
    shadow[..., 2] = 100
    shadow[..., 3] = shadow_alpha.astype(np.uint8)
    canvas = Image.new("RGBA", (W, H), WHITE)
    canvas = Image.alpha_composite(canvas, Image.fromarray(shadow, "RGBA"))
    canvas = Image.alpha_composite(canvas, raw.convert("RGBA"))
    ca = np.asarray(canvas)
    final_alpha = np.maximum(shadow_alpha, alpha.astype(np.float32)).astype(np.uint8)
    out = np.dstack([ca[..., :3], final_alpha])
    return Image.fromarray(out, "RGBA")

def main():
    for cmf in ("cream", "green"):
        src = os.path.join(BASE, "renders_form_b", cmf)
        dst = os.path.join(BASE, "renders_form_b_white", cmf)
        os.makedirs(dst, exist_ok=True)
        tiles = []
        for v in VIEWS:
            raw = Image.open(os.path.join(src, f"{v}.png")).convert("RGBA")
            out = add_soft_shadow(raw)
            out.save(os.path.join(dst, f"{v}.png"))
            tiles.append((v, out))
            print("COMPOSITED:", os.path.join(dst, f"{v}.png"))
        W, H = tiles[0][1].size
        sw = W // 2
        thumb = [img.resize((sw, H // 2), Image.LANCZOS) for _, img in tiles]
        sheet = Image.new("RGBA", (sw * 5 + 6 * 20, H // 2 + 90), WHITE)
        d = ImageDraw.Draw(sheet)
        d.text((20, 12), TITLES[cmf], fill=(60, 60, 65, 255))
        for i, ((v, _), img) in enumerate(zip(tiles, thumb)):
            sheet.paste(img, (20 + i * (sw + 20), 60))
            d.text((20 + i * (sw + 20), 40), v, fill=(120, 120, 125, 255))
        sheet.save(os.path.join(dst, "contact_sheet.png"))
        print("SHEET:", os.path.join(dst, "contact_sheet.png"))

if __name__ == "__main__":
    main()
