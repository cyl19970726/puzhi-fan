"""
LiteCool S1 — A 类 3D 打印件 STL 导出（形态 A 工程级装配体）
用法: blender --background --python cad/export_stl.py
流程:
  1. exec build_core_eng.py 重建工程装配体（渲染调用打桩跳过，几何/GLB/parts.json 照常）；
  2. 按 PRINT_PARTS 名单逐件复制网格 → 应用世界变换 → 重映射坐标
     （机器约定 X=高度/Y=前/Z=右 → 打印世界 Z=上/Y=前/X=-右）→ 导出 STL（m→mm, ×1000）；
  3. 打印逐件摘要（顶点/面数/包围盒 mm）供校验报告引用。
输出: cad/stl/<PartName>.stl（每件一个文件，单位 mm，Z=上）
"""
import bpy
import os
import sys
import math
import mathutils

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(BASE_DIR, "build_core_eng.py")
STL_DIR = os.path.join(BASE_DIR, "stl")

# A 类打印件名单（对照 docs/prototype_3d_print_route.md §1-A + assembly_a_parts.json）
PRINT_PARTS = [
    "Body",          # 后壳/主壳 2mm 壁
    "FrontPanel",    # 前壳面板
    "Louver_0", "Louver_1", "Louver_2",   # 导风板 ×3
    "Base",          # 配重底座
    "SkidPad",       # 防滑圈（TPU 95A）
    "M5_Separator",  # L 形中隔板
    "M5_ColdDuct",   # 冷风道
    "M5_HotDuct",    # 热风道导流板
    "M2_Bracket",    # 电池仓支架
    "M1_Pinion",     # 小齿轮 m0.8 12T
    "M1_Sector",     # 扇形齿轮 m0.8 18T
    "M1_Link",       # 导风联动杆
    "Knob",          # 旋钮
    "CoolKey",       # 制冷键
    "M7_Clip",       # 数显窗卡扣+遮光筋
    "M1_Bosses",     # 底座螺丝柱 ×3
    "Band",          # 腰线
    "M6_TwistLock",  # 前网罩旋扣 ×3（M6 网罩类）
    "IntakeGrille",  # 后进风格栅
    "HotVent_L",     # 左侧辅助进风格栅
    "HotVent_R",     # 右侧热排格栅
]


def rebuild_scene():
    """exec build_core_eng.py，渲染打桩（几何构建 + GLB/parts.json 导出照常执行）"""
    with open(BUILD_SCRIPT, "r", encoding="utf-8") as f:
        src = f.read()
    stub = "bpy.ops.render.render(write_still=True)"
    assert stub in src, "build_core_eng.py 渲染调用点变了，需要更新打桩"
    src = src.replace(stub, "pass  # render stubbed by export_stl.py")
    g = {"__file__": BUILD_SCRIPT, "__name__": "__main__"}
    exec(compile(src, BUILD_SCRIPT, "exec"), g)


def export_part_stl(name):
    src_obj = bpy.data.objects.get(name)
    if src_obj is None or src_obj.type != "MESH":
        print("MISSING:", name)
        return None

    # 依赖图求值后的网格（含未 apply 的修改器）→ 世界坐标
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = src_obj.evaluated_get(dg)
    mesh = bpy.data.meshes.new_from_object(eval_obj, depsgraph=dg)
    mesh.transform(src_obj.matrix_world)

    # 坐标重映射：机器 (X=高, Y=前, Z=右) → 打印世界 (x=-Z机, y=Y机, z=X机)
    # 真旋转（行列式 +1，无镜像）：new = R_y(-90°) @ old  =>  (-z, y, x)
    for v in mesh.vertices:
        x, y, z = v.co
        v.co = (-z, y, x)
    mesh.update()

    tmp = bpy.data.objects.new("__stl_tmp__", mesh)
    bpy.context.scene.collection.objects.link(tmp)
    bpy.ops.object.select_all(action="DESELECT")
    tmp.select_set(True)
    bpy.context.view_layer.objects.active = tmp

    os.makedirs(STL_DIR, exist_ok=True)
    out = os.path.join(STL_DIR, name + ".stl")
    bpy.ops.wm.stl_export(
        filepath=out,
        export_selected_objects=True,
        apply_modifiers=True,
        global_scale=1000.0,   # m → mm
        ascii_format=False,
        forward_axis="Y",
        up_axis="Z",
    )

    # 摘要（mm）
    bb = [v[:] for v in tmp.bound_box]
    xs = [p[0] * 1000 for p in bb]
    ys = [p[1] * 1000 for p in bb]
    zs = [p[2] * 1000 for p in bb]
    dims = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    print("EXPORTED: %-14s v=%-6d f=%-6d bbox(mm)=%.1f x %.1f x %.1f -> %s"
          % (name, len(mesh.vertices), len(mesh.polygons), dims[0], dims[1], dims[2], out))

    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(mesh)
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rebuild_scene()
    ok, missing = 0, []
    for name in PRINT_PARTS:
        if export_part_stl(name) is None:
            missing.append(name)
        else:
            ok += 1
    print("STL EXPORT DONE: %d/%d" % (ok, len(PRINT_PARTS)))
    if missing:
        print("MISSING PARTS:", missing)
        sys.exit(1)


main()
