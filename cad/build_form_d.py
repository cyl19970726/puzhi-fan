"""
LiteCool S1 — 形态 D「塔·认真版」程序化概念模型 + 渲染
用法: blender --background --factory-startup --python build_form_d.py
      FAST=1(默认) 480x640 低采样；FAST=0 768x1024 全五视图 + 存 form_d.blend
坐标约定(与 build_render.py 一致):
  X = 高度（竖直）；底座 26mm + 塔身 204mm = 总高 230mm
  Y = 前后（前 = +Y：百叶网罩 + 顶部斜面数显；后 = -Y：进风格栅 + TEC 热排）
  Z = 左右
形态依据: design/form-directions.md §5 方向 D；专利规避 research/patent_avoidance.md §3 方向 D 节
  · squircle 超椭圆截面 n=4（v3.0 n=3 基础上强化，非正圆）
  · 网罩 = 横向百叶式开孔（非放射状辐条+同心圆）
  · 出风温度大数显放顶部斜面（非正面中上部长条竖显）
  · 塔身-底座顺滑一体 loft（非球头+圆盘两段式）
  · TEC 热风独立后排格栅 = 竖向 pill 凹腔立柱（造型化设计元素）
输出: renders_form_d/{front,three_quarter,side,back,top}.png（透明底 RGBA）
"""
import bpy
import math
import mathutils
import os
from mathutils import Vector

# ================= 参数（form-directions §5：Ø90×230，底座 Ø110） =================
SECTION_N = 4.0                 # 超椭圆指数（v3.0=3.0，强化 squircle）
R_TOWER = 0.045                 # 塔身截面半径 Ø90
R_BASE = 0.055                  # 底座截面半径 Ø110
BASE_H = 0.026                  # 底座高（配重盘，厚度读出"稳"）
FLARE_L = 0.045                 # 塔身-底座顺滑过渡段长（ trumpet 内收）
TOWER_TOP = 0.204               # 塔身上缘（总高 0.026+0.204=0.230）
BAND = dict(x=0.052, h=0.006, r=0.047)           # 薄荷腰线（flare 结束处）
GRILLE = dict(x0=0.100, x1=0.168, z=0.028, bars=10, tilt=20.0)   # 前横向百叶网罩
INTAKE = dict(x0=0.062, x1=0.098, z=0.024, bars=6)               # 后进风（横条）
HOTVENT = dict(x0=0.110, x1=0.168, z=0.015, bars=5)              # TEC 热排（后竖向 pill 立柱）
SLANT_ANG = 35.0                # 顶部数显斜面倾角（斜面朝前上，坐姿俯视可读）
SLANT_P = (0.194, 0.028, 0.0)   # 斜面平面上一点
KNOB = dict(r=0.013, h=0.010, y=-0.010, z=0.000)                 # 顶部后区单旋钮
COOLKEY = dict(r=0.007, h=0.006, y=-0.010, z=0.026)              # 制冷键

C_IVORY = (0.949, 0.937, 0.914, 1.0)     # #F2EFE9 雾白
C_MINT  = (0.45, 0.78, 0.62, 1.0)        # 薄荷绿腰线（提饱和抗直射光，同 A/B 标定）
C_GRAY  = (0.06, 0.063, 0.068, 1.0)      # 深灰格栅/胶圈
C_ALUM  = (0.82, 0.84, 0.87, 1.0)        # 拉丝铝
C_CYAN  = (0.15, 0.70, 1.00, 1.0)        # 数显青色辉光
C_BLACK = (0.05, 0.05, 0.06, 1.0)

FAST = os.environ.get("FAST", "1") == "1"

# ================= 工具（抄自 build_render.py/build_form_a.py） =================
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

