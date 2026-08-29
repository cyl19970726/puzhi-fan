"""
LiteCool S1 — 大件 STL 平面抽取减面（体素网格 → 上传友好体积）
用法: blender --background --python cad/decimate_stl.py
对 cad/stl/ 中 >10MB 的 STL：Decimate(Planar, 5°) 减面 → 覆盖写回 → 由 validate_stl.py 复检。
平面抽取只合并共面三角，特征边/孔/齿形不受影响；减面后必须重新过校验。
"""
import bpy
import bmesh
import os
import math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")
SIZE_GATE = 10 * 1024 * 1024   # >10MB 才减
ANGLE = math.radians(5.0)


def manifold_ok(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bad = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    vol = bm.calc_volume()
    bm.free()
    return bad == 0 and zero == 0 and vol > 0


def decimate(path):
    before = os.path.getsize(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    f0 = len(obj.data.polygons)

    mod = obj.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "DISSOLVE"
    mod.angle_limit = ANGLE
    dg = bpy.context.evaluated_depsgraph_get()
    new_me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    obj.modifiers.remove(mod)
    old_me = obj.data
    obj.data = new_me
    bpy.data.meshes.remove(old_me)
    f1 = len(new_me.polygons)

    if not manifold_ok(new_me):
        print("DECIMATE SKIP (manifold broken): %s" % os.path.basename(path))
        return

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                          apply_modifiers=True, ascii_format=False)
    after = os.path.getsize(path)
    print("DECIMATED: %-22s f %d->%d  %.1fMB->%.1fMB" %
          (os.path.basename(path), f0, f1, before / 1e6, after / 1e6))


def main():
    for f in sorted(os.listdir(STL_DIR)):
        p = os.path.join(STL_DIR, f)
        if f.endswith(".stl") and os.path.getsize(p) > SIZE_GATE:
            decimate(p)
    print("DECIMATE DONE")


main()
