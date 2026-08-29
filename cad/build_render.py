"""
LiteCool S1 v3.0 — 桌面制冷风扇 程序化概念模型 + 渲染
用法: blender --background --factory-startup --python build_render.py
坐标约定:
  X = 高度（竖直）；塔身 200mm + 底座 30mm = 总高 230mm
  Y = 前后（前 = +Y：出风网罩 + 数显；后 = -Y：进风格栅 + TEC 热风排出口）
  Z = 左右（右 = +Z：旋钮）
轮廓 = 超椭圆塔（candidate B 方圆塔）；专利核查后只需替换 SECTION 参数/函数。
输出: renders_raw/{front,three_quarter,side,back,top}.png（透明底）
后处理: python3 composite_renders.py；验收: python3 verify_renders.py
"""
import bpy
import math
import mathutils
import os
from mathutils import Vector

# ================= 参数（design-spec v3.0 §5/§6） =================
TOWER_H, TOWER_W = 0.200, 0.090          # 塔身 200 高 × 90 直径（超椭圆）
SECTION_N = 3.0                           # 超椭圆指数（专利核查后可换）
CAP_R = 0.015                             # 塔顶/塔底圆角
BASE_W, BASE_H = 0.110, 0.030             # 底座 Ø110 × 30
TOTAL_H = TOWER_H + BASE_H                # 230mm
GRILLE = dict(x=0.048, r=0.034)           # 前出风网罩：中心高度 + 半径(Ø68)
DISP = dict(size=(0.030, 0.0025, 0.014), x=-0.012)   # 数显窗 30×14
INTAKE = dict(x0=-0.035, x1=0.020, z0=-0.028, z1=0.028, bars=7)   # 后进风格栅
HOTVENT = dict(x0=0.055, x1=0.085, z0=-0.015, z1=0.015, bars=4)   # TEC 热风排口（后上部）
KNOB = dict(x=0.030, r=0.010)            # 右侧旋钮（塔身下部）
TYPEC = dict(x=-0.108)                    # 底座后 Type-C

C_IVORY = (0.949, 0.937, 0.914, 1.0)     # #F2EFE9
C_MINT  = (0.35, 0.72, 0.52, 1.0)        # 腰线薄荷绿（高饱和扛直射光）
C_GRAY  = (0.06, 0.063, 0.068, 1.0)      # 深灰（网罩/格栅/底座胶圈）
C_ALUM  = (0.82, 0.84, 0.87, 1.0)        # 拉丝铝
C_CYAN  = (0.15, 0.70, 1.00, 1.0)        # 数显辉光
C_BLACK = (0.05, 0.05, 0.06, 1.0)

