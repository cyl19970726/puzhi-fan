#!/usr/bin/env python3
"""
verify_renders.py — 渲染验收闸（像素级，无视觉依赖）

OWNED BY PARENT（审计方）。工人不得修改本文件——若某个检查因渲染管线行为无法满足，
修管线或上报；**削弱闸门即视为验收作弊**（前会话"假 QA 通过"教训）。

用法:
  python3 verify_renders.py [renders_dir]
默认检查 renders/（方柱款）；若存在 renders_capsule/（胶囊变体）也一并检查。
全部 PASS 时退出码 0，任一 FAIL 退出码 1。

检查依据: design-spec.md v2.0 §5/§7/附
  机身 168×53×47 squircle；正面=冰敷板(45×30 砂银)+数显窗(30×13,青色发光,带"8.0"数字)+腰线；
  背面=横向进风格栅(≥5 条暗带)；侧面(长边 168×47)=2 个硅胶按键；顶部=7 片涡轮格栅(深色)。
分段策略: 有 alpha 通道时按 alpha 分段（白底 RGBA）；否则按背景色差分（旧渲染兼容）。
"""
import os
import sys
import numpy as np
from PIL import Image

EXPECT = {
    "front":         {"name": "正面(出风网罩+数显+腰线)", "ratio": (0.35, 0.62), "face": "front"},
    "back":          {"name": "背面(进风格栅+热风排口)", "ratio": (0.35, 0.62), "face": "back"},
    "side":          {"name": "侧面(旋钮)",             "ratio": (0.35, 0.62), "face": "side"},
    "top":           {"name": "顶部(塔帽+底座)",       "ratio": (0.6, 1.4),   "face": "top"},
    "three_quarter": {"name": "3/4 视角",               "ratio": (0.3, 3.0),   "face": "any"},
}

OVEREXP_LIMIT   = 0.25
SHADOW_BAND_H   = 70
SHADOW_DARKER   = 15
MIN_ICE_FRAC    = 0.010
MIN_BLUE_FRAC   = 0.0015
MIN_DIGIT_PX    = 40
MIN_MINT_FRAC   = 0.002
MIN_GRILLE_DARK = 0.020
MIN_BAND_ROWS   = 5
MIN_BTN_DARK    = 0.003
MIN_TOP_DARK    = 0.025
MAX_BLUE_BACK   = 0.0003

def load(path):
    img = Image.open(path)
    if img.mode == "RGBA":
        arr = np.asarray(img).astype(np.int16)
        return arr[..., :3], arr[..., 3]
    return np.asarray(img.convert("RGB")).astype(np.int16), None

