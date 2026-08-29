"""
LiteCool S1 — 形态 B「复古收音机」程序化概念模型 + 渲染
用法: blender --background --factory-startup --python build_form_b.py
      CMF=cream(默认)|green  双 CMF 方案；FAST=1(默认) 480px 低采样；FAST=0 1024px 终渲
坐标约定(与 build_form_a.py 一致):
  X = 高度（竖直）；支脚 10mm + 机身 150mm = 总高 160mm
  Y = 前后（前 = +Y：整面细网罩；后 = -Y：进风格栅 + Type-C）
  Z = 左右（右 = +Z）
形态依据: design/form-directions.md §3 方向 B；专利规避硬约束 research/patent_avoidance.md §3 方向 B:
  · 整面均匀细网罩(覆盖正面 80%+)，无偏置大圆喇叭区、无调频刻度窗
  · 单颗大旋钮(顶部居中)，无双旋钮+刻度窗三联布局
  · 数显小圆窗放顶面前缘(避开正面收音机构图)
  · TEC 热排从顶部后缘出，侧面不开喇叭式圆网
  · 矮圆木脚(非猫王式外撇金属锥脚)、菱形编织金属细网(非布艺/横条纹)
输出: renders_form_b/{cmf}/{front,three_quarter,side,back,top}.png（透明底 RGBA）
"""
import bpy
import math
import mathutils
import os
from mathutils import Vector

# ================= 参数（form-directions §3：W200 × H150 × D120） =================
FEET_H = 0.010                                  # 矮支脚高
BODY_W, BODY_H, BODY_D = 0.200, 0.150, 0.120    # 机身 Z×X×Y
BODY_R = 0.016                                  # 机身圆角(大 R，与猫王小 R 拉开)
BODY_X0 = FEET_H                                # 机身下缘 0.010
BODY_XC = BODY_X0 + BODY_H / 2                  # 机身中心高 0.085
TOP_X = BODY_X0 + BODY_H                        # 顶面 0.160
FRONT_Y = BODY_D / 2                            # 前面 y=+0.060
MESH = dict(x=0.085, w=0.190, h=0.128)          # 整面细网罩(正面 81% 面积)
DISP = dict(y=0.038, z=-0.055, r=0.012)         # 顶面小圆数显窗(前缘左)
KNOB = dict(r=0.021, h=0.016, y=-0.012, z=0.0)  # 顶部单颗大旋钮(居中偏后)
COOLKEY = dict(r=0.0075, h=0.005, y=0.038, z=0.055)  # 制冷键(前缘右，与数显对称)
HOTVENT = dict(y0=-0.054, y1=-0.034, z0=-0.072, z1=0.072, slats=6)  # 顶部后缘热排
INTAKE = dict(x0=0.034, x1=0.078, z0=-0.070, z1=0.070, bars=6)      # 背部进风(下段)
BAND_X = 0.0155                                 # 装饰腰线(木纹/黄铜)高度(整体低于网罩下沿 0.021)
MINT_X = 0.0193                                 # 薄荷绿品牌细线高度(腰线与网罩之间的勾边)

C_MINT = (0.45, 0.78, 0.62, 1.0)         # 薄荷绿 #A8D8C8 附近(略提饱和抗直射)
C_CYAN = (0.15, 0.70, 1.00, 1.0)         # 数显青色辉光
C_BLACK = (0.05, 0.05, 0.06, 1.0)

CMF = os.environ.get("CMF", "cream")
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

def woven_mesh_mat(name, c_dark, c_light):
    """菱形编织金属细网：两组正交 Wave(Object 坐标, 周期≈2.2mm)相乘 → 颜色 + Bump"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = 0.85
    bsdf.inputs["Roughness"].default_value = 0.42
    tex = nt.nodes.new("ShaderNodeTexCoord")
    waves = []
    for direction in ("X", "Z"):
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.bands_direction = direction
        w.inputs["Scale"].default_value = 450.0     # ≈2.2mm 周期(细网)
        w.inputs["Distortion"].default_value = 0.0
        nt.links.new(tex.outputs["Object"], w.inputs["Vector"])
        waves.append(w)
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    nt.links.new(waves[0].outputs["Color"], mult.inputs[0])
    nt.links.new(waves[1].outputs["Color"], mult.inputs[1])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = c_dark
    ramp.color_ramp.elements[1].color = c_light
    nt.links.new(mult.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(mult.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def wood_mat(name):
    """胡桃木纹：Noise → 双色棕 ramp(概念级木纹，旋钮/腰线/支脚共用)"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.45
    tex = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 5.0
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.7
    nt.links.new(tex.outputs["Object"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.085, 0.04, 1.0)
    ramp.color_ramp.elements[1].color = (0.42, 0.25, 0.12, 1.0)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
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

def cyl(name, radius, depth, loc, rot=(0, 0, 0), mat=None, verts=64, radius2=None):
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=radius2,
                                        depth=depth, location=loc)
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

