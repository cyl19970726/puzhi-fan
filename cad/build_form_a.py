"""
LiteCool S1 — 形态 A「桌面挂机」程序化概念模型 + 渲染
用法: blender --background --factory-startup --python build_form_a.py
      FAST=1(默认) 480px 低采样只渲 front/three_quarter；FAST=0 1024px 全五视图
坐标约定(与 build_render.py 一致):
  X = 高度（竖直）；底座 16mm + 机身 140mm = 总高 156mm
  Y = 前后（前 = +Y：出风口 + 导风板 + 数显；后 = -Y：进风格栅 + Type-C）
  Z = 左右（右 = +Z：数显右上 / 顶部旋钮偏右；两侧 = 热排格栅）
形态依据: design/form-directions.md §2 方向 A；architecture/product-architecture.md §3 双风道
输出: renders_form_a/{front,three_quarter,side,back,top}.png（透明底 RGBA）
"""
import bpy
import math
import mathutils
import os
from mathutils import Vector

# ================= 参数（form-directions §2：W220 × H140 × D110） =================
BODY_W, BODY_H, BODY_D = 0.220, 0.140, 0.110   # 机身 Z×X×Y
BODY_R = 0.012                                  # 机身圆角
BASE_H = 0.016                                  # 配重滑板座高
BODY_X0 = BASE_H                                # 机身下缘
BODY_XC = BASE_H + BODY_H / 2                   # 机身中心高 0.086
FRONT_Y = BODY_D / 2                            # 机身前面 y=+0.055
PANEL_T = 0.005                                 # 前壳厚（M6 前壳，微微凸出）
OUTLET = dict(x=0.064, w=0.188, h=0.050)        # 出风口（偏下，空调挂机语言）
LOUVER = dict(n=3, pitch=0.0155, chord=0.013, tilt=15.0)  # 导风板下倾 15°
DISP = dict(x=0.118, z=0.072, w=0.052, h=0.026)          # 数显（正面右上）
HOTVENT = dict(x0=0.055, x1=0.125, y0=-0.048, y1=0.008, bars=9)   # 侧热排（±Z 面，偏后）
INTAKE = dict(x0=0.058, x1=0.130, z0=-0.075, z1=0.075, bars=8)    # 后进风（-Y 面）
KNOB = dict(r=0.016, h=0.010, y=0.006, z=0.062)          # 顶部大旋钮
COOLKEY = dict(r=0.007, h=0.005, y=0.006, z=0.012)       # 制冷键
BAND_X = 0.030                                            # 薄荷腰线高度

C_IVORY = (0.949, 0.937, 0.914, 1.0)     # #F2EFE9 雾白
C_MINT  = (0.45, 0.78, 0.62, 1.0)        # 薄荷绿腰线（略提饱和抗直射光）
C_GRAY  = (0.06, 0.063, 0.068, 1.0)      # 深灰格栅
C_ALUM  = (0.82, 0.84, 0.87, 1.0)        # 拉丝铝
C_CYAN  = (0.15, 0.70, 1.00, 1.0)        # 数显青色辉光
C_BLACK = (0.05, 0.05, 0.06, 1.0)

FAST = os.environ.get("FAST", "1") == "1"

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

