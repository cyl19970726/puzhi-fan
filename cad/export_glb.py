"""
export_glb.py — 把 Blender 场景导出为 dashboard 用的 GLB（保留部件名，供 Three.js 热点标注）
用法: blender --background --factory-startup --python export_glb.py
输入: litecool_s1_concept.blend（或任意 build_render.py 产出的 blend）
输出: ../dashboard/model.glb
"""
import bpy
import os

BLEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "litecool_s1_desktop.blend")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dashboard", "model.glb")

bpy.ops.wm.open_mainfile(filepath=BLEND)

# 只导出实体网格；隐藏相机/灯等
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = False
        o.hide_set(False)
    else:
        o.hide_set(True)
        o.hide_render = True

# 保证所有网格导出（不要 selection）
bpy.ops.object.select_all(action="DESELECT")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=False,
                          export_yup=True, export_apply=False)
print("GLB EXPORTED:", OUT)

# 列出部件名（dashboard 标注用）
names = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
print("PARTS (%d):" % len(names))
for n in names:
    print("  -", n)