def build_display_top(text, x, cy, cz, mat):
    """顶面 7 段数码管字符(法线 +X)：字符躺 Z-Y 平面，字顶朝 -Y(机身后)，左→右沿 +Z
    俯视图(up=-Y, 产品前方朝画面下方)中文字为正立。整体合并为单个 mesh 'Display'"""
    h, w, t, d = 0.009, 0.0048, 0.0011, 0.0009
    pitch = w + 0.0024
    widths = [pitch * 0.45 if ch == "." else pitch for ch in text]
    total = sum(widths) - (pitch - w)
    objs = []
    zi = cz - total / 2 + w / 2
    for ch in text:
        if ch == ".":
            objs.append(box("seg", (d, t, t), (x, cy + h / 2 - t / 2, zi - w / 2), mat=mat))
            zi += pitch * 0.45
            continue
        for s in SEG_MAP[ch].split():
            if s == "top":
                o = box("seg", (d, t, w), (x, cy - h / 2 + t / 2, zi), mat=mat)
            elif s == "mid":
                o = box("seg", (d, t, w), (x, cy, zi), mat=mat)
            elif s == "bot":
                o = box("seg", (d, t, w), (x, cy + h / 2 - t / 2, zi), mat=mat)
            elif s == "ul":
                o = box("seg", (d, h / 2, t), (x, cy - h / 4, zi - w / 2 + t / 2), mat=mat)
            elif s == "ur":
                o = box("seg", (d, h / 2, t), (x, cy - h / 4, zi + w / 2 - t / 2), mat=mat)
            elif s == "ll":
                o = box("seg", (d, h / 2, t), (x, cy + h / 4, zi - w / 2 + t / 2), mat=mat)
            elif s == "lr":
                o = box("seg", (d, h / 2, t), (x, cy + h / 4, zi + w / 2 - t / 2), mat=mat)
            objs.append(o)
        zi += pitch
    return join_parts("Display", objs)

