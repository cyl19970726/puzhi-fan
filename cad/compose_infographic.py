#!/usr/bin/env python3
"""LiteCool S1 解构图鉴合成（PIL，A/B/D 三形态）——读 cad/infographic/{exploded_raw,anchors}{,_b,_d}
程序化排版：标题 + 爆炸主图 + 虚线引线/序号/中文标注 + 四角小面板 + 底部 icon 行。
坐标一律来自 Blender 相机投影（anchors.json），不手估。
标注文字单一事实源：cad/infographic/labels.json（价格取 data/bom.json 核验值）。
用法: python3 cad/compose_infographic.py [--form {a|b|d}]
"""
import json
import math
import os
import sys
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "infographic")
W, H = 1600, 2200

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"


def font(size, bold=False):
    want = "W6" if bold else "W3"
    for i in range(8):
        try:
            f = ImageFont.truetype(FONT_PATH, size, index=i)
            if want in f.getname()[1]:
                return f
        except Exception:
            break
    return ImageFont.truetype(FONT_PATH, size, index=0)


INK = (29, 29, 31)
MUTED = (110, 110, 115)
FAINT = (150, 150, 155)
BLUE = (26, 120, 200)
RED = (200, 80, 50)
LINK = (11, 110, 99)

# ---- 形态配置（标注清单在 labels.json，与 render_infographic / 工作台查看器共用）----
FORMS = {
    "a": {"suffix": "", "render_w": 1120, "subtitle": "桌面小空调 · 结构解析",
          "out": "LiteCool_S1_解构图鉴.png", "parts_json": "cad/assembly_a_parts.json", "count": 40,
          "dfm_y": 1340, "dfm_h": 240,
          "dfm": [("壁厚 2.0mm", "内外拔模锥台差集，非 solidify 近似"),
                  ("拔模 1.5°", "沿 Y 前后脱模，壁厚恒定"),
                  ("旋扣 IF-3", "转 15° 卡入，徒手可装"),
                  ("EVA 密封×6", "IF-2 漏风率 <5%（3×1.5 槽）"),
                  ("真孔风道", "后进风 / 前出风 / 右热排全贯通")]},
    "b": {"suffix": "_b", "render_w": 1120, "subtitle": "形态 B 复古收音机 · 结构解析",
          "out": "LiteCool_S1_解构图鉴_B.png", "parts_json": "cad/assembly_b_parts.json", "count": 35,
          "dfm_y": 1340, "dfm_h": 240,
          "dfm": [("壁厚 2.0mm", "主壳 1.5° 拔模，壁厚恒定"),
                  ("整面网罩", "真孔经纬条，覆盖正面 81%"),
                  ("旋扣 IF-3", "转 15° 卡入，徒手可装"),
                  ("EVA 密封×6", "IF-2 漏风率 <5%（3×1.5 槽）"),
                  ("真孔风道", "背冷进 / 背热进 / 顶热排全贯通")]},
    "d": {"suffix": "_d", "render_w": 820, "subtitle": "形态 D 塔·认真版 · 结构解析",
          "out": "LiteCool_S1_解构图鉴_D.png", "parts_json": "cad/assembly_d_parts.json", "count": 37,
          "dfm_y": 1440, "dfm_h": 215,
          "dfm": [("前后壳 2mm", "1.5° 拔模 + 外观分件线"),
                  ("百叶定角 20°", "横向非放射辐条（专利规避）"),
                  ("旋扣 IF-3", "转 15° 卡入，徒手可装"),
                  ("钢配重盘", "Ø88×3 低重心 F3 防倾"),
                  ("真孔风道", "后进风 / 前百叶出风 / 背 pill 热排")]},
}


def get_form():
    argv = sys.argv[1:]
    if "--form" in argv:
        return argv[argv.index("--form") + 1].lower()
    return os.environ.get("FORM", "a")


FORM = get_form()
CFG = FORMS[FORM]
with open(os.path.join(OUT, "labels.json"), encoding="utf-8") as fp:
    LABELS = [tuple(row) for row in json.load(fp)[FORM]]

# ---- 布局常量 ----
RENDER_W = CFG["render_w"]
PASTE_X = (W - RENDER_W) // 2          # a/b: 240
PASTE_Y = 350
PANEL_W, PANEL_H = 470, 250
LEFT_X = 222          # 左侧标注文字右缘
RIGHT_X = 1378        # 右侧标注文字左缘
LABEL_TOP = 620
LABEL_BOT = 1255


def dashed_line(d, p0, p1, fill, width=2, dash=7, gap=6):
    x0, y0 = p0; x1, y1 = p1
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1:
        return
    dx, dy = (x1 - x0) / length, (y1 - y0) / length
    t = 0.0
    while t < length:
        t2 = min(t + dash, length)
        d.line([(x0 + dx * t, y0 + dy * t), (x0 + dx * t2, y0 + dy * t2)], fill=fill, width=width)
        t = t2 + gap


