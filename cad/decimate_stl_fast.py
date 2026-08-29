#!/usr/bin/env python3
"""
LiteCool S1 — 大件 STL 减面（fast-simplification 二次边坍缩，保流形）
用法: python3 cad/decimate_stl_fast.py
规则: >10MB 的 STL 减面；齿轮类保 50% 面，其余保 25%。
减面后逐件验收：trimesh 水密 + 组件数不增 + 体积偏差 <2%，不过则保留原文件。
原文件备份在 cad/stl/_orig/（验收全部通过后由本脚本删除）。
"""
import os
import shutil
import trimesh
import fast_simplification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")
ORIG_DIR = os.path.join(STL_DIR, "_orig")
SIZE_GATE = 10 * 1024 * 1024

KEEP_RATIO = {           # 保留面数比例
    "M1_Pinion.stl": 0.50, "M1_Sector.stl": 0.50, "M1_Link.stl": 0.50,
    "Body.stl": 0.40, "M2_Bracket.stl": 0.50,
    "Knob.stl": 0.35, "CoolKey.stl": 0.35, "M7_Clip.stl": 0.35,
}


def decimate(path):
    fname = os.path.basename(path)
    keep = KEEP_RATIO.get(fname, 0.25)
    os.makedirs(ORIG_DIR, exist_ok=True)
    backup = os.path.join(ORIG_DIR, fname)
    if not os.path.exists(backup):
        shutil.copy2(path, backup)

    m = trimesh.load(backup)          # 从原件减，避免多次叠加
    v0, f0 = len(m.vertices), len(m.faces)
    vol0 = float(m.volume)
    n_comp0 = len(m.split(only_watertight=False))

    pts, faces = fast_simplification.simplify(
        m.vertices.astype("float32"), m.faces.astype("int64"),
        target_reduction=1.0 - keep, agg=7)
    d = trimesh.Trimesh(vertices=pts, faces=faces, process=True)
    d.merge_vertices()

    ok_wt = bool(d.is_watertight)
    n_comp = len(d.split(only_watertight=False))
    vol_dev = abs(float(d.volume) - vol0) / vol0 if vol0 else 1.0
    verdict = ok_wt and n_comp <= n_comp0 and vol_dev < 0.02
    print("%-22s f %d->%d watertight=%s comps=%d/%d vol_dev=%.3f%% -> %s" % (
        fname, f0, len(d.faces), ok_wt, n_comp, n_comp0, vol_dev * 100,
        "ACCEPT" if verdict else "REJECT-keep-orig"))
    if verdict:
        d.export(path)


def main():
    for f in sorted(os.listdir(STL_DIR)):
        p = os.path.join(STL_DIR, f)
        if f.endswith(".stl") and os.path.getsize(p) > SIZE_GATE:
            decimate(p)
    print("DECIMATE FAST DONE")


main()