# ================= 构建 =================
def build(mats, cfg):
    # 机身（圆角方盒，复古情感语言主体）
    body = box("Body", (BODY_H, BODY_D, BODY_W), (BODY_XC, 0, 0),
               mat=mats["Body"], bevel=BODY_R, bevel_seg=8)
    # 矮支脚 ×4（ squat 圆木脚/黄铜脚，与猫王外撇金属锥脚拉开）
    feet = []
    for sy in (1.0, -1.0):
        for sz in (1.0, -1.0):
            f = cyl("foot", 0.009, FEET_H, (FEET_H / 2, sy * 0.040, sz * 0.075),
                    rot=(0, math.pi / 2, 0), mat=mats["Feet"], verts=32, radius2=0.011)
            feet.append(f)
    join_parts("Feet", feet)
    # 装饰腰线（CMF1 胡桃木 / CMF2 黄铜）+ 薄荷绿品牌细线
    # 前面部分藏于网罩之后 → 正面保持"整面网"，侧面/背面读出腰线
    box("Band", (0.005, BODY_D + 0.0008, BODY_W + 0.0008), (BAND_X, 0, 0),
        mat=mats["Band"], bevel=0.002, bevel_seg=3)
    box("MintLine", (0.0016, BODY_D + 0.0008, BODY_W + 0.0008), (MINT_X, 0, 0),
        mat=mats["BandMint"], bevel=0.0008, bevel_seg=3)
    # ---- 正面整面均匀细网罩（浅凹腔 + 深色衬底 + 金属编织网板，覆盖正面 81%） ----
    rec = box("cutter_mesh", (MESH["h"] + 0.004, 0.006, MESH["w"] + 0.004),
              (MESH["x"], FRONT_Y - 0.002, 0), bevel=0.008, bevel_seg=4)
    boolean_cut(body, rec)
    box("MeshCavity", (MESH["h"] - 0.001, 0.001, MESH["w"] - 0.001),
        (MESH["x"], FRONT_Y - 0.0045, 0), mat=mats["GrilleDark"], bevel=0.007, bevel_seg=3)
    box("FrontMesh", (MESH["h"], 0.003, MESH["w"]),
        (MESH["x"], FRONT_Y - 0.0015, 0), mat=mats["MeshMetal"], bevel=0.008, bevel_seg=6)
    # ---- 顶面交互：小圆数显窗(前左) + 单颗大旋钮(中) + 制冷键(前右) ----
    # 数显： bezel 圈 + 深色玻璃 + 发光 7 段 "22.0"（出风温度常显）
    cyl("DisplayBezel", DISP["r"] + 0.0018, 0.0012, (TOP_X - 0.0002, DISP["y"], DISP["z"]),
        rot=(0, math.pi / 2, 0), mat=mats["Bezel"])
    cyl("DisplayGlass", DISP["r"], 0.001, (TOP_X + 0.0006, DISP["y"], DISP["z"]),
        rot=(0, math.pi / 2, 0), mat=mats["GlassDark"])
    build_display_top("22.0", TOP_X + 0.0016, DISP["y"], DISP["z"], mats["DigitGlow"])
    # 大旋钮（100 档无级）：胡桃木=光面车削；黄铜=滚花齿圈
    knob_parts = [cyl("knob", KNOB["r"], KNOB["h"],
                      (TOP_X + KNOB["h"] / 2 - 0.002, KNOB["y"], KNOB["z"]),
                      rot=(0, math.pi / 2, 0), mat=mats["Knob"])]
    if cfg["knurl"]:
        for i in range(40):
            a = i * 2 * math.pi / 40
            t = box("knurl", (KNOB["h"] - 0.002, 0.0035, 0.002),
                    (TOP_X + KNOB["h"] / 2 - 0.002,
                     KNOB["y"] + 0.0208 * math.cos(a),
                     KNOB["z"] + 0.0208 * math.sin(a)),
                    mat=mats["Knob"])
            t.rotation_euler = (a, 0, 0)
            knob_parts.append(t)
    knob_parts.append(cyl("knobcap", KNOB["r"] * 0.80, 0.0015,
                          (TOP_X + KNOB["h"] - 0.0025, KNOB["y"], KNOB["z"]),
                          rot=(0, math.pi / 2, 0), mat=mats["KnobCap"]))
    knob_parts.append(box("knobmark", (0.0012, 0.008, 0.0022),
                          (TOP_X + KNOB["h"] - 0.0012, KNOB["y"] - 0.008, KNOB["z"]),
                          mat=mats["VoidDark"]))
    join_parts("Knob", knob_parts)
    # 制冷键（TEC 开/关，薄荷标识点）
    ck = cyl("ck", COOLKEY["r"], COOLKEY["h"],
             (TOP_X + COOLKEY["h"] / 2 - 0.001, COOLKEY["y"], COOLKEY["z"]),
             rot=(0, math.pi / 2, 0), mat=mats["CoolKey"])
    ck_dot = cyl("ckdot", COOLKEY["r"] * 0.45, 0.0015,
                 (TOP_X + COOLKEY["h"] - 0.0005, COOLKEY["y"], COOLKEY["z"]),
                 rot=(0, math.pi / 2, 0), mat=mats["BandMint"])
    join_parts("CoolKey", [ck, ck_dot])
    # ---- TEC 热排：顶部后缘横槽格栅（造型化，避让侧面"喇叭式"圆网） ----
    hv_y = (HOTVENT["y0"] + HOTVENT["y1"]) / 2
    hv_d = HOTVENT["y1"] - HOTVENT["y0"]
    hv_w = HOTVENT["z1"] - HOTVENT["z0"]
    rec = box("cutter_hv", (0.008, hv_d + 0.002, hv_w + 0.004),
              (TOP_X - 0.002, hv_y, 0), bevel=0.004, bevel_seg=3)
    boolean_cut(body, rec)
    box("HotVentCavity", (0.001, hv_d - 0.002, hv_w - 0.002),
        (TOP_X - 0.005, hv_y, 0), mat=mats["GrilleDark"], bevel=0.003, bevel_seg=3)
    slats = []
    for i in range(HOTVENT["slats"]):
        yy = HOTVENT["y0"] + (i + 0.5) * hv_d / HOTVENT["slats"]
        slats.append(box(f"hv_{i}", (0.002, 0.0018, hv_w - 0.006),
                         (TOP_X - 0.0005, yy, 0), mat=mats["VentSlat"]))
    join_parts("HotVent", slats)
    # ---- 背部进风格栅（下段横条） + Type-C ----
    in_x = (INTAKE["x0"] + INTAKE["x1"]) / 2
    in_h = INTAKE["x1"] - INTAKE["x0"]
    in_w = INTAKE["z1"] - INTAKE["z0"]
    rec = box("cutter_intake", (in_h + 0.004, 0.012, in_w + 0.004),
              (in_x, -FRONT_Y + 0.004, 0), bevel=0.005, bevel_seg=4)
    boolean_cut(body, rec)
    box("IntakeCavity", (in_h - 0.002, 0.002, in_w - 0.002),
        (in_x, -FRONT_Y + 0.008, 0), mat=mats["GrilleDark"], bevel=0.004, bevel_seg=3)
    bars = []
    for i in range(INTAKE["bars"]):
        xx = INTAKE["x0"] + (i + 0.5) * in_h / INTAKE["bars"]
        bars.append(box(f"in_{i}", (0.0038, 0.002, in_w - 0.006),
                        (xx, -FRONT_Y - 0.0005, 0), mat=mats["VentSlat"]))
    join_parts("IntakeGrille", bars)
    box("TypeC", (0.005, 0.003, 0.011), (0.020, -FRONT_Y - 0.0005, 0.050),
        mat=mats["VoidDark"], bevel=0.0015, bevel_seg=3)
    return body

