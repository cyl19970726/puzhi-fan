"""
export_form_d.py — 把形态 D 的 Blender 场景导出为 dashboard 用的 GLB（保留部件名，供 Three.js 热点标注）
用法: blender --background --factory-startup --python export_form_d.py
输入: form_d.blend（build_form_d.py FAST=0 产出）
输出: form_d.glb；导出后解析 GLB JSON 块核验节点名
"""
import bpy
import json
import os
import struct

BASE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(BASE, "form_d.blend")
OUT = os.path.join(BASE, "form_d.glb")

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

# ---- 解析 GLB JSON 块，核验节点名与场景 mesh 一致 ----
with open(OUT, "rb") as f:
    magic, version, _length = struct.unpack("<4sII", f.read(12))
    assert magic == b"glTF", "not a GLB"
    clen, ctype = struct.unpack("<I4s", f.read(8))
    assert ctype == b"JSON", "first chunk not JSON"
    gltf = json.loads(f.read(clen))
node_names = sorted(nd.get("name", "") for nd in gltf.get("nodes", []))
print("GLB NODES (%d):" % len(node_names))
for n in node_names:
    print("  -", n)
missing = [n for n in names if n not in node_names]
assert not missing, "MISSING IN GLB: %s" % missing
print("NODE NAME CHECK: OK (%d mesh objects all present in GLB nodes)" % len(names))
