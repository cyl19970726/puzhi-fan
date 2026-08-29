"""LiteCool S1 — AI 外观皮肤:GLB 导入 → 按 spec 缩放 → 三点 studio 光 turntable + hero 渲染。

用法:
  blender --background --factory-startup --python cad/ai_shell_render.py -- \
      <in.glb> <out_dir> <target_longest_mm> [--hero-az 30]

处理:
  1. 导入 GLB,合并 bbox,均匀缩放使最长边 = target_longest_mm(记录缩放比 → scale_report.json)
  2. 底面落到 z=0、水平居中;Apply Transform;导出缩放后 GLB(<out_dir>/shell_scaled.glb)
  3. 三点光(key/fill/rim)+ 地面 + 浅灰世界;turntable 4 视角(az 30/120/210/300, el 15°)+ hero(el 25°)
  4. 渲染到 <out_dir>/renders/{turntable_0..3,hero}.png(1024px,Eevee)

尺寸校验:scale_report.json 含 raw_mm / final_mm / scale_factor / tri_count。
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
IN_GLB, OUT_DIR, TARGET_MM = argv[0], argv[1], float(argv[2])
HERO_AZ = 30.0
if "--hero-az" in argv:
    HERO_AZ = float(argv[argv.index("--hero-az") + 1])
TARGET_M = TARGET_MM / 1000.0

RENDERS = os.path.join(OUT_DIR, "renders")
os.makedirs(RENDERS, exist_ok=True)

# ---------- 1. 导入 + 缩放 ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=IN_GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
if not meshes:
    sys.exit("GLB 内无 mesh")

bpy.context.view_layer.update()


def world_bbox(objs):
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


lo, hi = world_bbox(meshes)
raw_dim = hi - lo
raw_longest = max(raw_dim.x, raw_dim.y, raw_dim.z)
s = TARGET_M / raw_longest

for o in meshes:
    o.scale = (o.scale.x * s, o.scale.y * s, o.scale.z * s)
bpy.context.view_layer.update()
lo, hi = world_bbox(meshes)
center = (lo + hi) / 2
for o in meshes:
    o.location = (o.location.x - center.x, o.location.y - center.y, o.location.z - lo.z)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

lo, hi = world_bbox(meshes)
final_dim = hi - lo
tri_count = 0
for o in meshes:
    m = o.data
    m.calc_loop_triangles()
    tri_count += len(m.loop_triangles)

# 主轴检查:若"躺倒"(Z 明显不是高)只记录,不擅自旋转——单图重建产物朝向以渲染图为准人工判
report = {
    "input_glb": IN_GLB,
    "target_longest_mm": TARGET_MM,
    "raw_dim_mm": [round(raw_dim.x * 1000, 2), round(raw_dim.y * 1000, 2), round(raw_dim.z * 1000, 2)],
    "scale_factor": round(s, 6),
    "final_dim_mm": [round(final_dim.x * 1000, 2), round(final_dim.y * 1000, 2), round(final_dim.z * 1000, 2)],
    "tri_count": tri_count,
    "mesh_objects": len(meshes),
}
with open(os.path.join(OUT_DIR, "scale_report.json"), "w") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

scaled_glb = os.path.join(OUT_DIR, "shell_scaled.glb")
bpy.ops.export_scene.gltf(filepath=scaled_glb, export_format="GLB")

# ---------- 2. 场景:地面 + 三点光 + 相机 ----------
scene = bpy.context.scene

# 地面(大圆盘,微粗糙浅灰)
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
gm = bpy.data.materials.new("Ground")
gm.use_nodes = True
gbsdf = gm.node_tree.nodes["Principled BSDF"]
gbsdf.inputs["Base Color"].default_value = (0.82, 0.81, 0.79, 1.0)
gbsdf.inputs["Roughness"].default_value = 0.9
ground.data.materials.append(gm)

size_xy = max(final_dim.x, final_dim.y)
h = final_dim.z
cam_target = Vector((0, 0, h * 0.5))


def area_light(name, loc, energy, size, color):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.shape = "DISK"
    ld.size = size
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    scene.collection.objects.link(ob)
    # 指向模型中心
    d = cam_target - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


R = size_xy * 2.2 + 0.5
area_light("Key", (R * 0.8, -R * 0.9, h * 2.2), 400, 1.2, (1.0, 0.97, 0.93))
area_light("Fill", (-R * 1.0, -R * 0.4, h * 1.2), 150, 1.5, (0.93, 0.96, 1.0))
area_light("Rim", (R * 0.2, R * 1.1, h * 2.0), 600, 1.0, (1.0, 1.0, 1.0))

world = bpy.data.worlds.new("W")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1.0)
bg.inputs[1].default_value = 0.35
scene.world = world
scene.view_settings.exposure = -1.0

# 相机
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 55
cam = bpy.data.objects.new("Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def place_cam(az_deg, el_deg, margin=1.45):
    az, el = math.radians(az_deg), math.radians(el_deg)
    half = max(size_xy / 2, h / 2) * margin
    dist = half / math.tan(cam_data.angle / 2) / max(0.4, math.cos(el))  # cam.angle 已是弧度
    dist = max(dist, half * 2.2)
    loc = Vector((dist * math.cos(el) * math.sin(az),
                  -dist * math.cos(el) * math.cos(az),
                  cam_target.z + dist * math.sin(el)))
    cam.location = loc
    d = cam_target - loc
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# ---------- 3. 渲染设置 ----------
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except Exception:
        continue
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
scene.render.image_settings.file_format = "PNG"
try:
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
except Exception:
    pass
if hasattr(scene, "eevee"):
    pass
scene.render.image_settings.color_depth = "8"

views = [("turntable_0", 30, 15), ("turntable_1", 120, 15),
         ("turntable_2", 210, 15), ("turntable_3", 300, 15),
         ("hero", HERO_AZ, 25)]
for name, az, el in views:
    place_cam(az, el)
    scene.render.filepath = os.path.join(RENDERS, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("rendered:", scene.render.filepath)

print("DONE. scale_report:", json.dumps(report))