# ================= CMF 方案 =================
def make_mats():
    if CMF == "cream":
        # ① 奶油白 + 胡桃木纹旋钮/腰线（哑光小家电）
        mats = {
            "Body":      new_mat("BodyCream", (0.955, 0.940, 0.905, 1.0), 0.0, 0.48),
            "MeshMetal": woven_mesh_mat("MeshBronze", (0.10, 0.09, 0.075, 1.0), (0.38, 0.33, 0.26, 1.0)),
            "Knob":      wood_mat("Walnut"),
            "KnobCap":   wood_mat("WalnutCap"),
            "Band":      wood_mat("WalnutBand"),
            "Feet":      wood_mat("WalnutFeet"),
            "Bezel":     wood_mat("WalnutBezel"),
            "CoolKey":   new_mat("CoolKeyCream", (0.90, 0.885, 0.85, 1.0), 0.0, 0.4),
            "VentSlat":  new_mat("VentSlatCream", (0.90, 0.885, 0.85, 1.0), 0.0, 0.5),
        }
        cfg = {"knurl": False}
    else:
        # ② 墨绿 + 黄铜点缀（哑光小家电）
        mats = {
            "Body":      new_mat("BodyGreen", (0.022, 0.062, 0.042, 1.0), 0.0, 0.46),
            "MeshMetal": woven_mesh_mat("MeshCharcoal", (0.03, 0.032, 0.035, 1.0), (0.16, 0.17, 0.18, 1.0)),
            "Knob":      new_mat("Brass", (0.42, 0.27, 0.10, 1.0), 1.0, 0.32),
            "KnobCap":   new_mat("BrassCap", (0.50, 0.33, 0.13, 1.0), 1.0, 0.24),
            "Band":      new_mat("BrassBand", (0.42, 0.27, 0.10, 1.0), 1.0, 0.34),
            "Feet":      new_mat("BrassFeet", (0.36, 0.23, 0.09, 1.0), 1.0, 0.40),
            "Bezel":     new_mat("BrassBezel", (0.42, 0.27, 0.10, 1.0), 1.0, 0.30),
            "CoolKey":   new_mat("CoolKeyGreen", (0.03, 0.06, 0.045, 1.0), 0.0, 0.4),
            "VentSlat":  new_mat("VentSlatGreen", (0.018, 0.052, 0.035, 1.0), 0.0, 0.5),
        }
        cfg = {"knurl": True}
    mats.update({
        "GrilleDark": new_mat("GrilleDark", (0.005, 0.005, 0.008, 1.0), 0.0, 0.9),
        "VoidDark":   new_mat("VoidDark", C_BLACK, 0.0, 0.8),
        "BandMint":   new_mat("BandMint", C_MINT, 0.0, 0.42,
                              emission=C_MINT, emission_strength=0.5),
        "GlassDark":  new_mat("GlassDark", (0.008, 0.012, 0.018, 1.0), 0.4, 0.18),
        "DigitGlow":  new_mat("DigitGlow", (0.02, 0.05, 0.10, 1.0), 0.0, 0.3,
                              emission=C_CYAN, emission_strength=5.0),
    })
    return mats, cfg

# ================= 场景 =================
def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats, cfg = make_mats()
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
    # 三点布光（与形态 A 同标定）
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
    return mats, cfg, scene

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
    "front":         Vector((BODY_XC, 0.55, 0.00)),
    "three_quarter": Vector((0.32, 0.36, 0.38)),
    "side":          Vector((BODY_XC, 0.00, 0.55)),
    "back":          Vector((BODY_XC, -0.55, 0.00)),
    "top":           Vector((0.55, 0.001, 0.001)),
}

def render_set(out_dir):
    mats, cfg, scene = setup_scene()
    build(mats, cfg)
    bpy.context.view_layer.update()
    for name in VIEWS:
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
        blend_path = f"/Users/hhh0x/chuifnegji/puzhi-fan/cad/form_b_{CMF}.blend"
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print("BLEND SAVED:", blend_path)

BASE_DIR = "/Users/hhh0x/chuifnegji/puzhi-fan/cad"
render_set(os.path.join(BASE_DIR, "renders_form_b", CMF))
print("ALL DONE CMF=", CMF)
