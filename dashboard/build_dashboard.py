#!/usr/bin/env python3
"""build_dashboard.py — 构建单文件产品工作台（竞品分析 + 设计概念图 + 3D 拆分）
用法: python3 build_dashboard.py
输出: dashboard/LiteCool_S1_workbench.html（file:// 双击即开，无需服务器）
"""
import base64
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.join(BASE, "..", "research")
CONCEPTS = os.path.join(BASE, "..", "concepts")

tpl = open(os.path.join(BASE, "app_template.html"), encoding="utf-8").read()

def load_json(path, fallback):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print("WARN json:", path, e)
    return fallback

parts = load_json(os.path.join(BASE, "parts.json"), {})
glb = open(os.path.join(BASE, "model.glb"), "rb").read()
competitors = load_json(os.path.join(RESEARCH, "competitors.json"), {"updated": "—", "items": []})
# 竞品图内联
for it in competitors.get("items", []):
    img_path = it.get("image", "")
    full = os.path.join(os.path.dirname(BASE), img_path) if img_path else ""
    if full and os.path.exists(full):
        try:
            it["img"] = "data:image/jpeg;base64," + base64.b64encode(open(full, "rb").read()).decode("ascii")
        except Exception:
            pass
print("competitor imgs inlined:", sum(1 for it in competitors.get("items", []) if "img" in it))
insights = load_json(os.path.join(RESEARCH, "insights.json"), [])

concept_titles = {
    "form_a": "A 立式塔 —— 品类主流形态的再设计（圆润塔身+大圆网罩+外露摇头转轴）",
    "form_b": "B 圆头台扇 —— 球头+金属立杆+加重圆盘底座（可俯仰+摇头）",
    "form_c": "C 复古收音机 —— 圆角方体+大圆网罩+旋钮阵列+皮革提手",
    "form_d": "D 环形无叶 —— 细环出风圈+短柱底座（专利风险，仅形态参考）",
    "form_e": "E 灯塔氛围 —— 细塔+顶部暖光灯环+下部出风",
    "form_f": "F 卡片折叠 —— 超薄卡片+折叠支架+磁吸底座（便携桌面两用）",
}
concepts = []
for key in ["form_a", "form_b", "form_c", "form_d", "form_e", "form_f"]:
    p = os.path.join(CONCEPTS, f"{key}.png")
    if os.path.exists(p):
        b64 = base64.b64encode(open(p, "rb").read()).decode("ascii")
        concepts.append({"src": "data:image/png;base64," + b64, "title": concept_titles.get(key, key)})
print("concepts inlined:", len(concepts))

exploded = None
ep = os.path.join(CONCEPTS, "exploded.png")
if os.path.exists(ep):
    exploded = "data:image/png;base64," + base64.b64encode(open(ep, "rb").read()).decode("ascii")
print("exploded inlined:", bool(exploded))

out = tpl.replace("window.__PARTS_DATA__", "(" + json.dumps(parts, ensure_ascii=False) + ")")
out = out.replace("window.__GLB_DATA_URI__", "(" + json.dumps("data:model/gltf-binary;base64," + base64.b64encode(glb).decode("ascii")) + ")")
out = out.replace("window.__COMPETITORS__", "(" + json.dumps(competitors, ensure_ascii=False) + ")")
out = out.replace("window.__INSIGHTS__", "(" + json.dumps(insights, ensure_ascii=False) + ")")
out = out.replace("window.__CONCEPTS__", "(" + json.dumps(concepts, ensure_ascii=False) + ")")
out = out.replace("window.__EXPLODED__", "(" + json.dumps(exploded) + ")")

out_path = os.path.join(BASE, "LiteCool_S1_workbench.html")
open(out_path, "w", encoding="utf-8").write(out)
print("BUILT:", out_path, "| size MB:", round(len(out) / 1e6, 1), "| competitors:", len(competitors.get("items", [])), "| insights:", len(insights), "| parts:", len(parts) - 1)