def arrow_head(d, tip, back, fill, size=11):
    tx, ty = tip; bx, by = back
    ang = math.atan2(ty - by, tx - bx)
    pts = [(tx, ty)]
    for a in (ang + math.radians(155), ang - math.radians(155)):
        pts.append((tx + size * math.cos(a), ty + size * math.sin(a)))
    d.polygon(pts, fill=fill)


def text_size(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def panel(d, xy, wh, title):
    x, y = xy; w, h = wh
    d.rounded_rectangle([x, y, x + w, y + h], radius=18, fill=(255, 255, 255, 238),
                        outline=(0, 0, 0, 30), width=1)
    d.text((x + 22, y + 16), title, font=font(23, bold=True), fill=INK)
    d.line([(x + 22, y + 52), (x + w - 22, y + 52)], fill=(0, 0, 0, 25), width=1)


def panel_control(d, x, y):
    """控制系统框图：旋钮 → MCU → 风机/TEC/数显"""
    panel(d, (x, y), (PANEL_W, PANEL_H), "控制系统")
    f = font(17); fb = font(17, bold=True)
    cy = y + 122

    def box(cx, cy, w, h, s, bold=False):
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=9,
                            fill=(245, 246, 248), outline=(0, 0, 0, 60), width=1)
        tw, th = text_size(d, s, fb if bold else f)
        d.text((cx - tw / 2, cy - th / 2 - 1), s, font=fb if bold else f, fill=INK)
    box(x + 82, cy, 118, 44, "旋钮 100档")
    box(x + 238, cy, 118, 44, "MCU 状态机", bold=True)
    d.line([(x + 141, cy), (x + 176, cy)], fill=MUTED, width=2)
    arrow_head(d, (x + 178, cy), (x + 141, cy), MUTED)
    for i, s in enumerate(["风机 FOC", "TEC 驱动", "数显驱动"]):
        by = y + 84 + i * 44
        box(x + 382, by, 128, 34, s)
        d.line([(x + 297, cy), (x + 314, cy)], fill=MUTED, width=2)
        d.line([(x + 314, min(cy, by)), (x + 314, max(cy, by))], fill=MUTED, width=2)
        d.line([(x + 314, by), (x + 342, by)], fill=MUTED, width=2)
        arrow_head(d, (x + 344, by), (x + 314, by), MUTED, size=8)


def panel_airflow(d, x, y):
    """双风道气流示意"""
    panel(d, (x, y), (PANEL_W, PANEL_H), "双风道气流 · ADR-1 物理分断")
    f = font(16)
    rows = [(y + 102, BLUE, "冷风道", ["后进风", "风机", "冷鳍", "前出风"]),
            (y + 182, RED, "热风道", ["后进风", "TEC热端", "铜鳍", "右侧排"])]
    for ry, col, name, segs in rows:
        d.text((x + 24, ry - 11), name, font=font(17, bold=True), fill=col)
        sx = x + 110
        step = (PANEL_W - 140) / len(segs)
        for i, s in enumerate(segs):
            cx = sx + step * (i + 0.5)
            tw, _ = text_size(d, s, f)
            d.text((cx - tw / 2, ry - 9), s, font=f, fill=INK)
            if i < len(segs) - 1:
                x0 = cx + tw / 2 + 6
                x1 = sx + step * (i + 1.5) - text_size(d, segs[i + 1], f)[0] / 2 - 8
                d.line([(x0, ry), (x1, ry)], fill=col, width=3)
                arrow_head(d, (x1, ry), (x0, ry), col, size=9)


