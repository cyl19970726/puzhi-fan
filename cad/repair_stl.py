"""
LiteCool S1 — STL 网格修复（Blender 无头）
用法: blender --background --python cad/repair_stl.py -- Base Body FrontPanel M2_Bracket
对指定零件（不带 .stl 后缀）:
  1. 合并重顶点(0.01mm) + 删除游离元素 + 溶解退化面（修零面积面/重面）;
  2. 非流形边(>2 link faces)：摘除其关联面后补洞;
  3. 边界边：holes_fill 补洞;
  4. 法线统一朝外（有符号体积为负则翻转）;
  5. 复检（边界/非流形/零面积/体积）全绿才覆盖写回 STL，否则报 REPAIR FAILED 退出 1。
"""
import bpy
import bmesh
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")


def diag(bm):
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    return boundary, nonman, zero, bm.calc_volume()


def repair(name):
    path = os.path.join(STL_DIR, name + ".stl")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.stl_import(filepath=path)
    obj = bpy.context.selected_objects[0]
    me = obj.data

    bm = bmesh.new()
    bm.from_mesh(me)
    print("REPAIR %s: before boundary=%d nonman=%d zero=%d vol=%.1f" % ((name,) + diag(bm)))

    # 1) 重顶点 + 退化 + 零面积面显式删除
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)
    bmesh.ops.dissolve_degenerate(bm, dist=0.005, edges=bm.edges)
    zfaces = [f for f in bm.faces if f.calc_area() < 1e-5]
    if zfaces:
        bmesh.ops.delete(bm, geom=zfaces, context="FACES")
    loose_v = [v for v in bm.verts if not v.link_edges]
    if loose_v:
        bmesh.ops.delete(bm, geom=loose_v, context="VERTS")

    # 2) 非流形边：摘面补洞（最多 5 轮）
    for _ in range(5):
        bad = [e for e in bm.edges if len(e.link_faces) > 2]
        if not bad:
            break
        faces = set()
        for e in bad:
            faces.update(e.link_faces)
        bmesh.ops.delete(bm, geom=list(faces), context="FACES")
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.01)

    # 3) 补洞 + 退化清扫（最多 5 轮，holes_fill 处理开放边界）
    for _ in range(5):
        bmesh.ops.dissolve_degenerate(bm, dist=0.005, edges=bm.edges)
        open_edges = [e for e in bm.edges if len(e.link_faces) == 1]
        if not open_edges:
            break
        res = bmesh.ops.holes_fill(bm, edges=open_edges)
        if not res.get("faces"):
            break
        zfaces = [f for f in bm.faces if f.calc_area() < 1e-5]
        if zfaces:
            bmesh.ops.delete(bm, geom=zfaces, context="FACES")

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bm.calc_volume() < 0:
        for f in bm.faces:
            f.normal_flip()

    boundary, nonman, zero, vol = diag(bm)
    print("REPAIR %s: after  boundary=%d nonman=%d zero=%d vol=%.1f" % (name, boundary, nonman, zero, vol))
    if boundary or nonman or zero or vol <= 0:
        print("REPAIR FAILED:", name)
        bm.free()
        return False

    bm.to_mesh(me)
    bm.free()
    me.update()

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                          apply_modifiers=True, ascii_format=False)
    print("REPAIRED:", path)
    return True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not argv:
        print("usage: repair_stl.py -- <PartName>...")
        sys.exit(2)
    ok = all(repair(n) for n in argv)
    sys.exit(0 if ok else 1)


main()
