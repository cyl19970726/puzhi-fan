"""
export_form_b.py — 把形态 B 的 Blender 场景导出为 dashboard 用的 GLB（保留部件名，供 Three.js 热点标注）
用法: blender --background --factory-startup --python export_form_b.py
      CMF=cream(默认)|green  选择导出来源 blend
输入: form_b_{CMF}.blend（build_form_b.py FAST=0 产出）
输出: form_b.glb（主 CMF=cream）或 form_b_green.glb；并解析 GLB JSON 块核验节点名
"""
import bpy
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CMF = os.environ.get("CMF", "cream")
BLEND = os.path.join(BASE, f"form_b_{CMF}.blend")
OUT = os.path.join(BASE, "form_b.glb" if CMF == "cream" else f"form_b_{CMF}.glb")

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

# ---- 解析 GLB JSON 块，核验节点名（不依赖 Blender 内存态） ----
import json
import struct

EXPECTED = {"Body", "FrontMesh", "MeshCavity", "Display", "DisplayGlass", "DisplayBezel",
            "Knob", "CoolKey", "HotVent", "HotVentCavity", "IntakeGrille", "IntakeCavity",
            "Feet", "TypeC", "Band", "MintLine"}

with open(OUT, "rb") as f:
    magic, version, total = struct.unpack("<III", f.read(12))
    assert magic == 0x46546C67, "not a GLB file"
    clen, ctype = struct.unpack("<II", f.read(8))
    assert ctype == 0x4E4F534A, "first chunk is not JSON"
    gltf = json.loads(f.read(clen))

node_names = {n.get("name", "") for n in gltf.get("nodes", [])}
missing = EXPECTED - node_names
print("GLB NODES (%d):" % len(node_names))
for n in sorted(node_names):
    print("  *", n)
if missing:
    print("VERIFY FAIL — missing nodes:", sorted(missing))
    raise SystemExit(1)
print("VERIFY PASS — all %d expected part names present in GLB JSON" % len(EXPECTED))