def panel_dfm(d, x, y, w, h, items):
    panel(d, (x, y), (w, h), "DFM 要点（开模接口）")
    f = font(17); fb = font(17, bold=True)
    yy = y + 70
    gap = min(34, (h - 86) // max(1, len(items)))   # 面板矮时自动收紧行距，防文字出框
    for k, v in items:
        d.ellipse([x + 24, yy + 7, x + 30, yy + 13], fill=LINK)
        d.text((x + 40, yy), k, font=fb, fill=INK)
        d.text((x + 40 + text_size(d, k, fb)[0] + 12, yy), v, font=f, fill=MUTED)
        yy += gap


def icon_snowflake(d, cx, cy, r, col):
    for k in range(6):
        a = math.radians(60 * k)
        x1, y1 = cx + r * math.cos(a), cy + r * math.sin(a)
        d.line([(cx, cy), (x1, y1)], fill=col, width=3)
        bx, by = cx + r * 0.55 * math.cos(a), cy + r * 0.55 * math.sin(a)
        for da in (35, -35):
            a2 = a + math.radians(180 + da)
            d.line([(bx, by), (bx + r * 0.3 * math.cos(a2), by + r * 0.3 * math.sin(a2))], fill=col, width=3)


def icon_display(d, cx, cy, r, col):
    d.rounded_rectangle([cx - r, cy - r * 0.62, cx + r, cy + r * 0.62], radius=8, outline=col, width=3)
    s = "22.0°"
    f = font(int(r * 0.52), bold=True)
    tw, th = text_size(d, s, f)
    d.text((cx - tw / 2, cy - th / 2 - 2), s, font=f, fill=col)


def icon_dual_duct(d, cx, cy, r, col):
    d.line([(cx - r, cy - r * 0.35), (cx + r * 0.7, cy - r * 0.35)], fill=BLUE, width=4)
    arrow_head(d, (cx + r * 0.85, cy - r * 0.35), (cx + r * 0.5, cy - r * 0.35), BLUE, size=12)
    d.line([(cx + r, cy + r * 0.35), (cx - r * 0.7, cy + r * 0.35)], fill=RED, width=4)
    arrow_head(d, (cx - r * 0.85, cy + r * 0.35), (cx - r * 0.5, cy + r * 0.35), RED, size=12)


def icon_battery(d, cx, cy, r, col):
    d.rounded_rectangle([cx - r * 0.85, cy - r * 0.4, cx + r * 0.55, cy + r * 0.4], radius=6,
                        outline=col, width=3)
    d.rectangle([cx + r * 0.55, cy - r * 0.16, cx + r * 0.75, cy + r * 0.16], fill=col)
    d.polygon([(cx - r * 0.05, cy - r * 0.32), (cx - r * 0.3, cy + r * 0.06),
               (cx - r * 0.06, cy + r * 0.06), (cx - r * 0.16, cy + r * 0.34),
               (cx + r * 0.2, cy - r * 0.06), (cx - r * 0.02, cy - r * 0.06)], fill=col)


def main():
    with open(os.path.join(OUT, "anchors%s.json" % CFG["suffix"]), encoding="utf-8") as fp:
        aj = json.load(fp)
    anchors = aj["anchors"]
    raw = Image.open(os.path.join(OUT, "exploded_raw%s.png" % CFG["suffix"])).convert("RGBA")
    # 按 alpha 内容包围盒裁剪，主图内容撑满（锚点同步减裁剪偏移）
    crop = raw.getbbox()
    raw = raw.crop(crop)
    scale = RENDER_W / raw.width
    render_h = round(raw.height * scale)
    raw = raw.resize((RENDER_W, render_h), Image.LANCZOS)

    img = Image.new("RGBA", (W, H), (244, 245, 247, 255))
    d = ImageDraw.Draw(img)

    # ---------- 标题 ----------
    s = "产 品 解 构 图 鉴"
    f = font(26)
    d.text(((W - text_size(d, s, f)[0]) / 2, 62), s, font=f, fill=MUTED)
    s = "LiteCool S1"
    f = font(98, bold=True)
    d.text(((W - text_size(d, s, f)[0]) / 2, 104), s, font=f, fill=INK)
    s = CFG["subtitle"]
    f = font(36)
    d.text(((W - text_size(d, s, f)[0]) / 2, 232), s, font=f, fill=INK)
    d.line([(W / 2 - 260, 300), (W / 2 + 260, 300)], fill=(0, 0, 0, 40), width=1)

    # ---------- 主图 ----------
    img.alpha_composite(raw, (PASTE_X, PASTE_Y))

    def to_canvas(name):
        a = anchors[name]
        return (PASTE_X + (a["px"] - crop[0]) * scale, PASTE_Y + (a["py"] - crop[1]) * scale)

    # ---------- 小面板 ----------
    panel_control(d, 40, 330)
    panel_airflow(d, W - 40 - PANEL_W, 330)
    panel_dfm(d, 40, CFG["dfm_y"], PANEL_W, CFG["dfm_h"], CFG["dfm"])

    # ---------- 引线标注 ----------
    f_lab = font(21, bold=True)
    f_note = font(16)
    entries = []
    for i, (name, title, note) in enumerate(LABELS):
        ax, ay = to_canvas(name)
        entries.append({"i": i + 1, "name": name, "title": title, "note": note,
                        "ax": ax, "ay": ay, "side": "L" if ax < W / 2 else "R"})

    # 左右平衡：差距 >2 时把靠中线的条目挪去少的一侧
    for _ in range(8):
        Ls = [e for e in entries if e["side"] == "L"]
        Rs = [e for e in entries if e["side"] == "R"]
        if abs(len(Ls) - len(Rs)) <= 2:
            break
        heavy, light, hs, ls = (Ls, Rs, "L", "R") if len(Ls) > len(Rs) else (Rs, Ls, "R", "L")
        heavy.sort(key=lambda e: abs(e["ax"] - W / 2))
        heavy[0]["side"] = ls

    def layout_side(items, top, bot):
        items.sort(key=lambda e: e["ay"])
        gap = 62
        ys = [min(max(e["ay"], top), bot) for e in items]
        for k in range(1, len(ys)):                    # 前向：保序 + 最小间距
            ys[k] = max(ys[k], ys[k - 1] + gap)
        if ys and ys[-1] > bot:                        # 溢出底部：从 bot 反向压回
            ys[-1] = bot
            for k in range(len(ys) - 2, -1, -1):
                ys[k] = min(ys[k], ys[k + 1] - gap)
        if ys and ys[0] < top:                         # 再溢出顶部：从 top 前向推开
            ys[0] = top
            for k in range(1, len(ys)):
                ys[k] = max(ys[k], ys[k - 1] + gap)
        for e, y in zip(items, ys):
            e["ly"] = y

    layout_side([e for e in entries if e["side"] == "L"], LABEL_TOP, LABEL_BOT)
    layout_side([e for e in entries if e["side"] == "R"], LABEL_TOP, LABEL_BOT)

    leader_col = (60, 60, 64, 190)
    num_r = 14
    nf = font(16, bold=True)
    for e in entries:
        ax, ay, ly = e["ax"], e["ay"], e["ly"]
        tw1, _ = text_size(d, e["title"], f_lab)
        tw2, _ = text_size(d, e["note"], f_note)
        if e["side"] == "L":
            lx0 = LEFT_X - max(tw1, tw2)
            d.text((LEFT_X - tw1, ly), e["title"], font=f_lab, fill=INK)
            d.text((LEFT_X - tw2, ly + 29), e["note"], font=f_note, fill=MUTED)
            conn = (LEFT_X + 10, ly + 13)                    # 引线从文字右缘出（朝零件）
            num_c = (max(lx0 - num_r - 8, num_r + 6), ly + 13)   # 序号圆在文字块外侧（钳住不出画布）
        else:
            d.text((RIGHT_X, ly), e["title"], font=f_lab, fill=INK)
            d.text((RIGHT_X, ly + 29), e["note"], font=f_note, fill=MUTED)
            conn = (RIGHT_X - 10, ly + 13)
            num_c = (min(RIGHT_X + max(tw1, tw2) + num_r + 8, W - 8 - num_r), ly + 13)
        dashed_line(d, conn, (ax, ay), leader_col, width=2)
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=(255, 255, 255, 230),
                  outline=(40, 40, 44, 255), width=2)
        d.ellipse([num_c[0] - num_r, num_c[1] - num_r, num_c[0] + num_r, num_c[1] + num_r],
                  fill=(29, 29, 31, 255))
        ns = str(e["i"])
        nw, nh = text_size(d, ns, nf)
        d.text((num_c[0] - nw / 2, num_c[1] - nh / 2 - 1), ns, font=nf, fill=(255, 255, 255))

    # ---------- 底部 icon 行 ----------
    d.line([(120, 1660), (W - 120, 1660)], fill=(0, 0, 0, 25), width=1)
    icons = [("真 TEC 制冷", icon_snowflake), ("出风温度数显", icon_display),
             ("双风道", icon_dual_duct), ("充插两用", icon_battery)]
    cell = 300
    x0 = (W - cell * len(icons)) / 2 + cell / 2
    f_ic = font(22, bold=True)
    icy = 1790
    for k, (name, fn) in enumerate(icons):
        cx = x0 + k * cell
        fn(d, cx, icy, 34, INK)
        d.text((cx - text_size(d, name, f_ic)[0] / 2, icy + 56), name, font=f_ic, fill=INK)
        if k:
            d.line([(cx - cell / 2, icy - 34), (cx - cell / 2, icy + 88)], fill=(0, 0, 0, 22), width=1)

    # ---------- 页脚 ----------
    s = "数据源：%s（%d 件 DFM 级装配体）· data/bom.json（2026-08-28 1688 核验）｜BOM ≈¥73 · 出厂 ≈¥82 vs 目标 ¥55–65（R8 未决）" % (
        CFG["parts_json"], CFG["count"])
    f = font(15)
    d.text(((W - text_size(d, s, f)[0]) / 2, H - 46), s, font=f, fill=FAINT)

    out_path = os.path.join(OUT, CFG["out"])
    img.convert("RGB").save(out_path, quality=95)
    print("COMPOSED:", out_path, img.size)


if __name__ == "__main__":
    main()
