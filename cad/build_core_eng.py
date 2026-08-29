"""
LiteCool S1 — 形态 A 工程级（DFM 级）装配体 v2.0
用法: blender --background --python build_core_eng.py      （FAST=1 默认 480px 快渲；FAST=0 800px 终渲）
与 build_core.py（概念级）的差异：
  1. 风道真实化：后进风/侧热排/前出风口全部 boolean 开真孔（不再是贴面格栅+假腔板）；
     中隔板延长为 L 形全风道隔板（冷/热腔物理分断, ADR-1）；热端鳍片通道朝右侧热排。
  2. 外壳 DFM：壳体 2.0mm 壁厚（外 frustum - 内 frustum 差集，非 solidify 近似）、
     可见竖边 1.5° 拔模（沿 Y 脱模方向锥度）、前壳↔后壳分件线（0.5mm 缝）、
     底座 3 颗螺丝柱（Ø2.5 通孔+Ø5 沉孔）、前网罩旋扣×3（转 15° 卡入, IF-3）、
     数显窗卡扣+遮光筋（IF-4）、电池仓防反插+减震筋（IF-5）。
  3. 导风联动真实化：28BYJ-48 → m0.8 12T 小齿轮 → 中间导风板端部 18T 扇形齿轮，
     3 片导风板端部曲柄销 + 联动杆同轴联动（啮合中心距 = 分度圆半径之和）。
  4. 密封：隔板与外壳接触边加 3mm 宽 ×1.5mm 深 EVA 密封棉槽 + EVA 棉条（IF-2）。
不读 form_a.blend：壳体全部按工程结构重建（外观尺寸/分件沿用形态 A 概念稿）。
输出:
  cad/assembly_a_eng.glb        — 40 个命名 mesh，extras 带 module/label/explode(glTF 坐标)
  cad/assembly_a_parts.json     — 工作台④数据源（glb 指向 assembly_a_eng.glb）
  cad/renders_assembly_eng/{assembled,exploded}.png
坐标约定（同 build_form_a.py）: X=高度, Y=前后(前=+Y), Z=左右(右=+Z)
"""
import bpy
import math
import mathutils
import os
import json
import struct
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLB_OUT = os.path.join(BASE_DIR, "assembly_a_eng.glb")
PARTS_JSON = os.path.join(BASE_DIR, "assembly_a_parts.json")
RENDER_DIR = os.path.join(BASE_DIR, "renders_assembly_eng")
FAST = os.environ.get("FAST", "1") == "1"

# ================= 总体参数（外形沿用形态 A：W220(Z)×H140(X)×D110(Y) + 底座16） =================
WALL = 0.002                  # 外壳壁厚 2.0mm（DFM 规则）
DRAFT = math.tan(math.radians(1.5))   # 拔模 1.5°（沿 Y 脱模：后小前大）
BODY_X0, BODY_X1 = 0.016, 0.156       # 机身高度范围（底座上缘→顶）
BODY_Y0, BODY_Y1 = -0.055, 0.055      # 机身后→前
BODY_Z = 0.110                        # 机身半宽
INTAKE = dict(x0=0.058, x1=0.130, z0=-0.075, z1=0.075, bars=8)   # 后进风真孔
HOTVENT = dict(x0=0.055, x1=0.125, y0=-0.048, y1=0.020, bars=9)  # 右侧热排真孔（鳍片通道朝此）
AUXVENT = dict(x0=0.055, x1=0.125, y0=-0.048, y1=0.008, bars=9)  # 左侧辅助进风真孔
OUTLET = dict(x0=0.035, x1=0.093, z=-0.098)                      # 前出风槽（半宽 z）
DISP = dict(x0=0.105, x1=0.131, z0=0.046, z1=0.098)              # 数显窗孔
LOUVER_X = [0.0485, 0.064, 0.0795]    # 3 片导风板 pivot（pitch 15.5mm）
LOUVER_Y = 0.046                       # 导风板 pivot 前后位置
GEAR_Z = 0.0955                        # 齿轮啮合平面（电机仓内）

# ================= 工具（与 build_form_a.py / build_core.py 同风格） =================
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

def box(name, size, loc, mat=None, bevel=0.0, bevel_seg=3):
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