def bg_stats(arr):
    h, w = arr.shape[:2]
    pts = [(2, 2), (2, w - 3), (h - 3, 2), (h - 3, w - 3),
           (2, w // 2), (h - 3, w // 2), (h // 2, 2), (h // 2, w - 3)]
    cols = np.array([arr[y, x] for y, x in pts])
    return cols.mean(axis=0), cols.std()

def mask_color(arr, bg, tol=18):
    d = np.abs(arr - bg).max(axis=2)
    return d > tol

def bbox(mask):
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()

def frac(region, cond):
    if region.sum() == 0:
        return 0.0
    return float((region & cond).sum()) / float(region.sum())

class Checker:
    def __init__(self, label):
        self.label = label
        self.fails = []
        self.passes = []

    def check(self, name, ok, detail=""):
        if ok:
            self.passes.append(name)
        else:
            self.fails.append(f"{name} {detail}")

    def verdict(self):
        if self.fails:
            print(f"[FAIL] {self.label}: {'; '.join(self.fails)}")
            return False
        print(f"[PASS] {self.label} ({len(self.passes)} checks)")
        return True

def check_view(d, arr, alpha, c, expect):
    h, w = arr.shape[:2]
    if alpha is not None:
        bg, bgsd = bg_stats(arr[alpha < 8] if (alpha < 8).sum() > 100 else arr)
        c.check("白底", float(bg.mean()) >= 245, f"(bg={bg.mean():.0f})")
        mask = alpha >= 128
        shadow = (alpha >= 8) & (alpha < 128)
    else:
        bg, bgsd = bg_stats(arr)
        c.check("背景浅色", float(bg.mean()) >= 170, f"(bg={bg.mean():.0f})")
        mask = mask_color(arr, bg)
        shadow = None

    bb = bbox(mask)
    c.check("产品主体存在", bb is not None)
    if bb is None:
        return
    x0, y0, x1, y1 = bb
    pw, ph = x1 - x0, y1 - y0
    area_frac = mask.mean()
    c.check("产品占比合理", 0.04 < area_frac < 0.92, f"(area={area_frac:.2f})")

    ratio = pw / max(ph, 1)
    lo, hi = expect["ratio"]
    c.check("宽高比", lo <= ratio <= hi, f"(实测 {ratio:.2f}, 期望 {lo:.1f}-{hi:.1f})")

    sub = arr[y0:y1 + 1, x0:x1 + 1]
    submask = mask[y0:y1 + 1, x0:x1 + 1]
    bright = (sub.max(axis=2) >= 250)
    over = frac(submask, bright)
    c.check("过曝控制", over <= OVEREXP_LIMIT, f"(过曝 {over:.1%}, 限 {OVEREXP_LIMIT:.0%})")

    # 投影
    band_y1 = min(h - 1, y1 + SHADOW_BAND_H)
    if y1 + 1 < band_y1:
        if alpha is not None:
            sh = shadow[y1 + 1:band_y1, x0:x1 + 1]
            shadow_frac = sh.mean()
        else:
            below = arr[y1 + 1:band_y1, x0:x1 + 1]
            shadow_frac = (below.mean(axis=2) < bg.mean() - SHADOW_DARKER).mean()
        c.check("地面/接触投影", shadow_frac > 0.03, f"(阴影区 {shadow_frac:.1%})")
    else:
        c.check("地面/接触投影", False, "(产品下缘贴底，无投影区)")

    r, g, b = sub[..., 0].astype(int), sub[..., 1].astype(int), sub[..., 2].astype(int)
    lum = sub.mean(axis=2)
    sat = sub.max(axis=2) - sub.min(axis=2)

    blue = submask & (b > r + 25) & (b >= g - 10)   # 青/蓝（纯青 B==G，不能要求 b>g）
    silver = submask & (sat < 40) & (lum >= 110) & (lum <= 225)
    mint = submask & (g > r + 12) & (g > b + 2) & (sat > 15)
    dark = submask & (lum < 100)

    if expect["face"] == "front":
        c.check("出风网罩深色区", frac(submask, dark) >= MIN_GRILLE_DARK,
                f"(暗 {frac(submask, dark):.2%}, 限 {MIN_GRILLE_DARK:.2%})")
        c.check("数显青色发光", frac(submask, blue) >= MIN_BLUE_FRAC,
                f"(青 {frac(submask, blue):.2%}, 限 {MIN_BLUE_FRAC:.2%})")
        c.check("腰线薄荷绿", frac(submask, mint) >= MIN_MINT_FRAC,
                f"(薄荷绿 {frac(submask, mint):.2%}, 限 {MIN_MINT_FRAC:.2%})")
        # 数显窗内字形：与窗辉光色差异大的像素（数字笔画，白色或深色）
        by, bx = np.where(blue)
        if len(by):
            wx0, wy0, wx1, wy1 = bx.min(), by.min(), bx.max(), by.max()
            win = sub[wy0:wy1 + 1, wx0:wx1 + 1]
            win_blue = (win[..., 2].astype(int) > win[..., 0].astype(int) + 25) & \
                       (win[..., 2].astype(int) >= win[..., 1].astype(int) - 10)
            if win_blue.sum() > 0:
                glow = win[win_blue].mean(axis=0)
                diff = np.abs(win.astype(int) - glow).max(axis=2)
                digits = int((diff > 45).sum())
                c.check("数显窗内有字形", digits >= MIN_DIGIT_PX,
                        f"(字形像素 {digits}, 限 {MIN_DIGIT_PX})")
            else:
                c.check("数显窗内有字形", False, "(窗口内无青色像素)")
        else:
            c.check("数显窗内有字形", False, "(无青色窗口)")
    elif expect["face"] == "back":
        c.check("进风格栅暗像素", frac(submask, dark) >= MIN_GRILLE_DARK,
                f"(暗 {frac(submask, dark):.2%}, 限 {MIN_GRILLE_DARK:.2%})")
        rowfrac = (dark & submask).sum(axis=1) / np.maximum(submask.sum(axis=1), 1)
        bands = int((rowfrac > 0.15).sum())
        c.check("格栅横向暗带", bands >= MIN_BAND_ROWS, f"(暗带行 {bands}, 限 {MIN_BAND_ROWS})")
        c.check("背面无青色数显", frac(submask, blue) <= MAX_BLUE_BACK,
                f"(青 {frac(submask, blue):.2%}, 限 {MAX_BLUE_BACK:.2%})")
    elif expect["face"] == "side":
        c.check("旋钮/按键暗区", frac(submask, dark) >= MIN_BTN_DARK,
                f"(暗 {frac(submask, dark):.2%}, 限 {MIN_BTN_DARK:.2%})")
    # top 无逐元素检查：塔帽+底座同心轮廓由宽高比与占比覆盖

def check_dir(dpath):
    ok_all = True
    for name, expect in EXPECT.items():
        p = os.path.join(dpath, f"{name}.png")
        if not os.path.exists(p):
            print(f"[FAIL] {name}: 文件缺失 {p}")
            ok_all = False
            continue
        arr, alpha = load(p)
        c = Checker(f"{os.path.basename(dpath)}/{name}.png {expect['name']}")
        check_view(dpath, arr, alpha, c, expect)
        if not c.verdict():
            ok_all = False
    sheet = os.path.join(dpath, "contact_sheet.png")
    if not os.path.exists(sheet):
        print(f"[FAIL] contact_sheet.png 缺失")
        ok_all = False
    else:
        print(f"[PASS] contact_sheet.png 存在")
    return ok_all

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
    ok = check_dir(base)
    capsule = os.path.join(os.path.dirname(base), "renders_capsule")
    if os.path.isdir(capsule):
        print("--- capsule variant ---")
        ok = check_dir(capsule) and ok
    print("=== OVERALL:", "PASS" if ok else "FAIL", "===")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