def join_parts(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

# 7 段数码管字形（段: top/mid/bot/ul/ur/ll/lr）
SEG_MAP = {
    "0": "top ul ur ll lr bot", "1": "ur lr", "2": "top ur mid ll bot",
    "3": "top ur mid lr bot", "4": "ul ur mid lr", "5": "top ul mid lr bot",
    "6": "top ul mid ll lr bot", "7": "top ur lr", "8": "top mid bot ul ur ll lr",
    "9": "top ul ur mid lr bot",
}

def build_display_text(text, cx, y, cz, mat):
    """7 段数码管风格字符，法线 +Y，整体以 cz 居中，返回合并后的单个 mesh"""
    h, w, t, d = 0.016, 0.0085, 0.0016, 0.001
    pitch = w + 0.0045
    # 先算总宽用于居中
    widths = [pitch * 0.45 if ch == "." else pitch for ch in text]
    total = sum(widths) - (pitch - w)  # 末尾字符只占 w
    objs = []
    zi = cz - total / 2 + w / 2
    for ch in text:
        if ch == ".":
            objs.append(box("seg", (t, d, t), (cx - h / 2 + t / 2, y, zi - w / 2), mat=mat))
            zi += pitch * 0.45
            continue
        for s in SEG_MAP[ch].split():
            if s == "top":
                o = box("seg", (t, d, w), (cx + h / 2 - t / 2, y, zi), mat=mat)
            elif s == "mid":
                o = box("seg", (t, d, w), (cx, y, zi), mat=mat)
            elif s == "bot":
                o = box("seg", (t, d, w), (cx - h / 2 + t / 2, y, zi), mat=mat)
            elif s == "ul":
                o = box("seg", (h / 2, d, t), (cx + h / 4, y, zi - w / 2 + t / 2), mat=mat)
            elif s == "ur":
                o = box("seg", (h / 2, d, t), (cx + h / 4, y, zi + w / 2 - t / 2), mat=mat)
            elif s == "ll":
                o = box("seg", (h / 2, d, t), (cx - h / 4, y, zi - w / 2 + t / 2), mat=mat)
            elif s == "lr":
                o = box("seg", (h / 2, d, t), (cx - h / 4, y, zi + w / 2 - t / 2), mat=mat)
            objs.append(o)
        zi += pitch
    return join_parts("Display", objs)

# ================= 构建 =================
def build(mats):
    # 机身（横置圆角方体，挂机语言主体）
    body = box("Body", (BODY_H, BODY_D, BODY_W), (BODY_XC, 0, 0),
               mat=mats["BodyIvory"], bevel=BODY_R, bevel_seg=8)
    # 整块配重滑板座（低重心、大面积，前缘微探出）
    base = box("Base", (BASE_H, BODY_D + 0.008, BODY_W + 0.008), (BASE_H / 2, 0, 0),
               mat=mats["BodyIvory"], bevel=0.006, bevel_seg=6)
    # 防滑硅胶圈（底座底面整圈，侧视可见一圈深灰）
    skid = box("SkidPad", (0.004, BODY_D - 0.006, BODY_W - 0.008), (-0.001, 0, 0),
               mat=mats["FrameDark"], bevel=0.002, bevel_seg=4)
    # 薄荷绿细腰线（壳体分模线，品牌基因）
    band = box("Band", (0.004, BODY_D + 0.004, BODY_W + 0.004), (BAND_X, 0, 0),
               mat=mats["BandMint"], bevel=0.0018, bevel_seg=3)
    # ---- 前壳 + 出风口 + 导风板（空调感第一符号） ----
    panel = box("FrontPanel", (BODY_H - 0.004, PANEL_T, BODY_W - 0.004),
                (BODY_XC, FRONT_Y + PANEL_T / 2 - 0.001, 0),
                mat=mats["BodyIvory"], bevel=0.010, bevel_seg=6)
    # 机身出风口凹腔（深色内腔 = 风道）
    cav = box("cutter_outlet", (OUTLET["h"] + 0.004, 0.030, OUTLET["w"] + 0.004),
              (OUTLET["x"], FRONT_Y - 0.012, 0), bevel=0.006, bevel_seg=4)
    boolean_cut(body, cav)
    duct = box("OutletCavity", (OUTLET["h"] - 0.002, 0.004, OUTLET["w"] - 0.002),
               (OUTLET["x"], FRONT_Y - 0.024, 0), mat=mats["GrilleDark"], bevel=0.004, bevel_seg=3)
    # 前壳出风槽（比凹腔略大，露出斜切边）
    slot = box("cutter_slot", (OUTLET["h"] + 0.008, PANEL_T + 0.006, OUTLET["w"] + 0.008),
               (OUTLET["x"], FRONT_Y + PANEL_T / 2 - 0.001, 0), bevel=0.007, bevel_seg=4)
    boolean_cut(panel, slot)
    # 可调导风板 ×3，下倾 15°（绕 Z 轴：前缘下压）
    for i in range(LOUVER["n"]):
        xx = OUTLET["x"] + (i - (LOUVER["n"] - 1) / 2) * LOUVER["pitch"]
        lv = box(f"Louver_{i}", (LOUVER["chord"], 0.0022, OUTLET["w"] - 0.010),
                 (xx, FRONT_Y - 0.004, 0), mat=mats["BodyIvory"], bevel=0.001, bevel_seg=3)
        lv.rotation_euler = (0, 0, math.radians(LOUVER["tilt"]))
    # ---- 出风温度大数显（正面右上，数码管风格，发光青色） ----
    panel_front_y = FRONT_Y + PANEL_T - 0.001          # 前壳外表面
    glass = box("DisplayGlass", (DISP["h"], 0.0015, DISP["w"]),
                (DISP["x"], panel_front_y + 0.0008, DISP["z"]),
                mat=mats["GlassDark"], bevel=0.004, bevel_seg=4)
    build_display_text("22.0", DISP["x"], panel_front_y + 0.0022, DISP["z"], mats["DigitGlow"])
    # ---- 侧热排格栅（±Z 面偏后，"室外机"语言：凹腔 + 竖条格栅） ----
    hv_x = (HOTVENT["x0"] + HOTVENT["x1"]) / 2
    hv_h = HOTVENT["x1"] - HOTVENT["x0"]
    hv_y = (HOTVENT["y0"] + HOTVENT["y1"]) / 2
    hv_d = HOTVENT["y1"] - HOTVENT["y0"]
    for side, sz in (("R", 1.0), ("L", -1.0)):
        zf = sz * BODY_W / 2
        rec = box(f"cutter_hv_{side}", (hv_h + 0.004, hv_d + 0.004, 0.012),
                  (hv_x, hv_y, zf - sz * 0.004), bevel=0.005, bevel_seg=4)
        boolean_cut(body, rec)
        plate = box(f"HotVentCavity_{side}", (hv_h - 0.002, hv_d - 0.002, 0.002),
                    (hv_x, hv_y, zf - sz * 0.008), mat=mats["GrilleDark"], bevel=0.004, bevel_seg=3)
        slats = []
        for i in range(HOTVENT["bars"]):
            yy = HOTVENT["y0"] + (i + 0.5) * hv_d / HOTVENT["bars"]
            slats.append(box(f"hv_{side}_{i}", (hv_h - 0.006, 0.0032, 0.002),
                             (hv_x, yy, zf + sz * 0.0005), mat=mats["Grid"]))
        join_parts(f"HotVent_{side}", slats)
    # ---- 后进风格栅（-Y 面，横条，与热排竖条造型区分） ----
    in_x = (INTAKE["x0"] + INTAKE["x1"]) / 2
    in_h = INTAKE["x1"] - INTAKE["x0"]
    in_w = INTAKE["z1"] - INTAKE["z0"]
    rec = box("cutter_intake", (in_h + 0.004, 0.012, in_w + 0.004),
              (in_x, -FRONT_Y + 0.004, 0), bevel=0.005, bevel_seg=4)
    boolean_cut(body, rec)
    plate = box("IntakeCavity", (in_h - 0.002, 0.002, in_w - 0.002),
                (in_x, -FRONT_Y + 0.008, 0), mat=mats["GrilleDark"], bevel=0.004, bevel_seg=3)
    bars = []
    for i in range(INTAKE["bars"]):
        xx = INTAKE["x0"] + (i + 0.5) * in_h / INTAKE["bars"]
        bars.append(box(f"in_{i}", (0.0038, 0.002, in_w - 0.006),
                        (xx, -FRONT_Y - 0.0005, 0), mat=mats["Grid"]))
    join_parts("IntakeGrille", bars)
    # ---- 顶部交互：大旋钮（100 档无级）+ 制冷键 ----
    top_x = BODY_X0 + BODY_H
    knob = cyl("Knob", KNOB["r"], KNOB["h"], (top_x + KNOB["h"] / 2 - 0.002, KNOB["y"], KNOB["z"]),
               rot=(0, math.pi / 2, 0), mat=mats["FrameDark"])
    cap = cyl("KnobCap", KNOB["r"] * 0.82, 0.002, (top_x + KNOB["h"] - 0.002, KNOB["y"], KNOB["z"]),
              rot=(0, math.pi / 2, 0), mat=mats["Aluminum"])
    mark = box("KnobMark", (0.0012, 0.009, 0.0022),
               (top_x + KNOB["h"] - 0.0005, KNOB["y"] - 0.008, KNOB["z"]), mat=mats["VoidDark"])
    join_parts("KnobAsm", [knob, cap, mark]).name = "Knob"
    ck = cyl("CoolKey", COOLKEY["r"], COOLKEY["h"],
             (top_x + COOLKEY["h"] / 2 - 0.001, COOLKEY["y"], COOLKEY["z"]),
             rot=(0, math.pi / 2, 0), mat=mats["FrameDark"])
    ck_dot = cyl("CoolKeyDot", COOLKEY["r"] * 0.45, 0.0015,
                 (top_x + COOLKEY["h"] - 0.0005, COOLKEY["y"], COOLKEY["z"]),
                 rot=(0, math.pi / 2, 0), mat=mats["BandMint"])
    join_parts("CoolKeyAsm", [ck, ck_dot]).name = "CoolKey"
    # ---- 底座后 Type-C ----
    tc = box("TypeC", (0.005, 0.003, 0.011), (0.008, -(BODY_D + 0.008) / 2 + 0.0005, 0),
             mat=mats["VoidDark"], bevel=0.0015, bevel_seg=3)
    return body

# ================= 场景 =================
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
        scene.render.resolution_y = 360
    else:
        scene.render.resolution_x = 1024
        scene.render.resolution_y = 768
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
    # 三点布光（瞄准机身中心）
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

TARGET = Vector((BODY_XC, 0.0, 0.0))
VIEWS = {
    "front":         Vector((BODY_XC, 0.60, 0.00)),
    "three_quarter": Vector((0.34, 0.38, 0.40)),
    "side":          Vector((BODY_XC, 0.00, 0.60)),
    "back":          Vector((BODY_XC, -0.60, 0.00)),
    "top":           Vector((0.60, 0.001, 0.001)),
}
FAST_VIEWS = ["front", "three_quarter", "side", "back", "top"]

def render_set(out_dir):
    mats, scene = setup_scene()
    build(mats)
    bpy.context.view_layer.update()
    names = FAST_VIEWS if FAST else list(VIEWS.keys())
    for name in names:
        loc = VIEWS[name]
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.name = f"cam_{name}"
        cam.data.lens = 55
        # 俯视图：产品前方(+Y)朝画面下方，长轴(Z)水平
        up = Vector((0.0, -1.0, 0.0)) if name == "top" else Vector((1.0, 0.0, 0.0))
        aim_camera(cam, TARGET, loc, up)
        scene.camera = cam
        scene.render.filepath = f"{out_dir}/{name}.png"
        bpy.ops.render.render(write_still=True)
        print("RENDERED:", f"{out_dir}/{name}.png")
        bpy.data.objects.remove(cam, do_unlink=True)
    if not FAST:
        blend_path = "/Users/hhh0x/chuifnegji/puzhi-fan/cad/form_a.blend"
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("BLEND SAVED:", blend_path)

BASE_DIR = "/Users/hhh0x/chuifnegji/puzhi-fan/cad"
render_set(os.path.join(BASE_DIR, "renders_form_a"))
print("ALL DONE")