# ================= 工具 =================
def new_mat(name, base, metallic=0.0, roughness=0.5, emission=None, emission_strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = base
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    return m

def box(name, size, loc, mat=None, bevel=0.0, bevel_seg=5):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat is not None:
        obj.data.materials.append(mat)
    if bevel > 0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = bevel_seg
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(40)
    return obj

def cyl(name, radius, depth, loc, rot=(0, 0, 0), mat=None, verts=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    if mat is not None:
        obj.data.materials.append(mat)
    return obj

def boolean_cut(target, cutter):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("bool_" + cutter.name, "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def superellipse_pts(a, b, n, N=72):
    pts = []
    for i in range(N):
        ang = 2 * math.pi * i / N
        c, s = math.cos(ang), math.sin(ang)
        pts.append((math.copysign(abs(c) ** (2.0 / n), c) * a,
                    math.copysign(abs(s) ** (2.0 / n), s) * b))
    return pts

def prism(name, a, b, length, loc, mat=None, bevel_w=0.0):
    """超椭圆截面棱柱（长轴 X，截面 YZ）；可选端面圆角并立即烘焙"""
    import bmesh
    pts = superellipse_pts(a, b, SECTION_N)
    N = len(pts)
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    x0, x1 = -length / 2, length / 2
    ring0 = [bm.verts.new((x0, py, pz)) for (py, pz) in pts]
    ring1 = [bm.verts.new((x1, py, pz)) for (py, pz) in pts]
    cap0 = bm.verts.new((x0, 0, 0))
    cap1 = bm.verts.new((x1, 0, 0))
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
        bm.faces.new((cap0, ring0[j], ring0[i]))
        bm.faces.new((cap1, ring1[i], ring1[j]))
    bm.to_mesh(mesh)
    bm.free()
    obj.location = loc
    if mat is not None:
        obj.data.materials.append(mat)
    if bevel_w > 0:
        mod = obj.modifiers.new("bevel_ends", "BEVEL")
        mod.width = bevel_w
        mod.segments = 8
        mod.limit_method = "ANGLE"
        mod.angle_limit = math.radians(30)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="bevel_ends")
    return obj

# ================= 构建 =================
def build(mats):
    tower_lo = 0.0                    # 塔身下缘
    tower_hi = TOWER_H                # 塔身上缘（+X 顶）
    # 塔身（重心居中于 (TOWER_H/2, 0, 0)）
    body = prism("Tower", TOWER_W / 2, TOWER_W / 2, TOWER_H, (TOWER_H / 2, 0, 0),
                 mat=mats["BodyIvory"], bevel_w=CAP_R)
    # 前出风网罩：圆形凹槽 + 径向格栅 + 中心毂 + 深色背板（真实桌面扇的深色风道内腔）
    grille_c = cyl("cutter_grille", GRILLE["r"], 0.030, (GRILLE["x"], TOWER_W / 2 + 0.002, 0),
                   rot=(math.radians(90), 0, 0))
    boolean_cut(body, grille_c)
    back_disc = cyl("GrilleBack", 0.020, 0.003, (GRILLE["x"], TOWER_W / 2 - 0.006, 0),
                    rot=(math.radians(90), 0, 0), mat=mats["GrilleDark"])
    # 轴流扇叶（网罩后可见，3 片）
    for i in range(3):
        ang = i * (360.0 / 3)
        blade = box(f"FanBlade_{i}", (0.0025, 0.004, 0.030), (GRILLE["x"], TOWER_W / 2 - 0.013, 0),
                    mat=mats["Grid"])
        blade.rotation_euler = (math.radians(ang), 0, 0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    fancap = cyl("FanHub", 0.008, 0.006, (GRILLE["x"], TOWER_W / 2 - 0.012, 0),
                 rot=(math.radians(90), 0, 0), mat=mats["Grid"])
    for i in range(8):
        ang = i * (360.0 / 8)
        bar = box(f"GrilleBar_{i}", (0.060, 0.002, 0.003), (GRILLE["x"], TOWER_W / 2 - 0.004, 0),
                  mat=mats["GrilleDark"])
        bar.rotation_euler = (math.radians(ang), 0, 0)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    hub = cyl("GrilleHub", 0.012, 0.006, (GRILLE["x"], TOWER_W / 2 + 0.001, 0),
              rot=(math.radians(90), 0, 0), mat=mats["GrilleDark"])
    rim_torus = bpy.ops.mesh.primitive_torus_add(major_radius=GRILLE["r"] + 0.0005, minor_radius=0.0015,
                                                 major_segments=48, minor_segments=8,
                                                 location=(GRILLE["x"], TOWER_W / 2 + 0.002, 0))
    rim = bpy.context.active_object
    rim.name = "GrilleRing"
    rim.rotation_euler = (math.radians(90), 0, 0)   # 轴沿 Y（真正的环，不是实心圆盘）
    rim.data.materials.append(mats["FrameDark"])
    # 数显窗 + 字形 "22.0"（出风温度，法线 +Y）
    disp = box("Display", DISP["size"], (DISP["x"], TOWER_W / 2 + 0.0012, 0),
               mat=mats["DisplayGlow"], bevel=0.0006, bevel_seg=4)
    frame = box("DisplayFrame", (0.034, 0.0018, 0.018), (DISP["x"], TOWER_W / 2 + 0.0006, 0),
                mat=mats["FrameDark"], bevel=0.0008, bevel_seg=4)
    font = bpy.data.curves.new("DisplayText", type="FONT")
    font.body = "22.0"
    font.size = 0.0105
    font.extrude = 0.0012
    font.align_x = "CENTER"
    font.align_y = "CENTER"
    txt = bpy.data.objects.new("DisplayText", font)
    txt.location = (DISP["x"], TOWER_W / 2 + 0.0022, 0)
    txt.rotation_euler = (-math.pi / 2, 0, 0)
    bpy.context.collection.objects.link(txt)
    txt.data.materials.append(mats["DigitWhite"])
    # 后进风格栅（-Y，下部）
    recess = box("IntakeRecess", (INTAKE["x1"] - INTAKE["x0"], 0.008, INTAKE["z1"] - INTAKE["z0"]),
                 ((INTAKE["x0"] + INTAKE["x1"]) / 2, -TOWER_W / 2 + 0.002, 0))
    boolean_cut(body, recess)
    for i in range(INTAKE["bars"]):
        xx = INTAKE["x0"] + (i + 0.5) * (INTAKE["x1"] - INTAKE["x0"]) / INTAKE["bars"]
        bar = box(f"IntakeBar_{i}", (0.005, 0.003, INTAKE["z1"] - INTAKE["z0"] + 0.002),
                  (xx, -TOWER_W / 2 - 0.0012, 0), mat=mats["Grid"])
    # TEC 热风排口（后上部，斜向格栅）
    for i in range(HOTVENT["bars"]):
        xx = HOTVENT["x0"] + (i + 0.5) * (HOTVENT["x1"] - HOTVENT["x0"]) / HOTVENT["bars"]
        bar = box(f"HotVentBar_{i}", (0.006, 0.003, HOTVENT["z1"] - HOTVENT["z0"] + 0.002),
                  (xx, -TOWER_W / 2 - 0.0012, 0), mat=mats["Grid"])
    # 右侧旋钮（+Z，下部）
    knob = cyl("Knob", KNOB["r"], 0.012, (KNOB["x"], 0, TOWER_W / 2 + 0.003),
               rot=(math.radians(90), 0, 0), mat=mats["FrameDark"])
    knobtip = cyl("KnobGrip", KNOB["r"] * 0.85, 0.003, (KNOB["x"], 0, TOWER_W / 2 + 0.008),
                  rot=(math.radians(90), 0, 0), mat=mats["Aluminum"])
    # 品牌腰线（塔身下缘，超椭圆带）
    band = prism("Band", (TOWER_W / 2) * 1.02, (TOWER_W / 2) * 1.02, 0.008,
                 (0.010, 0, 0), mat=mats["BandIvory"])
    # 底座（Ø110 × 30 + 防滑胶圈）
    base = prism("Base", BASE_W / 2, BASE_W / 2, BASE_H, (-BASE_H / 2, 0, 0),
                 mat=mats["BodyIvory"], bevel_w=0.004)
    ring = prism("BaseRing", (BASE_W / 2) * 1.005, (BASE_W / 2) * 1.005, 0.006,
                 (-BASE_H + 0.003, 0, 0), mat=mats["FrameDark"])
    # 底座后 Type-C 凹口
    typec = box("TypeC", (0.004, 0.008, 0.006), (TYPEC["x"], -BASE_W / 2 - 0.001, 0), mat=mats["VoidDark"])
    return body

# ================= 场景 =================
def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {
        "BodyIvory": new_mat("BodyIvory", C_IVORY, 0.0, 0.42),
        "Aluminum":  new_mat("Aluminum",  C_ALUM,  1.0, 0.22),
        "Grid":      new_mat("Grid",      C_GRAY,  0.2, 0.55),
        "FrameDark": new_mat("FrameDark", C_GRAY,  0.3, 0.45),
        "VoidDark":  new_mat("VoidDark",  C_BLACK, 0.0, 0.8),
        "GrilleDark": new_mat("GrilleDark", (0.005, 0.005, 0.008, 1.0), 0.0, 0.9),
        "BandIvory": new_mat("BandIvory", C_MINT,  0.0, 0.42,
                             emission=(0.35, 0.72, 0.52, 1.0), emission_strength=0.1),
        "DisplayGlow": new_mat("DisplayGlow", (0.02, 0.05, 0.10, 1.0), 0.6, 0.3,
                               emission=C_CYAN, emission_strength=2.2),
        "DigitWhite": new_mat("DigitWhite", (1.0, 1.0, 1.0, 1.0), 0.0, 0.2,
                              emission=(0.9, 0.97, 1.0, 1.0), emission_strength=2.0),
    }
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1920
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.4
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 0.6
    try:
        scene.eevee.use_soft_shadows = True
    except Exception:
        pass
    # 三点布光：面积光默认 -Z 发射，逐一瞄准原点；位置避开所有相机视锥
    def add_area(name, loc, energy, size=0.4):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.active_object
        lamp.name = name
        lamp.data.energy = energy
        lamp.data.size = size
        fwd = (Vector((0.0, 0.0, 0.0)) - Vector(loc)).normalized()
        z = -fwd
        up = Vector((0.0, 0.0, 1.0))
        x = up.cross(z)
        if x.length < 1e-6:
            up = Vector((0.0, 1.0, 0.0))
            x = up.cross(z)
        x.normalize()
        y = z.cross(x)
        y.normalize()
        lamp.rotation_euler = mathutils.Matrix((x, y, z)).transposed().to_euler()
        return lamp
    add_area("KeyLight", (0.30, 0.45, 0.30), 3.0)
    add_area("FillLight", (-0.55, 0.10, -0.55), 1.2)
    add_area("RimLight", (0.30, 0.60, -0.20), 1.5)
    return mats, scene

def aim_camera(cam, target, loc):
    fwd = (target - loc).normalized()
    z = -fwd
    up = Vector((1.0, 0.0, 0.0))
    x = up.cross(z)
    if x.length < 1e-6:
        up = Vector((0.0, 0.0, 1.0))
        x = up.cross(z)
    x.normalize()
    y = z.cross(x)
    y.normalize()
    cam.rotation_euler = mathutils.Matrix((x, y, z)).transposed().to_euler()

TARGET = Vector((0.05, 0.0, 0.0))   # 塔身中心略偏下（产品总高 230，相机需 ≥0.75m 才能完整入画）
VIEWS = {
    "front":         Vector((0.05, 0.75, 0.00)),
    "three_quarter": Vector((0.45, 0.45, 0.50)),
    "side":          Vector((0.05, 0.00, 0.75)),
    "back":          Vector((0.05, -0.75, 0.00)),
    "top":           Vector((0.40, 0.00, 0.00)),
}

def render_set(out_dir):
    mats, scene = setup_scene()
    build(mats)
    bpy.context.view_layer.update()
    for name, loc in VIEWS.items():
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.name = f"cam_{name}"
        cam.data.lens = 50
        aim_camera(cam, TARGET, loc)
        scene.camera = cam
        scene.render.filepath = f"{out_dir}/{name}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED:", f"{out_dir}/{name}.png")
        bpy.data.objects.remove(cam, do_unlink=True)
    blend_path = "/Users/hhh0x/chuifnegji/puzhi-fan/cad/litecool_s1_desktop.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("BLEND SAVED:", blend_path)

BASE_DIR = "/Users/hhh0x/chuifnegji/puzhi-fan/cad"
render_set(os.path.join(BASE_DIR, "renders_raw"))
print("ALL DONE")
