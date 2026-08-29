"""
export_form_a.py — 把形态 A 的 Blender 场景导出为 dashboard 用的 GLB（保留部件名，供 Three.js 热点标注）
用法: blender --background --factory-startup --python export_form_a.py
输入: form_a.blend（build_form_a.py FAST=0 产出）
输出: form_a.glb
"""
import bpy
import os

BASE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(BASE, "form_a.blend")
OUT = os.path.join(BASE, "form_a.glb")

bpy.ops.wm.open_mainfile(filepath=BLEND)

# 只导出实体网格；隐藏相机/灯等
for o in bpy.data.objects:
    if o.type == "MESH":
        o.hide_render = False
        o.hide_set(False)
    else:
        o.hide_set(True)
        o.hide_render = True

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_selection=False,
                          export_yup=True, export_apply=False)
print("GLB EXPORTED:", OUT)

names = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
print("PARTS (%d):" % len(names))
for n in names:
    print("  -", n)
