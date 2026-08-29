"""
LiteCool S1 — 问题件源场景体素重构（Base / M2_Bracket）
用法: blender --background --python cad/fix_stl_voxel.py
背景: STL soup 补丁式修复对穿插盒体不稳定（补洞误填电池仓/底座零面积面 float32 反复再生）。
做法: exec build_core_eng.py 重建源场景 → 取零件世界坐标网格 → 坐标重映射(机器X→打印Z)
      → Voxel Remesh（保证水密流形的并集）→ 重导 STL。
"""
import bpy
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(BASE_DIR, "build_core_eng.py")
STL_DIR = os.path.join(BASE_DIR, "stl")

# 体素尺寸（m）：穿插拼接件重融为单一水密流形；特征尺度见注释
TARGETS = {"Body": 0.00040, "M2_Bracket": 0.00020}


def rebuild_scene():
    with open(BUILD_SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    stub = "bpy.ops.render.render(write_still=True)"
    assert stub in src
    src = src.replace(stub, "pass  # render stubbed")
    exec(compile(src, BUILD_SCRIPT, "exec"), {"__file__": BUILD_SCRIPT, "__name__": "__main__"})


def fix(name, voxel):
    src_obj = bpy.data.objects[name]
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(src_obj.evaluated_get(dg), depsgraph=dg)
    mesh.transform(src_obj.matrix_world)
    for v in mesh.vertices:
        x, y, z = v.co
        v.co = (-z, y, x)   # 机器(X高,Y前,Z右) → 打印(x=-Z,y=Y,z=X)
    mesh.update()

    tmp = bpy.data.objects.new("__voxel_tmp__", mesh)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.ops.object.select_all(action="DESELECT")
    tmp.select_set(True)
    bpy.context.view_layer.objects.active = tmp

    mesh.remesh_voxel_size = voxel
    bpy.ops.object.voxel_remesh()
    print("VOXEL %s: voxel=%.4fmm -> v=%d f=%d" % (name, voxel * 1000, len(mesh.vertices), len(mesh.polygons)))

    out = os.path.join(STL_DIR, name + ".stl")
    bpy.ops.wm.stl_export(filepath=out, export_selected_objects=True,
                          apply_modifiers=True, global_scale=1000.0, ascii_format=False)
    print("REEXPORTED:", out)
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(mesh)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rebuild_scene()
    os.makedirs(STL_DIR, exist_ok=True)
    for name, voxel in TARGETS.items():
        fix(name, voxel)
    print("VOXEL FIX DONE")


main()