def join_parts(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def superellipse_pts(a, b, n, N=96):
    pts = []
    for i in range(N):
        ang = 2 * math.pi * i / N
        c, s = math.cos(ang), math.sin(ang)
        pts.append((math.copysign(abs(c) ** (2.0 / n), c) * a,
                    math.copysign(abs(s) ** (2.0 / n), s) * b))
    return pts

def prism(name, a, b, length, loc, mat=None, bevel_w=0.0, n=SECTION_N):
    """超椭圆截面棱柱（长轴 X，截面 YZ）；可选端面圆角并立即烘焙"""
    import bmesh
    pts = superellipse_pts(a, b, n)
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

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def loft(name, rings, mat, n=SECTION_N, N=96):
    """变截面超椭圆放样；rings = [(x, a, b), ...] 自下而上，两端封口，侧面平滑着色"""
    import bmesh
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    all_rings = []
    for (x, a, b) in rings:
        pts = superellipse_pts(a, b, n, N)
        all_rings.append([bm.verts.new((x, py, pz)) for (py, pz) in pts])
    for r in range(len(all_rings) - 1):
        r0, r1 = all_rings[r], all_rings[r + 1]
        for i in range(N):
            j = (i + 1) % N
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    c0 = bm.verts.new((rings[0][0], 0, 0))
    c1 = bm.verts.new((rings[-1][0], 0, 0))
    for i in range(N):
        j = (i + 1) % N
        bm.faces.new((c0, all_rings[0][j], all_rings[0][i]))
        bm.faces.new((c1, all_rings[-1][i], all_rings[-1][j]))
    bm.to_mesh(mesh)
    bm.free()
    if mat is not None:
        mesh.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = True
    return obj

# 7 段数码管字形（段: top/mid/bot/ul/ur/ll/lr）
SEG_MAP = {
    "0": "top ul ur ll lr bot", "1": "ur lr", "2": "top ur mid ll bot",
    "3": "top ur mid lr bot", "4": "ul ur mid lr", "5": "top ul mid lr bot",
    "6": "top ul mid ll lr bot", "7": "top ur lr", "8": "top mid bot ul ur ll lr",
    "9": "top ul ur mid lr bot",
}

def build_display_text(text, mat):
    """7 段数码管风格字符，建于原点、法线 +Y、字符上方 +X，返回合并单 mesh（调用方再旋转就位）"""
    h, w, t, d = 0.016, 0.0085, 0.0016, 0.001
    pitch = w + 0.0045
    widths = [pitch * 0.45 if ch == "." else pitch for ch in text]
    total = sum(widths) - (pitch - w)
    objs = []
    zi = -total / 2 + w / 2
    for ch in text:
        if ch == ".":
            objs.append(box("seg", (t, d, t), (-h / 2 + t / 2, 0, zi - w / 2), mat=mat))
            zi += pitch * 0.45
            continue
        for s in SEG_MAP[ch].split():
            if s == "top":
                o = box("seg", (t, d, w), (h / 2 - t / 2, 0, zi), mat=mat)
            elif s == "mid":
                o = box("seg", (t, d, w), (0, 0, zi), mat=mat)
            elif s == "bot":
                o = box("seg", (t, d, w), (-h / 2 + t / 2, 0, zi), mat=mat)
            elif s == "ul":
                o = box("seg", (h / 2, d, t), (h / 4, 0, zi - w / 2 + t / 2), mat=mat)
            elif s == "ur":
                o = box("seg", (h / 2, d, t), (h / 4, 0, zi + w / 2 - t / 2), mat=mat)
            elif s == "ll":
                o = box("seg", (h / 2, d, t), (-h / 4, 0, zi - w / 2 + t / 2), mat=mat)
            elif s == "lr":
                o = box("seg", (h / 2, d, t), (-h / 4, 0, zi + w / 2 - t / 2), mat=mat)
            objs.append(o)
        zi += pitch
    d = join_parts("Display", objs)
    # join 后原点留在首段盒子的位置；把顶点转回世界坐标并清零原点，供调用方旋转/平移就位
    off = d.location.copy()
    for v in d.data.vertices:
        v.co += off
    d.location = (0, 0, 0)
    return d

# ================= 构建 =================
def build(mats):
    # ---- 底座（Ø110 配重盘：21mm 雾白主盘 + 6mm 整圈防滑硅胶底圈，两段式配色读出"稳"） ----
    prism("Base", R_BASE, R_BASE, BASE_H - 0.005, (-(BASE_H - 0.005) / 2, 0, 0),
          mat=mats["BodyIvory"], bevel_w=0.004)
    # 整圈防滑硅胶圈（底座下缘整圈深灰微内收台阶，侧/背视可读 = F3 的视觉证据）
    prism("SkidPad", R_BASE - 0.002, R_BASE - 0.002, 0.006, (-BASE_H + 0.003, 0, 0),
          mat=mats["FrameDark"])
    # 底座后 Type-C
    box("TypeC", (0.006, 0.003, 0.010), (-0.012, -R_BASE + 0.0005, 0),
        mat=mats["VoidDark"], bevel=0.0015, bevel_seg=3)
    # ---- 塔身（变截面 loft：底座 Ø110 顺滑内收到 Ø90，一体轮廓） ----
    rings = []
    for x in (0.0, 0.006, 0.012, 0.020, 0.030, FLARE_L):
        r = R_TOWER + (R_BASE - R_TOWER) * (1.0 - smoothstep(x / FLARE_L))
        rings.append((x, r, r))
    rings += [(0.100, R_TOWER, R_TOWER), (0.190, R_TOWER, R_TOWER),
              (0.197, 0.0438, 0.0438), (0.2005, 0.0395, 0.0395),
              (0.2030, 0.0320, 0.0320)]
    tower = loft("Tower", rings, mats["BodyIvory"])
    # ---- 顶部斜面（数显窗承载面，朝前上 35°） ----
    ang = math.radians(SLANT_ANG)
    n = Vector((math.cos(ang), math.sin(ang), 0.0))           # 斜面法线
    cutter = box("cutter_slant", (0.20, 0.20, 0.20),
                 Vector(SLANT_P) + n * 0.10)
    cutter.rotation_euler = (0, 0, ang)
    bpy.context.view_layer.objects.active = cutter
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    boolean_cut(tower, cutter)
    # 斜面切面保持平直着色（平滑着色会让切面发花）
    for p in tower.data.polygons:
        if p.normal.dot(n) > 0.9:
            p.use_smooth = False
    # ---- 出风温度大数显（顶部斜面，7 段数码管 "22.0" 青色发光） ----
    u = Vector((math.sin(ang), -math.cos(ang), 0.0))          # 斜面内"上坡"方向
    q = Vector(SLANT_P) + u * 0.004                           # 斜面中心
    glass = box("DisplayGlass", (0.0016, 0.026, 0.044), q + n * 0.0008,
                mat=mats["GlassDark"], bevel=0.0007, bevel_seg=3)
    glass.rotation_euler = (0, 0, ang)
    digits = build_display_text("22.0", mats["DigitGlow"])
    digits.rotation_euler = (0, 0, ang - math.pi / 2)         # +Y→n, +X→u
    digits.location = q + n * 0.0022
    # ---- 前网罩：横向百叶式开孔（专利规避：非放射辐条+同心圆） ----
    gr_x = (GRILLE["x0"] + GRILLE["x1"]) / 2
    gr_h = GRILLE["x1"] - GRILLE["x0"]
    rec = box("cutter_grille", (gr_h + 0.004, 0.030, GRILLE["z"] * 2 + 0.004),
              (gr_x, R_TOWER - 0.012, 0), bevel=0.010, bevel_seg=5)
    boolean_cut(tower, rec)
    box("GrilleCavity", (gr_h - 0.006, 0.003, GRILLE["z"] * 2 - 0.006),
        (gr_x, R_TOWER - 0.0235, 0), mat=mats["GrilleDark"], bevel=0.008, bevel_seg=4)
    slats = []
    pitch = gr_h / GRILLE["bars"]
    for i in range(GRILLE["bars"]):
        xx = GRILLE["x0"] + (i + 0.5) * pitch
        b = box(f"lv_{i}", (0.0035, 0.0022, GRILLE["z"] * 2 - 0.004),
                (xx, R_TOWER - 0.008, 0), mat=mats["Grid"])
        b.rotation_euler = (0, 0, math.radians(GRILLE["tilt"]))   # 前缘下压百叶角
        slats.append(b)
    join_parts("Grille", slats)
    # ---- 后进风格栅（横条，与热排竖条方向区分） ----
    in_x = (INTAKE["x0"] + INTAKE["x1"]) / 2
    in_h = INTAKE["x1"] - INTAKE["x0"]
    rec = box("cutter_intake", (in_h + 0.004, 0.030, INTAKE["z"] * 2 + 0.004),
              (in_x, -R_TOWER + 0.012, 0), bevel=0.008, bevel_seg=4)
    boolean_cut(tower, rec)
    box("IntakeCavity", (in_h - 0.006, 0.003, INTAKE["z"] * 2 - 0.006),
        (in_x, -R_TOWER + 0.0235, 0), mat=mats["GrilleDark"], bevel=0.006, bevel_seg=3)
    bars = []
    pitch = in_h / INTAKE["bars"]
    for i in range(INTAKE["bars"]):
        xx = INTAKE["x0"] + (i + 0.5) * pitch
        bars.append(box(f"in_{i}", (0.0035, 0.0022, INTAKE["z"] * 2 - 0.006),
                        (xx, -R_TOWER + 0.008, 0), mat=mats["Grid"]))
    join_parts("IntakeGrille", bars)
    # ---- TEC 热风独立后排格栅（竖向 pill 凹腔立柱 = 造型化设计元素） ----
    hv_x = (HOTVENT["x0"] + HOTVENT["x1"]) / 2
    hv_h = HOTVENT["x1"] - HOTVENT["x0"]
    rec = box("cutter_hotvent", (hv_h + 0.004, 0.030, HOTVENT["z"] * 2 + 0.004),
              (hv_x, -R_TOWER + 0.012, 0), bevel=0.013, bevel_seg=6)
    boolean_cut(tower, rec)
    box("HotVentCavity", (hv_h - 0.006, 0.003, HOTVENT["z"] * 2 - 0.006),
        (hv_x, -R_TOWER + 0.0235, 0), mat=mats["GrilleDark"], bevel=0.010, bevel_seg=5)
    fins = []
    pitch = (HOTVENT["z"] * 2 - 0.006) / HOTVENT["bars"]
    for i in range(HOTVENT["bars"]):
        zz = -HOTVENT["z"] + 0.003 + (i + 0.5) * pitch
        fins.append(box(f"hv_{i}", (hv_h - 0.010, 0.0022, 0.0035),
                        (hv_x, -R_TOWER + 0.008, zz), mat=mats["Grid"]))
    join_parts("HotVent", fins)
    # ---- 薄荷绿腰线（flare 结束处整圈，品牌基因） ----
    prism("Band", BAND["r"], BAND["r"], BAND["h"], (BAND["x"], 0, 0),
          mat=mats["BandMint"])
    # ---- 顶部后区：单旋钮 + 制冷键 ----
    knob = cyl("knob_body", KNOB["r"], KNOB["h"],
               (0.2020, KNOB["y"], KNOB["z"]), rot=(0, math.pi / 2, 0), mat=mats["FrameDark"])
    cap = cyl("knob_cap", KNOB["r"] * 0.82, 0.002,
              (0.2070, KNOB["y"], KNOB["z"]), rot=(0, math.pi / 2, 0), mat=mats["Aluminum"])
    mark = box("knob_mark", (0.0012, 0.008, 0.0022),
               (0.2073, KNOB["y"] - 0.0065, KNOB["z"]), mat=mats["VoidDark"])
    join_parts("Knob", [knob, cap, mark])
    ck = cyl("ck_body", COOLKEY["r"], COOLKEY["h"],
             (0.2025, COOLKEY["y"], COOLKEY["z"]), rot=(0, math.pi / 2, 0), mat=mats["FrameDark"])
    dot = cyl("ck_dot", COOLKEY["r"] * 0.45, 0.0015,
              (0.2057, COOLKEY["y"], COOLKEY["z"]), rot=(0, math.pi / 2, 0), mat=mats["BandMint"])
    join_parts("CoolKey", [ck, dot])
    return tower

# ================= 场景 =================
TARGET = Vector((0.102, 0.0, 0.0))

def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = {
        "BodyIvory": new_mat("BodyIvory", C_IVORY, 0.0, 0.45),
        "Aluminum":  new_mat("Aluminum",  C_ALUM,  1.0, 0.22),
        "Grid":      new_mat("Grid",      C_GRAY,  0.2, 0.55),
        "FrameDark": new_mat("FrameDark", C_GRAY,  0.3, 0.45),
        "VoidDark":  new_mat("VoidDark",  C_BLACK, 0.0, 0.8),
        "GrilleDark": new_mat("GrilleDark", (0.005, 0.005, 0.008, 1.0), 0.0, 0.9),
        "BandMint":  new_mat("BandMint",  C_MINT,  0.0, 0.42,
                             emission=C_MINT, emission_strength=0.5),
        "GlassDark": new_mat("GlassDark", (0.008, 0.012, 0.018, 1.0), 0.4, 0.18),
        "DigitGlow": new_mat("DigitGlow", (0.02, 0.05, 0.10, 1.0), 0.0, 0.3,
                             emission=C_CYAN, emission_strength=5.0),
    }
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    if FAST:
        scene.render.resolution_x = 480
        scene.render.resolution_y = 640
    else:
        scene.render.resolution_x = 768
        scene.render.resolution_y = 1024
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.4
    try:
        scene.eevee.taa_render_samples = 16 if FAST else 64
    except Exception:
        pass
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 0.6
    def add_area(name, loc, energy, size=0.4):
        bpy.ops.object.light_add(type="AREA", location=loc)
        lamp = bpy.context.active_object
        lamp.name = name
        lamp.data.energy = energy
        lamp.data.size = size
        fwd = (TARGET - Vector(loc)).normalized()
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
    add_area("KeyLight", (0.35, 0.40, 0.35), 4.0)
    add_area("FillLight", (0.10, -0.15, -0.55), 1.5)
    add_area("RimLight", (0.45, -0.45, 0.25), 2.5)
    return mats, scene

def aim_camera(cam, target, loc, up_hint=Vector((1.0, 0.0, 0.0))):
    fwd = (target - loc).normalized()
    z = -fwd
    up = up_hint
    x = up.cross(z)
    if x.length < 1e-6:
        up = Vector((0.0, 0.0, 1.0))
        x = up.cross(z)
    x.normalize()
    y = z.cross(x)
    y.normalize()
    cam.rotation_euler = mathutils.Matrix((x, y, z)).transposed().to_euler()

VIEWS = {
    "front":         Vector((0.102, 0.62, 0.00)),
    "three_quarter": Vector((0.40, 0.40, 0.44)),
    "side":          Vector((0.102, 0.00, 0.62)),
    "back":          Vector((0.102, -0.62, 0.00)),
    "top":           Vector((0.45, 0.00, 0.001)),
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
        # 俯视图：产品前方(+Y)朝画面下方
        up = Vector((0.0, -1.0, 0.0)) if name == "top" else Vector((1.0, 0.0, 0.0))
        aim_camera(cam, TARGET, loc, up)
        scene.camera = cam
        scene.render.filepath = f"{out_dir}/{name}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED:", f"{out_dir}/{name}.png")
        bpy.data.objects.remove(cam, do_unlink=True)
    if not FAST:
        blend_path = "/Users/hhh0x/chuifnegji/puzhi-fan/cad/form_d.blend"
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("BLEND SAVED:", blend_path)

BASE_DIR = "/Users/hhh0x/chuifnegji/puzhi-fan/cad"
render_set(os.path.join(BASE_DIR, "renders_form_d"))
print("ALL DONE")