def cyl(name, radius, depth, loc, rot=(0, 0, 0), mat=None, verts=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    if mat is not None:
        obj.data.materials.append(mat)
    return obj

def cone(name, r1, depth, loc, rot=(0, 0, 0), mat=None, verts=32):
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=0.0, depth=depth, vertices=verts, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.rotation_euler = rot
    if mat is not None:
        obj.data.materials.append(mat)
    return obj

def frustum_y(name, y0, y1, xb, zb, xt, zt, mat=None):
    """沿 Y 的拔模锥台：y0 截面 xb=(x0,x1)/zb=(z0,z1)，y1 截面 xt/zt（后小前大=1.5°拔模）"""
    v = [(xb[0], y0, zb[0]), (xb[1], y0, zb[0]), (xb[1], y0, zb[1]), (xb[0], y0, zb[1]),
         (xt[0], y1, zt[0]), (xt[1], y1, zt[0]), (xt[1], y1, zt[1]), (xt[0], y1, zt[1])]
    f = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (3, 2, 6, 7),
         (0, 3, 7, 4), (1, 5, 6, 2)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    if mat is not None:
        me.materials.append(mat)
    return obj

def apply_bevel(obj, width, seg=4):
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = width
    mod.segments = seg
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(30)
    bpy.ops.object.modifier_apply(modifier=mod.name)

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

def gear_mesh(name, teeth, module, thickness, loc, arc=None, mat=None):
    """m0.8 示意齿轮：梯形齿，X-Y 平面，沿 Z 拉伸。arc=(a0,a1) 时只在该角度范围出齿（扇形齿轮）。"""
    m = module
    rp = teeth * m / 2            # 分度圆半径
    rt = rp + m                   # 齿顶圆
    rr = rp - 1.25 * m            # 齿根圆
    p = 2 * math.pi / teeth
    pts = []
    for i in range(teeth):
        a = i * p
        in_arc = True
        if arc is not None:
            a0, a1 = arc
            in_arc = a0 <= a <= a1      # a 本就在 [0, 2π)，直接与出齿弧比较
        tip = rt if in_arc else rr
        for da, r in ((-0.5 * p, rr), (-0.30 * p, rr), (-0.15 * p, tip),
                      (0.15 * p, tip), (0.30 * p, rr), (0.5 * p, rr)):
            aa = a + da
            pts.append((r * math.cos(aa), r * math.sin(aa)))
    n = len(pts)
    cx, cy, cz = loc
    z0, z1 = cz - thickness / 2, cz + thickness / 2
    verts = [(cx + px, cy + py, z0) for px, py in pts] + \
            [(cx + px, cy + py, z1) for px, py in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    if mat is not None:
        me.materials.append(mat)
    return obj, rp

def arrow(name, p0, p1, mat, shaft_r=0.0035, head_r=0.009, head_l=0.022):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    total = d.length
    shaft_len = total - head_l
    mid = p0 + d.normalized() * (shaft_len / 2)
    sh = cyl(name + "_shaft", shaft_r, shaft_len, mid, mat=mat)
    tip = p0 + d.normalized() * (shaft_len + head_l / 2)
    hd = cone(name + "_head", head_r, head_l, tip, mat=mat)
    q = d.normalized().to_track_quat("Z", "X")
    sh.rotation_euler = q.to_euler()
    hd.rotation_euler = q.to_euler()
    return join_parts(name, [sh, hd])

# 7 段数码管字形（沿用 build_form_a.py）
SEG_MAP = {
    "0": "top ul ur ll lr bot", "1": "ur lr", "2": "top ur mid ll bot",
    "3": "top ur mid lr bot", "4": "ul ur mid lr", "5": "top ul mid lr bot",
    "6": "top ul mid ll lr bot", "7": "top ur lr", "8": "top mid bot ul ur ll lr",
    "9": "top ul ur mid lr bot",
}

def build_display_text(text, cx, y, cz, mat):
    h, w, t, d = 0.016, 0.0085, 0.0016, 0.001
    pitch = w + 0.0045
    widths = [pitch * 0.45 if ch == "." else pitch for ch in text]
    total = sum(widths) - (pitch - w)
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

# ================= 零件注册表（沿用旧命名体系；语义延续件同名，新增件同前缀） =================
SHELL_META = {
    "Base":           ("M1", "配重滑板底座(3×Ø2.5螺丝孔+沉孔)"),
    "SkidPad":        ("M1", "防滑硅胶圈"),
    "TypeC":          ("M1", "Type-C 进线口"),
    "M1_Bosses":      ("M1", "底座螺丝柱×3(Ø2.5柱+Ø5沉孔)"),
    "Body":           ("M6", "后壳/主壳(2mm壁厚+1.5°拔模+真孔)"),
    "FrontPanel":     ("M6", "前壳面板(2mm+分件线+出风/数显真孔)"),
    "Band":           ("M6", "薄荷腰线(外观分模线)"),
    "M6_TwistLock":   ("M6", "前壳旋扣×3(转15°卡入, IF-3)"),
    "Louver_0":       ("M6", "导风板 1(端部曲柄销)"),
    "Louver_1":       ("M6", "导风板 2(端部扇齿轴)"),
    "Louver_2":       ("M6", "导风板 3(端部曲柄销)"),
    "Display":        ("M7", "数码管字形 22.0"),
    "DisplayGlass":   ("M7", "半透数显窗 PMMA"),
    "M7_Clip":        ("M7", "数显窗卡扣×4+遮光筋(IF-4)"),
    "HotVent_L":      ("M5", "左侧辅助进风格栅(真孔)"),
    "HotVent_R":      ("M5", "右侧热排格栅(真孔)"),
    "IntakeGrille":   ("M5", "后进风格栅(真孔横条)"),
    "Knob":           ("M3", "旋钮(100档FOC)"),
    "CoolKey":        ("M3", "制冷键"),
}
CORE_META = {
    "M5_TEC":        ("M5", "TEC 制冷片 40×40×3.8"),
    "M5_ColdFins":   ("M5", "冷端铝鳍片组(风道沿Y)"),
    "M5_HotSink":    ("M5", "热端散热器(鳍片通道朝右+Z)"),
    "M5_Separator":  ("M5", "L形全风道中隔板(ADR-1,带EVA槽)"),
    "M5_EVA":        ("M5", "EVA密封棉条×6(IF-2,3×1.5槽)"),
    "M5_ColdDuct":   ("M5", "冷风道(风机→冷鳍→前出贯通腔)"),
    "M5_HotDuct":    ("M5", "热风道导流板(散热器→右侧排)"),
    "M4_FanFrame":   ("M4", "风机框 Ø80"),
    "M4_FanHub":     ("M4", "轮毂+无刷电机"),
    "M4_FanBlades":  ("M4", "扇叶 ×7"),
    "M2_Cell_A":     ("M2", "18650 电芯 A"),
    "M2_Cell_B":     ("M2", "18650 电芯 B"),
    "M2_Bracket":    ("M2", "电池仓(防反插+减震筋,IF-5)"),
    "M3_PCB":        ("M3", "主控 PCB(冷侧进风后方)"),
    "M3_ICs":        ("M3", "主要 IC(MCU/驱动/充电)"),
    "M3_Pot":        ("M3", "旋钮电位器"),
    "M1_Stepper":    ("M1", "28BYJ-48 步进电机(电机仓)"),
    "M1_Pinion":     ("M1", "小齿轮 m0.8 12T"),
    "M1_Sector":     ("M1", "扇形齿轮 m0.8 18T(中间导风板轴)"),
    "M1_Link":       ("M1", "导风板联动杆(3曲柄销同动)"),
    "M7_Module":     ("M7", "数码管模组"),
}

# 爆炸偏移（Blender 坐标系）
CENTER = Vector((0.086, 0.0, 0.0))
XP, XN, YP, YN, ZP, ZN = (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)
EXPLODE = {
    "Body": (XP, 0.11), "Band": (XP, 0.05), "FrontPanel": (YP, 0.10),
    "M6_TwistLock": (YP, 0.13),
    "Louver_0": (YP, 0.16), "Louver_1": (YP, 0.16), "Louver_2": (YP, 0.16),
    "Display": (YP, 0.13), "DisplayGlass": (YP, 0.135), "M7_Clip": (YP, 0.115),
    "Knob": (XP, 0.17), "CoolKey": (XP, 0.17),
    "Base": (XN, 0.06), "SkidPad": (XN, 0.115), "M1_Bosses": (XN, 0.095), "TypeC": (YN, 0.10),
    "HotVent_R": (ZP, 0.10), "HotVent_L": (ZN, 0.10),
    "IntakeGrille": (YN, 0.11),
    "M4_FanFrame": (ZN, 0.105), "M4_FanHub": (ZN, 0.105), "M4_FanBlades": (ZN, 0.105),
    "M5_ColdFins": (ZN, 0.075), "M5_TEC": (ZP, 0.032), "M5_HotSink": (ZP, 0.075),
    "M5_Separator": (XN, 0.05), "M5_EVA": (XN, 0.075),
    "M5_ColdDuct": (ZN, 0.045), "M5_HotDuct": (ZP, 0.10),
    "M2_Bracket": (ZN, 0.05), "M2_Cell_A": (ZN, 0.12), "M2_Cell_B": (ZN, 0.15),
    "M3_PCB": (YN, 0.075), "M3_ICs": (YN, 0.105), "M3_Pot": (XP, 0.155),
    "M1_Stepper": (ZP, 0.145), "M1_Pinion": (ZP, 0.17), "M1_Sector": (ZP, 0.17),
    "M1_Link": (ZP, 0.145),
    "M7_Module": (YP, 0.06),
}

# ================= 外壳（DFM 级重建） =================
def build_shell(m):
    parts = []
    # ---- 后壳/主壳 Body：外拔模锥台(圆角) − 内拔模锥台(前开口) = 2.0mm 壁厚 tub ----
    dx = DRAFT * (BODY_Y1 - BODY_Y0)            # 1.5° 拔模收缩量（后端，脱模方向 Y）
    body = frustum_y("Body", BODY_Y0, BODY_Y1,
                     (BODY_X0, BODY_X1 - dx), (-BODY_Z + dx, BODY_Z - dx),
                     (BODY_X0, BODY_X1), (-BODY_Z, BODY_Z), mat=m["BodyIvory"])
    apply_bevel(body, 0.010, seg=5)
    cav = frustum_y("cutter_cav", BODY_Y0 + WALL, BODY_Y1 + 0.010,
                    (BODY_X0 + WALL, BODY_X1 - dx - WALL),
                    (-BODY_Z + dx + WALL, BODY_Z - dx - WALL),
                    (BODY_X0 + WALL, BODY_X1 - WALL), (-BODY_Z + WALL, BODY_Z - WALL))
    boolean_cut(body, cav)
    # 后进风真孔（后壁 2mm 贯通）
    in_x0, in_x1 = INTAKE["x0"], INTAKE["x1"]
    boolean_cut(body, box("cutter_intake", (in_x1 - in_x0, 0.010, INTAKE["z1"] - INTAKE["z0"]),
                          ((in_x0 + in_x1) / 2, BODY_Y0 + WALL / 2, 0), bevel=0.004))
    # 右侧热排真孔 + 左侧辅助进风真孔（±Z 壁贯通）
    for side, vent, sz in (("R", HOTVENT, 1.0), ("L", AUXVENT, -1.0)):
        vx = (vent["x0"] + vent["x1"]) / 2
        vy = (vent["y0"] + vent["y1"]) / 2
        boolean_cut(body, box("cutter_hv_" + side,
                              (vent["x1"] - vent["x0"], vent["y1"] - vent["y0"], 0.012),
                              (vx, vy, sz * (BODY_Z - 0.004)), bevel=0.004))
    # 旋扣槽×3（顶壁/左右壁前缘贯通槽 10×10mm，IF-3 母口）
    boolean_cut(body, box("cutter_lock_t", (0.010, 0.012, 0.010), (0.1549, 0.051, 0)))
    for sz in (1.0, -1.0):
        boolean_cut(body, box("cutter_lock_s", (0.010, 0.012, 0.010), (0.086, 0.051, sz * 0.1089)))
    parts.append(body)
    # ---- 前壳 FrontPanel：2mm 板（拔模锥台+圆角），出风槽/数显窗真孔，0.5mm 分件缝 ----
    panel = frustum_y("FrontPanel", BODY_Y1, BODY_Y1 + WALL,
                      (0.017, 0.155), (-0.107, 0.107),
                      (0.0175, 0.1545), (-0.1065, 0.1065), mat=m["BodyIvory"])
    apply_bevel(panel, 0.008, seg=4)
    slot = box("cutter_slot", (OUTLET["x1"] - OUTLET["x0"], 0.008, 2 * (-OUTLET["z"])),
               ((OUTLET["x0"] + OUTLET["x1"]) / 2, BODY_Y1 + WALL / 2, 0), bevel=0.005)
    boolean_cut(panel, slot)
    dw = box("cutter_disp", (DISP["x1"] - DISP["x0"], 0.008, DISP["z1"] - DISP["z0"]),
             ((DISP["x0"] + DISP["x1"]) / 2, BODY_Y1 + WALL / 2, (DISP["z0"] + DISP["z1"]) / 2),
             bevel=0.003)
    boolean_cut(panel, dw)
    parts.append(panel)
    # ---- 旋扣×3（前壳背面 L 钩，钩片 12mm>槽 10mm，已旋转 15° 的锁止态，IF-3） ----
    locks = []
    st = box("lk_stem_t", (0.002, 0.005, 0.003), (0.1549, BODY_Y1 - 0.0025, 0), mat=m["BodyIvory"])
    tb = box("lk_tab_t", (0.002, 0.0016, 0.012), (0.1549, BODY_Y1 - 0.0055, 0), mat=m["BodyIvory"])
    tb.rotation_euler = (0, math.radians(15), 0)
    locks += [st, tb]
    for sz in (1.0, -1.0):
        st = box("lk_stem_s", (0.003, 0.005, 0.002), (0.086, BODY_Y1 - 0.0025, sz * 0.1089), mat=m["BodyIvory"])
        tb = box("lk_tab_s", (0.012, 0.0016, 0.002), (0.086, BODY_Y1 - 0.0055, sz * 0.1089), mat=m["BodyIvory"])
        tb.rotation_euler = (0, math.radians(15), 0)
        locks += [st, tb]
    parts.append(join_parts("M6_TwistLock", locks))
    # ---- 进风/热排格栅条（真孔内的横/竖条，条间为真实开口） ----
    bars = []
    for i in range(INTAKE["bars"]):
        xx = in_x0 + (i + 0.5) * (in_x1 - in_x0) / INTAKE["bars"]
        bars.append(box("in_%d" % i, (0.0038, 0.0018, INTAKE["z1"] - INTAKE["z0"] - 0.004),
                        (xx, BODY_Y0 + WALL / 2, 0), mat=m["Grid"]))
    parts.append(join_parts("IntakeGrille", bars))
    for side, vent, sz in (("R", HOTVENT, 1.0), ("L", AUXVENT, -1.0)):
        slats = []
        for i in range(vent["bars"]):
            yy = vent["y0"] + (i + 0.5) * (vent["y1"] - vent["y0"]) / vent["bars"]
            slats.append(box("hv_%s_%d" % (side, i),
                             (vent["x1"] - vent["x0"] - 0.006, 0.0032, 0.0018),
                             ((vent["x0"] + vent["x1"]) / 2, yy, sz * (BODY_Z - 0.0035)),
                             mat=m["Grid"]))
        parts.append(join_parts("HotVent_" + side, slats))
    # ---- 导风板×3：叶片 + 左轴承短轴 + 右联动长轴 + 曲柄盘/销（pivot 轴沿 Z，LOUVER_Y，下倾15°） ----
    for i, xx in enumerate(LOUVER_X):
        lv = [box("lv_blade", (0.013, 0.0022, 0.178), (xx, LOUVER_Y, -0.005),
                  mat=m["BodyIvory"], bevel=0.001),
              cyl("lv_stub", 0.0025, 0.006, (xx, LOUVER_Y, -0.097),
                  mat=m["BodyIvory"]),
              cyl("lv_shaft", 0.002, 0.014, (xx, LOUVER_Y, 0.090),
                  mat=m["BodyIvory"]),
              cyl("lv_crank", 0.004, 0.003, (xx, LOUVER_Y, 0.0915),
                  mat=m["BodyIvory"]),
              cyl("lv_pin", 0.0012, 0.004, (xx, LOUVER_Y - 0.005, 0.0915),
                  mat=m["CellSteel"])]
        # 叶片下倾 15°（绕 Z 轴，前缘下压）；轴/曲柄保持轴线姿态
        lv[0].rotation_euler = (0, 0, math.radians(15))
        parts.append(join_parts("Louver_%d" % i, lv))
    # ---- 联动杆（3 曲柄销同动，M1_Link） ----
    parts.append(box("M1_Link", (0.050, 0.0016, 0.004),
                     (LOUVER_X[1], LOUVER_Y - 0.005, 0.0915), mat=m["CellSteel"], bevel=0.0008))
    # ---- 数显：窗孔内 PMMA 玻璃 + 数码管字形 + 卡扣×4 + 遮光筋（IF-4） ----
    glass = box("DisplayGlass", (0.030, 0.0015, 0.056),
                (0.118, BODY_Y1 - 0.0008, 0.072), mat=m["GlassDark"], bevel=0.003)
    parts.append(glass)
    parts.append(build_display_text("22.0", 0.118, BODY_Y1 - 0.0024, 0.072, m["DigitGlow"]))
    clips = []
    # 遮光筋：窗孔背面整圈筋（高3mm）
    dx0, dx1, dz0, dz1 = DISP["x0"] - 0.002, DISP["x1"] + 0.002, DISP["z0"] - 0.002, DISP["z1"] + 0.002
    cxm, czm = (dx0 + dx1) / 2, (dz0 + dz1) / 2
    clips.append(box("rib_x0", (0.0012, 0.003, dz1 - dz0), (dx0, BODY_Y1 - 0.0015, czm), mat=m["BodyIvory"]))
    clips.append(box("rib_x1", (0.0012, 0.003, dz1 - dz0), (dx1, BODY_Y1 - 0.0015, czm), mat=m["BodyIvory"]))
    clips.append(box("rib_z0", (dx1 - dx0, 0.003, 0.0012), (cxm, BODY_Y1 - 0.0015, dz0), mat=m["BodyIvory"]))
    clips.append(box("rib_z1", (dx1 - dx0, 0.003, 0.0012), (cxm, BODY_Y1 - 0.0015, dz1), mat=m["BodyIvory"]))
    # 卡扣×4（咬住玻璃背缘的斜钩）
    for hx in (dx0 + 0.001, dx1 - 0.001):
        for hz in (czm - 0.018, czm + 0.018):
            clips.append(box("clip", (0.002, 0.0026, 0.004), (hx, BODY_Y1 - 0.0013, hz),
                             mat=m["BodyIvory"], bevel=0.0005))
    parts.append(join_parts("M7_Clip", clips))
    parts.append(box("M7_Module", (0.026, 0.006, 0.050), (0.118, BODY_Y1 - 0.0065, 0.072),
                     mat=m["ICBlack"], bevel=0.0015))
    # ---- 底座：滑板座 + 配重腔 + 3×(Ø2.5 通孔 + Ø5 沉孔) + 防滑圈 + Type-C ----
    base = box("Base", (0.016, 0.118, 0.228), (0.008, 0, 0), mat=m["BodyIvory"])
    apply_bevel(base, 0.006, seg=4)
    # 配重腔：顶面开口（朝机身内），4mm 底 / 6mm 壁，装配后灌铅砂/钢珠 + 环氧封口
    boolean_cut(base, box("cutter_weight", (0.013, 0.106, 0.216), (0.0105, 0, 0)))
    BOSS_AT = [(0.035, 0.080), (0.035, -0.080), (-0.040, 0.0)]
    for i, (by, bz) in enumerate(BOSS_AT):
        boolean_cut(base, cyl("cutter_screw_%d" % i, 0.00125, 0.020, (0.008, by, bz), rot=(0, math.pi / 2, 0)))
        boolean_cut(base, cyl("cutter_sink_%d" % i, 0.0025, 0.004, (0.002, by, bz), rot=(0, math.pi / 2, 0)))
    parts.append(base)
    bosses = []
    for i, (by, bz) in enumerate(BOSS_AT):
        bo = cyl("boss_%d" % i, 0.004, 0.018, (0.027, by, bz), rot=(0, math.pi / 2, 0), mat=m["BodyIvory"])
        # 盲孔：柱顶留 4mm 咬合料，螺钉从底座穿入柱体 12mm
        boolean_cut(bo, cyl("cutter_boss_%d" % i, 0.00125, 0.012, (0.024, by, bz), rot=(0, math.pi / 2, 0)))
        bosses.append(bo)
    parts.append(join_parts("M1_Bosses", bosses))
    skid = box("SkidPad", (0.004, 0.104, 0.212), (-0.001, 0, 0),
               mat=m["FrameDark"], bevel=0.002)
    for i, (by, bz) in enumerate(BOSS_AT):       # 硅胶垫让位螺丝沉孔（Ø8 开孔）
        boolean_cut(skid, cyl("cutter_skid_%d" % i, 0.004, 0.008, (0.0, by, bz), rot=(0, math.pi / 2, 0)))
    parts.append(skid)
    parts.append(box("TypeC", (0.005, 0.003, 0.011), (0.008, -0.0585, 0),
                     mat=m["VoidDark"], bevel=0.0015))
    # ---- 腰线（外观分模线环带，沿用概念；套在机身上，四周 0.4mm 装配间隙） ----
    band = box("Band", (0.004, 0.114, 0.224), (0.030, 0, 0),
               mat=m["BandMint"], bevel=0.0018)
    # 环带化：按机身截面抽芯（该站位机身 y[-0.055,0.0512] z[±0.1097] + 0.4mm/侧间隙）
    boolean_cut(band, box("cutter_band", (0.006, 0.1070, 0.2202), (0.030, -0.0019, 0)))
    parts.append(band)
    # ---- 顶部旋钮 + 制冷键（贴合拔模后的顶面） ----
    def top_x_at(yy):
        return (BODY_X1 - dx) + dx * ((yy - BODY_Y0) / (BODY_Y1 - BODY_Y0))
    kx = top_x_at(0.004)
    knob = cyl("Knob", 0.016, 0.010, (kx + 0.004, 0.004, 0.062), rot=(0, math.pi / 2, 0), mat=m["FrameDark"])
    cap = cyl("KnobCap", 0.0131, 0.002, (kx + 0.009, 0.004, 0.062), rot=(0, math.pi / 2, 0), mat=m["Aluminum"])
    mark = box("KnobMark", (0.0012, 0.009, 0.0022), (kx + 0.010, -0.004, 0.062), mat=m["VoidDark"])
    parts.append(join_parts("KnobAsm", [knob, cap, mark]))
    ck = cyl("CoolKey", 0.007, 0.005, (top_x_at(0.006) + 0.0015, 0.006, 0.012),
             rot=(0, math.pi / 2, 0), mat=m["FrameDark"])
    ck_dot = cyl("CoolKeyDot", 0.0032, 0.0015, (top_x_at(0.006) + 0.004, 0.006, 0.012),
                 rot=(0, math.pi / 2, 0), mat=m["BandMint"])
    parts.append(join_parts("CoolKeyAsm", [ck, ck_dot]))
    parts[-2].name = "Knob"
    parts[-1].name = "CoolKey"
    return parts

# ================= 内部核心（风道真实化 + 密封 + 齿轮联动） =================
def build_core(m):
    parts = []
    TX = 0.082          # TEC 三明治 X 中心（对齐右侧热排孔）
    # ---- M5 热模块：TEC 40×40×3.8（冷面 -Z / 热面 +Z，法线 Z） ----
    parts.append(box("M5_TEC", (0.040, 0.040, 0.0038), (TX, 0.012, 0.0019),
                     mat=m["TEC"], bevel=0.0006))
    # 冷端：基板 40×40×4（z -0.004..0）+ 8 鳍（板法线 Z，风道沿 Y 贯通）
    cf = [box("cf_base", (0.040, 0.040, 0.004), (TX, 0.012, -0.002), mat=m["AluFin"])]
    for i in range(8):
        z = -0.0355 + i * 0.0044
        cf.append(box("cf_%d" % i, (0.040, 0.036, 0.001), (TX, 0.012, z), mat=m["AluFin"]))
    parts.append(join_parts("M5_ColdFins", cf))
    # 热端：基板（z 0.0038..0.0078）+ 9 鳍（板法线 Z，鳍片通道沿 Z 朝右侧热排）
    hs = [box("hs_base", (0.040, 0.040, 0.004), (TX, 0.012, 0.0058), mat=m["Copper"])]
    for i in range(9):
        z = 0.0145 + i * 0.0103
        hs.append(box("hs_%d" % i, (0.040, 0.036, 0.0012), (TX, 0.012, z), mat=m["Copper"]))
    parts.append(join_parts("M5_HotSink", hs))
    # ---- L 形全风道中隔板（ADR-1）：主板(X-Y@z=0.002, y -0.053..0.0368) + 前横板(X-Z@y=0.036) ----
    # 边缘密封肋（加厚到 5mm，开 3mm 宽 ×1.5mm 深 EVA 槽，IF-2）
    sep = [box("sep_main", (0.136, 0.0898, 0.0016), (0.086, -0.0081, 0.002), mat=m["SepBoard"]),
           box("sep_cross", (0.136, 0.0016, 0.106), (0.086, 0.036, 0.055), mat=m["SepBoard"])]
    ribs = [
        # (名字, 尺寸, 中心, 槽口 cutter 尺寸, 槽口中心) — 槽 3mm 宽 ×1.5mm 深，开在与外壳接触的肋面
        ("rib_mt", (0.006, 0.0898, 0.005), (0.1505, -0.0081, 0.002),    # 主板顶边（肋面 x=0.1535）
         (0.002, 0.0898, 0.003), (0.153, -0.0081, 0.002)),
        ("rib_mb", (0.006, 0.0898, 0.005), (0.0215, -0.0081, 0.002),    # 主板底边（肋面 x=0.0185）
         (0.002, 0.0898, 0.003), (0.019, -0.0081, 0.002)),
        ("rib_mk", (0.136, 0.006, 0.005), (0.086, -0.0505, 0.002),      # 主板后边（肋面 y=-0.0535）
         (0.136, 0.002, 0.003), (0.086, -0.053, 0.002)),
        ("rib_ct", (0.006, 0.0016, 0.106), (0.1505, 0.036, 0.055),      # 横板顶边
         (0.002, 0.0016, 0.106), (0.153, 0.036, 0.055)),
        ("rib_cb", (0.006, 0.0016, 0.106), (0.0215, 0.036, 0.055),      # 横板底边
         (0.002, 0.0016, 0.106), (0.019, 0.036, 0.055)),
        ("rib_cr", (0.136, 0.005, 0.006), (0.086, 0.036, 0.1045),       # 横板右边（肋面 z=0.1075）
         (0.136, 0.003, 0.002), (0.086, 0.036, 0.107)),
    ]
    eva = []
    for nm, rs, rc, gs, gc in ribs:
        rib = box(nm, rs, rc, mat=m["SepBoard"])
        boolean_cut(rib, box("g_" + nm, gs, gc))
        sep.append(rib)
        # EVA 棉条：嵌槽内、外凸 ~0.5mm（与壳体内壁压缩量示意）
        eva.append(box("eva_" + nm,
                       (gs[0] - 0.0006, gs[1] - 0.0006, gs[2] - 0.0006),
                       (gc[0] + (0.0005 if gc[0] > 0.1 else (-0.0005 if gc[0] < 0.05 else 0)),
                        gc[1] + (-0.0005 if gc[1] < -0.05 else 0),
                        gc[2] + (0.0005 if gc[2] > 0.1 else 0)),
                       mat=m["EVA"]))
    sepall = join_parts("M5_Separator", sep)
    # TEC 窗（冷/热基板穿过，2mm 间隙）
    boolean_cut(sepall, box("cutter_sepwin", (0.044, 0.044, 0.020), (TX, 0.012, 0.002)))
    # 步进电机仓豁口（横板右上，电机穿仓）
    boolean_cut(sepall, box("cutter_motor", (0.034, 0.010, 0.030), (0.065, 0.036, 0.098)))
    parts.append(sepall)
    parts.append(join_parts("M5_EVA", eva))
    # ---- 冷风道（M5_ColdDuct）：底板 + 顶板斜切(全高进风静压腔→出风口收缩) + 左右侧板 = 贯通腔 ----
    duct = [box("duct_floor", (0.002, 0.029, 0.196), (0.035, 0.0385, 0), mat=m["DuctWall"]),
            box("duct_sideL", (0.119, 0.029, 0.002), (0.0945, 0.0385, -0.097), mat=m["DuctWall"]),
            box("duct_sideR", (0.119, 0.017, 0.002), (0.0945, 0.0445, 0.087), mat=m["DuctWall"])]
    ceil = box("duct_ceil", (0.0735, 0.0016, 0.196), (0.1235, 0.0325, 0), mat=m["DuctWall"])
    ceil.rotation_euler = (0, 0, math.radians(146.2))     # 顶板从 x=0.154@y=0.012 斜到 x=0.093@y=0.053
    duct.append(ceil)
    sidel, sider = duct[1], duct[2]
    for xx in LOUVER_X:                                    # 左/右侧板开导风板轴承孔 ×3（轴沿 Z）
        boolean_cut(sidel, cyl("cutter_stub", 0.003, 0.006, (xx, LOUVER_Y, -0.097)))
        boolean_cut(sider, cyl("cutter_shaft", 0.0025, 0.006, (xx, LOUVER_Y, 0.087)))
    parts.append(join_parts("M5_ColdDuct", duct))
    # ---- 热风道导流板（M5_HotDuct）：热鳍出风口 → 右侧热排孔的两侧挡板 ----
    hd = [box("hd_a", (0.048, 0.0016, 0.057), (0.082, -0.0088, 0.0785), mat=m["DuctWall"]),
          box("hd_b", (0.048, 0.0016, 0.057), (0.082, 0.0325, 0.0785), mat=m["DuctWall"])]
    parts.append(join_parts("M5_HotDuct", hd))
    # ---- M4 动力：Ø80 轴流无刷风机（轴沿 Y，向 +Y 吹，后进风静压腔内） ----
    fc = (0.085, -0.010, -0.030)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0385, minor_radius=0.0022,
                                     major_segments=48, minor_segments=12, location=fc)
    frame = bpy.context.active_object
    frame.name = "M4_FanFrame"
    frame.rotation_euler = (math.pi / 2, 0, 0)
    frame.data.materials.append(m["FanDark"])
    parts.append(frame)
    parts.append(cyl("M4_FanHub", 0.012, 0.020, fc, rot=(math.pi / 2, 0, 0), mat=m["FanDark"]))
    blades = []
    for i in range(7):
        a = i * 2 * math.pi / 7
        r = 0.0255
        bl = box("bl_%d" % i, (0.026, 0.0028, 0.015),
                 (fc[0] + r * math.cos(a), fc[1], fc[2] + r * math.sin(a)), mat=m["BladeDark"])
        bl.rotation_euler = (0.55, -a, 0.0)
        blades.append(bl)
    parts.append(join_parts("M4_FanBlades", blades))
    # ---- M2 能源：2×18650（沿 Z 躺放）+ 电池仓（防反插键位+减震筋, IF-5） ----
    for tag, yy in (("A", -0.012), ("B", 0.010)):
        cell = [cyl("cell_%s" % tag, 0.009, 0.065, (0.029, yy, -0.062),
                    mat=m["CellWrap"]),
                cyl("cellcap_%s" % tag, 0.0085, 0.0015, (0.029, yy, -0.0288),
                    mat=m["CellSteel"])]
        parts.append(join_parts("M2_Cell_%s" % tag, cell))
    br = [box("br_tray", (0.002, 0.048, 0.072), (0.019, -0.002, -0.062), mat=m["Bracket"]),
          box("br_end1", (0.022, 0.048, 0.003), (0.029, -0.002, -0.0965), mat=m["Bracket"]),
          box("br_end2", (0.022, 0.048, 0.003), (0.029, -0.002, -0.0275), mat=m["Bracket"]),
          box("br_side1", (0.022, 0.002, 0.072), (0.029, -0.025, -0.062), mat=m["Bracket"]),
          box("br_side2", (0.022, 0.002, 0.072), (0.029, 0.021, -0.062), mat=m["Bracket"]),
          # 防反插：端壁单侧键位凸台（不对称）+ 偏心 JST 座
          box("br_key", (0.004, 0.008, 0.006), (0.038, 0.017, -0.029), mat=m["Bracket"]),
          box("br_jst", (0.008, 0.008, 0.006), (0.034, -0.004, -0.024), mat=m["ICBlack"]),
          # 减震筋 ×3（两侧壁+仓底 EVA 凸筋，与电芯 0.5mm 压缩量）
          box("br_r1", (0.016, 0.0025, 0.060), (0.029, -0.02275, -0.062), mat=m["EVA"]),
          box("br_r2", (0.016, 0.0012, 0.060), (0.029, 0.0194, -0.062), mat=m["EVA"]),
          box("br_r3", (0.001, 0.040, 0.060), (0.0205, -0.002, -0.062), mat=m["EVA"]),
          # BMS 保护板
          box("br_bms", (0.018, 0.030, 0.0016), (0.029, -0.002, -0.0245), mat=m["PCBGreen"])]
    parts.append(join_parts("M2_Bracket", br))
    # ---- M3 主控：PCB（冷侧进风后方立板）+ IC + 旋钮电位器 ----
    parts.append(box("M3_PCB", (0.060, 0.0016, 0.060), (0.115, -0.046, -0.055),
                     mat=m["PCBGreen"], bevel=0.002))
    ics = [box("ic_mcu", (0.012, 0.002, 0.012), (0.125, -0.0443, -0.070), mat=m["ICBlack"]),
           box("ic_drv", (0.010, 0.002, 0.010), (0.105, -0.0443, -0.040), mat=m["ICBlack"]),
           box("ic_chg", (0.008, 0.002, 0.008), (0.095, -0.0443, -0.070), mat=m["ICBlack"]),
           box("ic_usbc", (0.006, 0.003, 0.010), (0.090, -0.0445, -0.030), mat=m["CellSteel"])]
    parts.append(join_parts("M3_ICs", ics))
    pot = [cyl("pot_body", 0.0085, 0.012, (0.146, 0.004, 0.062), rot=(0, math.pi / 2, 0), mat=m["FanDark"]),
           cyl("pot_shaft", 0.003, 0.012, (0.155, 0.004, 0.062), rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
    parts.append(join_parts("M3_Pot", pot))
    # ---- M1 导风机构：28BYJ-48（轴沿 Z，电机仓 z 0.0885..0.1075）+ m0.8 齿轮副 + 扇形齿轮 ----
    parts.append(cyl("M1_Stepper", 0.014, 0.019, (0.064, 0.034, 0.098),
                     mat=m["StepperBlue"]))
    pinion, rp1 = gear_mesh("M1_Pinion", 12, 0.0008, 0.003, (0.064, 0.034, GEAR_Z), mat=m["GearPOM"])
    hub1 = cyl("pin_hub", 0.0025, 0.004, (0.064, 0.034, GEAR_Z), mat=m["GearPOM"])
    parts.append(join_parts("M1_PinionAsm", [pinion, hub1]))
    parts[-1].name = "M1_Pinion"
    # 扇形齿轮：18T 当量，出齿弧对准 -Y 的小齿轮（中心距 12.0mm = R4.8+R7.2）
    sector, rp2 = gear_mesh("M1_Sector", 18, 0.0008, 0.003, (0.064, LOUVER_Y, GEAR_Z),
                            arc=(math.radians(200), math.radians(340)), mat=m["GearPOM"])
    # arc 参数按 X-Y 平面角度（+X 起算）：小齿轮在扇齿 -Y 方向 = 270°
    hub2 = cyl("sec_hub", 0.004, 0.007, (0.064, LOUVER_Y, 0.0945), mat=m["GearPOM"])
    parts.append(join_parts("M1_SectorAsm", [sector, hub2]))
    parts[-1].name = "M1_Sector"
    assert abs(rp1 + rp2 - 0.012) < 1e-9, "齿轮中心距错误"
    return parts

# ================= 爆炸向量 / GLB 核验（同 build_core.py） =================
def part_centroid(obj):
    return obj.matrix_world.translation.copy()

def explode_vec(name, obj):
    if name in EXPLODE:
        d, mag = EXPLODE[name]
        return Vector(d) * mag
    c = part_centroid(obj) - CENTER
    ax = max(range(3), key=lambda i: abs(c[i]))
    dom = Vector((0, 0, 0))
    dom[ax] = 1.0 if c[ax] >= 0 else -1.0
    mag = 0.04 + 0.8 * abs(c[ax])
    return dom * mag

def to_gltf(v):
    return [v.x, v.z, -v.y]

def verify_glb(path):
    with open(path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", "not a GLB"
        clen, ctype = struct.unpack("<II", f.read(8))
        gltf = json.loads(f.read(clen).decode("utf-8"))
    nodes = gltf.get("nodes", [])
    named = [(n.get("name", "?"), "explode" in (n.get("extras") or {})) for n in nodes]
    print("GLB NODES (%d):" % len(named))
    miss = []
    for nm, has_ex in sorted(named):
        print("  - %s%s" % (nm, "" if has_ex else "  [NO extras]"))
        if not has_ex:
            miss.append(nm)
    print("GLB extras missing:", miss if miss else "none")
    return [nm for nm, _ in named]

# ================= 场景 =================
def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 480 if FAST else 800
    scene.render.resolution_y = 360 if FAST else 600
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.exposure = 0.4
    try:
        scene.eevee.taa_render_samples = 16 if FAST else 64
    except Exception:
        pass
    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 0.6

    TARGET = Vector((0.086, 0.0, 0.0))

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
    add_area("KeyLight", (0.35, 0.40, 0.35), 4.0)
    add_area("FillLight", (0.10, -0.15, -0.55), 1.5)
    add_area("RimLight", (0.45, -0.45, 0.25), 2.5)
    return scene

def make_mats():
    return {
        "BodyIvory":  new_mat("BodyIvory", (0.949, 0.937, 0.914, 1), 0.0, 0.45),
        "Aluminum":   new_mat("Aluminum", (0.82, 0.84, 0.87, 1), 1.0, 0.22),
        "Grid":       new_mat("Grid", (0.06, 0.063, 0.068, 1), 0.2, 0.55),
        "FrameDark":  new_mat("FrameDark", (0.06, 0.063, 0.068, 1), 0.3, 0.45),
        "VoidDark":   new_mat("VoidDark", (0.05, 0.05, 0.06, 1), 0.0, 0.8),
        "BandMint":   new_mat("BandMint", (0.45, 0.78, 0.62, 1), 0.0, 0.42,
                              emission=(0.45, 0.78, 0.62, 1), emission_strength=0.5),
        "GlassDark":  new_mat("GlassDark", (0.008, 0.012, 0.018, 1), 0.4, 0.18),
        "DigitGlow":  new_mat("DigitGlow", (0.02, 0.05, 0.10, 1), 0.0, 0.3,
                              emission=(0.15, 0.70, 1.0, 1), emission_strength=5.0),
        "TEC":        new_mat("TEC", (0.94, 0.94, 0.92, 1), 0.0, 0.35),
        "AluFin":     new_mat("AluFin", (0.85, 0.87, 0.90, 1), 1.0, 0.25),
        "Copper":     new_mat("Copper", (0.72, 0.42, 0.24, 1), 1.0, 0.30),
        "SepBoard":   new_mat("SepBoard", (0.88, 0.86, 0.78, 1), 0.0, 0.6),
        "EVA":        new_mat("EVA", (0.12, 0.12, 0.13, 1), 0.0, 0.9),
        "DuctWall":   new_mat("DuctWall", (0.80, 0.82, 0.78, 1), 0.0, 0.55),
        "FanDark":    new_mat("FanDark", (0.10, 0.10, 0.11, 1), 0.2, 0.5),
        "BladeDark":  new_mat("BladeDark", (0.16, 0.17, 0.19, 1), 0.1, 0.45),
        "CellSteel":  new_mat("CellSteel", (0.62, 0.66, 0.70, 1), 1.0, 0.28),
        "CellWrap":   new_mat("CellWrap", (0.18, 0.44, 0.62, 1), 0.1, 0.45),
        "Bracket":    new_mat("Bracket", (0.25, 0.50, 0.38, 1), 0.0, 0.6),
        "PCBGreen":   new_mat("PCBGreen", (0.04, 0.32, 0.14, 1), 0.1, 0.5),
        "ICBlack":    new_mat("ICBlack", (0.06, 0.06, 0.07, 1), 0.3, 0.4),
        "StepperBlue": new_mat("StepperBlue", (0.16, 0.32, 0.68, 1), 0.6, 0.35),
        "GearPOM":    new_mat("GearPOM", (0.92, 0.90, 0.82, 1), 0.0, 0.35),
    }

# ================= 主流程 =================
def main():
    scene = setup_scene()
    m = make_mats()
    shell = build_shell(m)
    core = build_core(m)

    meta = dict(SHELL_META)
    meta.update(CORE_META)
    records = []
    for o in bpy.data.objects:
        if o.type != "MESH" or o.name not in meta:
            continue
        mod, label = meta[o.name]
        v = explode_vec(o.name, o)
        o["module"] = mod
        o["label"] = label
        o["explode"] = to_gltf(v)
        records.append({"name": o.name, "module": mod, "label": label, "explode": to_gltf(v)})
    names_found = {r["name"] for r in records}
    assert names_found == set(meta.keys()), "零件名对不上: %s" % (set(meta.keys()) ^ names_found)
    with open(PARTS_JSON, "w", encoding="utf-8") as f:
        json.dump({"glb": "cad/assembly_a_eng.glb", "parts": records}, f, ensure_ascii=False, indent=1)
    print("PARTS JSON:", PARTS_JSON, "(%d parts)" % len(records))

    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=GLB_OUT, export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=False, export_extras=True)
    print("GLB EXPORTED:", GLB_OUT)
    verify_glb(GLB_OUT)

    # ---- 渲染 1：装配态（半透壳 + 双风道箭头） ----
    os.makedirs(RENDER_DIR, exist_ok=True)
    trans_mats = {}
    for nm in ("Body", "FrontPanel", "Base"):
        ob = bpy.data.objects[nm]
        src = ob.data.materials[0]
        tm = src.copy()
        tm.name = src.name + "_Ghost"
        bsdf = tm.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Alpha"].default_value = 0.12
        try:
            tm.surface_render_method = "DITHERED"
        except Exception:
            try:
                tm.blend_method = "BLEND"
            except Exception:
                pass
        ob.data.materials[0] = tm
        trans_mats[nm] = src
    arrow_cold = arrow("Airflow_Cold", (0.082, -0.075, -0.020), (0.082, 0.085, -0.020),
                       new_mat("AirCold", (0.10, 0.55, 0.95, 1), 0.0, 0.4,
                               emission=(0.10, 0.55, 0.95, 1), emission_strength=1.5))
    ah = new_mat("AirHot", (0.95, 0.30, 0.12, 1), 0.0, 0.4,
                 emission=(0.95, 0.30, 0.12, 1), emission_strength=1.5)
    arrow_h1 = arrow("Airflow_Hot_in", (0.082, -0.075, 0.050), (0.082, -0.002, 0.050), ah)
    arrow_h2 = arrow("Airflow_Hot_out", (0.082, 0.012, 0.060), (0.082, 0.012, 0.145), ah)
    arrows = [arrow_cold, arrow_h1, arrow_h2]

    TARGET = Vector((0.086, 0.0, 0.0))

    def shoot(name, loc, target):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.data.lens = 55
        fwd = (Vector(target) - Vector(loc)).normalized()
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
        scene.camera = cam
        scene.render.filepath = os.path.join(RENDER_DIR, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED:", scene.render.filepath)
        bpy.data.objects.remove(cam, do_unlink=True)

    shoot("assembled", (0.34, 0.38, 0.40), TARGET)

    if os.environ.get("INSPECT") == "1":
        # 检查视角：半透后视（看进风真孔/隔板/热风道）+ 半透右侧（看热排/电机仓/齿轮）
        shoot("inspect_back", (0.30, -0.42, -0.30), TARGET)
        shoot("inspect_right", (0.30, 0.05, 0.55), TARGET)
        # 半透特写：齿轮啮合（电机仓）+ 隔板 EVA 槽 + 风道内部
        shoot("inspect_gear", (0.02, 0.16, 0.30), (0.064, 0.040, 0.095))
        shoot("inspect_gear_zoom", (0.064, 0.14, 0.22), (0.064, 0.040, 0.0955))
        shoot("inspect_duct", (0.30, 0.30, -0.35), (0.070, 0.010, -0.010))
        # 恢复不透明材质，拍外观/特写（验证真孔与 DFM 特征可读）
        for nm, src in trans_mats.items():
            bpy.data.objects[nm].data.materials[0] = src
        for a in arrows:
            a.hide_render = True
        scene.view_settings.exposure = 0.1
        shoot("inspect_ext_front", (0.086, 0.55, 0.10), TARGET)
        shoot("inspect_ext_back", (0.086, -0.55, 0.0), TARGET)
        shoot("inspect_ext_right", (0.086, 0.05, 0.60), TARGET)
        shoot("inspect_front_close", (0.064, 0.28, 0.02), (0.064, 0.040, 0.0))
        shoot("inspect_disp_close", (0.118, 0.28, 0.10), (0.118, 0.055, 0.072))
        shoot("inspect_base_bottom", (-0.30, 0.10, 0.15), (0.010, 0.0, 0.0))
        print("INSPECT DONE")
        return

    # ---- 渲染 2：爆炸态 ----
    for a in arrows:
        a.hide_render = True
    moved = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name in meta:
            v = explode_vec(o.name, o)
            o.location += v
            moved.append((o, v))
    shoot("exploded", (0.60, 0.68, 0.76), (0.10, 0.0, 0.0))
    for o, v in moved:
        o.location -= v
    print("ALL DONE")

main()
