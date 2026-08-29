"""
LiteCool S1 — STL 逐件可打印校验（Blender 无头）
用法: blender --background --python cad/validate_stl.py
对 cad/stl/*.stl 逐件:
  1. 流形检查: 边界边/非流形边(bmesh link_faces!=2)、游离元素、重顶点、零面积面;
  2. 法线/水密: bmesh 有符号体积(负=法线翻内);
  3. 壁厚抽样: BVH 沿 -法线 射线, ≤300 点/件, 记录 min/p5/median(mm);
  4. 尺寸: 包围盒(mm, 打印坐标 x=宽 z=高 y=深)。
结果写 cad/stl/_validation.json（不生成 md，md 由 gen_validation_report.py 合并 trimesh 交叉校验后产出）。
"""
import bpy
import bmesh
import os
import json
import math
import statistics
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")
OUT_JSON = os.path.join(STL_DIR, "_validation.json")

THICK_MIN = 1.2          # 关键配合面最小壁厚 mm
SAMPLE_MAX = 300
EPS_IN = 0.02            # 射线起点内缩 mm


def check_one(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    me = obj.data

    bm = bmesh.new()
    bm.from_mesh(me)
    n_edges = len(bm.edges)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    zero_area = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    volume = bm.calc_volume()

    # 壁厚抽样（网格已是 mm）
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()
    bvh = BVHTree.FromBMesh(bm)
    th = []
    n_v = len(bm.verts)
    stride = max(1, n_v // SAMPLE_MAX)
    for i in range(0, n_v, stride):
        v = bm.verts[i]
        n = v.normal
        if n.length < 1e-6:
            continue
        n = n.normalized()
        origin = v.co - n * EPS_IN
        loc, norm, idx, dist = bvh.ray_cast(origin, -n, 1000.0)
        if loc is not None and norm is not None:
            # 掠射命中（命中面法线与射线近垂直）=棱边伪影，不计为壁厚；直穿命中 norm·n≈-1
            if norm.dot(n) > -0.5:
                continue
            t = (loc - v.co).length
            if t > 1e-4:
                th.append(t)
    bm.free()

    th.sort()
    res = {
        "file": os.path.basename(path),
        "verts": len(me.vertices),
        "faces": len(me.polygons),
        "edges": n_edges,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "zero_area_faces": zero_area,
        "volume_mm3": round(volume, 1),
        "normals_outward": volume > 0,
        "bbox_mm": [round(d, 2) for d in obj.dimensions],
        "thickness_samples": len(th),
        "thickness_min": round(th[0], 3) if th else None,
        "thickness_p5": round(th[max(0, int(len(th) * 0.05))], 3) if th else None,
        "thickness_median": round(statistics.median(th), 3) if th else None,
    }
    res["watertight"] = (boundary == 0 and nonmanifold == 0)
    res["thickness_ok"] = bool(th) and res["thickness_p5"] >= THICK_MIN
    res["pass"] = res["watertight"] and res["normals_outward"] and zero_area == 0
    print("CHECKED: %(file)-24s watertight=%(watertight)s vol=%(volume_mm3)s "
          "thk(min/p5/med)=%(thickness_min)s/%(thickness_p5)s/%(thickness_median)s "
          "bbox=%(bbox_mm)s pass=%(pass)s" % res)
    return res


def main():
    files = sorted(f for f in os.listdir(STL_DIR) if f.endswith(".stl"))
    results = [check_one(os.path.join(STL_DIR, f)) for f in files]
    with open(OUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(results, fp, ensure_ascii=False, indent=1)
    n_pass = sum(1 for r in results if r["pass"])
    print("VALIDATION DONE: %d/%d manifold-pass, json=%s" % (n_pass, len(results), OUT_JSON))


main()
