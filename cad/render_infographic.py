"""
LiteCool S1 — 信息图专用高清爆炸渲染 + 引线锚点投影（A/B/D 三形态）
用法: blender --background --python cad/render_infographic.py -- --form {a|b|d}
流程:
  1. exec 对应 build_core_eng{,_b,_d}.py（重建工程装配体场景，含材质/灯光；FAST 快渲两张旧图属附带产物）
  2. 爆炸向量 ×SPREAD 拉开间距（给引线留位），3/4 俯视相机自动取景
  3. 渲 cad/infographic/exploded_raw{,_b,_d}.png（RGBA 透明底）
  4. world_to_camera_view 投影关键零件质心 → cad/infographic/anchors{,_b,_d}.json（像素坐标，供 PIL 画引线）
标注零件清单（KEY_PARTS）取自 infographic/labels.json —— 与 PIL 合成、工作台查看器共用同一事实源。
"""
import bpy
import os
import sys
import json
import math
import mathutils
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "infographic")
os.makedirs(OUT_DIR, exist_ok=True)

# ---- 形态参数：--form b（默认 a）----
FORM = "a"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--form" in argv:
    FORM = argv[argv.index("--form") + 1].lower()
FORM = os.environ.get("FORM", FORM)

FORMS = {
    #            build 脚本               默认渲染尺寸     输出后缀
    "a": {"build": "build_core_eng.py",   "size": (1600, 1200), "suffix": ""},
    "b": {"build": "build_core_eng_b.py", "size": (1600, 1200), "suffix": "_b"},
    "d": {"build": "build_core_eng_d.py", "size": (1200, 1600), "suffix": "_d"},
}
cfg = FORMS[FORM]
SUF = cfg["suffix"]

SPREAD = float(os.environ.get("SPREAD", "1.25"))    # 爆炸间距放大系数
IMG_W = int(os.environ.get("IMG_W", str(cfg["size"][0])))
IMG_H = int(os.environ.get("IMG_H", str(cfg["size"][1])))

# 信息图要标注的关键零件（label/价格由 PIL 合成阶段从 labels.json 取，这里只要锚点）
with open(os.path.join(OUT_DIR, "labels.json"), encoding="utf-8") as fp:
    KEY_PARTS = [row[0] for row in json.load(fp)[FORM]]

# ---- 1. 重建场景（build_core_eng*.main() 会跑一遍：建模+导GLB+两张 FAST 快渲） ----
ns = {"__file__": os.path.join(BASE_DIR, cfg["build"])}
exec(compile(open(ns["__file__"], encoding="utf-8").read(), ns["__file__"], "exec"), ns)
meta = dict(ns["SHELL_META"]); meta.update(ns["CORE_META"])
explode_vec = ns["explode_vec"]

scene = bpy.context.scene
# 信息图要更挺的颜色：Standard 视图变换（Filmic 会洗白）
try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -0.4
except Exception:
    pass

# ---- 2. 爆炸拉开 ----
part_objs = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.name in meta:
        o.location += explode_vec(o.name, o) * SPREAD
        part_objs.append(o)

# 隐藏气流箭头（爆炸图不需要）
for o in bpy.data.objects:
    if o.name.startswith("Airflow_"):
        o.hide_render = True

# 爆炸态信息图：外壳恢复不透明（爆炸后遮挡少；半透+白底会整图发白）
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.materials:
        for i, mt in enumerate(o.data.materials):
            if mt and mt.name.endswith("_Ghost"):
                orig = bpy.data.materials.get(mt.name[:-6])
                if orig:
                    o.data.materials[i] = orig

# ---- 3. 相机自动取景（3/4 俯视，同 build_core_eng 爆炸机位方向） ----
scene.render.resolution_x = IMG_W
scene.render.resolution_y = IMG_H
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
try:
    scene.eevee.taa_render_samples = 64
except Exception:
    pass

# 爆炸后整体包围盒
bmin = Vector((1e9, 1e9, 1e9)); bmax = Vector((-1e9, -1e9, -1e9))
for o in part_objs:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        bmin = Vector(map(min, bmin, w)); bmax = Vector(map(max, bmax, w))
center = (bmin + bmax) / 2

direction = (Vector((0.60, 0.68, 0.76)) - Vector((0.10, 0.0, 0.0))).normalized()
bpy.ops.object.camera_add(location=center + direction * 2.0)
cam = bpy.context.active_object
cam.data.lens = 55
fwd = (center - cam.location).normalized()
z = -fwd
up = Vector((1.0, 0.0, 0.0))
x = up.cross(z)
if x.length < 1e-6:
    up = Vector((0.0, 0.0, 1.0)); x = up.cross(z)
x.normalize(); y = z.cross(x); y.normalize()
cam.rotation_euler = mathutils.Matrix((x, y, z)).transposed().to_euler()
scene.camera = cam

# 取景：从近到远，直到包围盒 8 角全部落在 [0.05, 0.95] 视口内
corners = [Vector((a, b, c)) for a in (bmin.x, bmax.x)
           for b in (bmin.y, bmax.y) for c in (bmin.z, bmax.z)]
def fits(dist):
    cam.location = center + direction * dist
    bpy.context.view_layer.update()
    return all(0.05 < world_to_camera_view(scene, cam, c).x < 0.95 and
               0.05 < world_to_camera_view(scene, cam, c).y < 0.95 for c in corners)
dist = 0.25
while dist < 3.0 and not fits(dist):
    dist += 0.05
cam.location = center + direction * (dist + 0.04)
bpy.context.view_layer.update()
print("CAM DIST:", dist + 0.04)

# ---- 4. 渲染 ----
scene.render.filepath = os.path.join(OUT_DIR, "exploded_raw%s.png" % SUF)
bpy.ops.render.render(write_still=True)
print("RENDERED:", scene.render.filepath)

# ---- 5. 投影关键零件质心 → 像素坐标 JSON ----
anchors = {}
for name in KEY_PARTS:
    o = bpy.data.objects.get(name)
    if o is None:
        print("MISSING PART:", name); continue
    # 用包围盒中心（比 origin 更贴近视觉中心）
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    ctr = sum(cs, Vector()) / 8
    co = world_to_camera_view(scene, cam, ctr)
    anchors[name] = {
        "px": round(co.x * IMG_W, 1),
        "py": round((1.0 - co.y) * IMG_H, 1),
        "module": meta[name][0],
        "label": meta[name][1],
    }
anchors_path = os.path.join(OUT_DIR, "anchors%s.json" % SUF)
with open(anchors_path, "w", encoding="utf-8") as f:
    json.dump({"img_w": IMG_W, "img_h": IMG_H, "spread": SPREAD,
               "paste": None, "anchors": anchors}, f, ensure_ascii=False, indent=1)
print("ANCHORS:", len(anchors), "->", anchors_path)
print("INFOGRAPHIC RENDER DONE (form %s)" % FORM)
