#!/usr/bin/env python3
"""composite_renders.py — renders_raw (透明底) → renders/ (白底 RGBA + 软接触投影)

RGB = 白底合成；alpha = max(产品 alpha, 合成投影 alpha)。验收闸按 alpha 分段。
（Blender 5.1 EEVEE 的 shadow-catcher 无材质时渲染为不透明灰板，实测不可用，
故投影在合成层用软椭圆生成——白底产品图的标准做法。）
"""
import os
import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
WHITE = (255, 255, 255, 255)

def add_soft_shadow(raw):
    """在产品下缘加软椭圆接触投影，返回 (RGB白底合成, alpha)"""
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

def composite(src_dir, dst_dir, label):
    os.makedirs(dst_dir, exist_ok=True)
    views = ["front", "three_quarter", "side", "back", "top"]
    tiles = []
    for v in views:
        raw = Image.open(os.path.join(src_dir, f"{v}.png")).convert("RGBA")
        out = add_soft_shadow(raw)
        out.save(os.path.join(dst_dir, f"{v}.png"))
        tiles.append((v, out))
        print("COMPOSITED:", os.path.join(dst_dir, f"{v}.png"))
    # contact sheet：5 张竖幅并排
    W, H = tiles[0][1].size
    sheet = Image.new("RGBA", (W * 5 + 6 * 30, H + 120), WHITE)
    d = ImageDraw.Draw(sheet)
    d.text((30, 30), label, fill=(60, 60, 65, 255))
    for i, (v, img) in enumerate(tiles):
        sheet.paste(img, (30 + i * (W + 30), 100))
        d.text((30 + i * (W + 30), 70), v, fill=(120, 120, 125, 255))
    sheet.save(os.path.join(dst_dir, "contact_sheet.png"))
    print("SHEET:", os.path.join(dst_dir, "contact_sheet.png"))
    return {v: img for v, img in tiles}

def main():
    sq = composite(os.path.join(BASE, "renders_raw"), os.path.join(BASE, "renders"),
                   "LiteCool S1 — 桌面制冷风扇 (塔身O90x200 + 底座O110x30)")
    cap_raw = os.path.join(BASE, "renders_raw_capsule")
    if os.path.isdir(cap_raw) and os.listdir(cap_raw):
        cap = composite(cap_raw, os.path.join(BASE, "renders_capsule"),
                        "LiteCool S1 — 轮廓变体")
        # 变体对比：2×2 竖幅网格（正面对比在上，3/4 对比在下）
        W, H = sq["front"].size
        comp = Image.new("RGBA", (W * 2 + 3 * 30, H * 2 + 3 * 30), WHITE)
        d = ImageDraw.Draw(comp)
        d.text((30, 10), "轮廓对比 (同角度同 CMF)", fill=(60, 60, 65, 255))
        comp.paste(sq["front"], (30, 30))
        comp.paste(cap["front"], (W + 60, 30))
        comp.paste(sq["three_quarter"], (30, H + 60))
        comp.paste(cap["three_quarter"], (W + 60, H + 60))
        out = os.path.join(BASE, "renders", "variant_compare.png")
        comp.save(out)
        print("COMPARE:", out)
    else:
        print("SKIP capsule variant (renders_raw_capsule 不存在)")

if __name__ == "__main__":
    main()
