"""
LiteCool S1 — 形态 A 工程装配体（内部核心 + 外壳）+ 爆炸视图数据 + 验收渲染
用法: blender --background --python build_core.py
输入: form_a.blend（build_form_a.py FAST=0 产出；外壳件原样复用，不改 build_form_a.py）
输出:
  cad/assembly_a.glb        — 外壳件 + 内部件全命名 mesh，node extras 带 module/label/explode(向量, glTF 坐标系)
  cad/assembly_a_parts.json — 工作台④数据源（零件→模块/中文名/爆炸向量）
  cad/renders_assembly/{assembled,exploded}.png — 装配态(半透明壳+风道箭头) / 爆炸态
坐标约定（同 build_form_a.py）: X=高度, Y=前后(前=+Y), Z=左右(右=+Z)
布局依据: architecture/product-architecture.md §3.2 双风道 + §5.2 层叠（适配方向 A 横向布局:
          冷风道 后进风→风机→冷鳍→前出风口; 热风道 后进风→热端散热器→右侧/后排出）
"""
import bpy
import math
import mathutils
import os
import json
import struct
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(BASE_DIR, "form_a.blend")
GLB_OUT = os.path.join(BASE_DIR, "assembly_a.glb")
PARTS_JSON = os.path.join(BASE_DIR, "assembly_a_parts.json")
RENDER_DIR = os.path.join(BASE_DIR, "renders_assembly")

# ================= 工具（与 build_form_a.py 同风格） =================
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

def arrow(name, p0, p1, mat, shaft_r=0.0035, head_r=0.009, head_l=0.022):
    """圆柱+锥头箭头，p0→p1（仅渲染用，不进 GLB）"""
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

# ================= 零件注册表 =================
# name → (module, label)；内部件在下方构建，外壳件名来自 form_a.blend
SHELL_META = {
    "Base":           ("M1", "配重滑板底座"),
    "SkidPad":        ("M1", "防滑硅胶圈"),
    "TypeC":          ("M1", "Type-C 进线口"),
    "Body":           ("M6", "主机壳(后壳)"),
    "FrontPanel":     ("M6", "前壳面板"),
    "Band":           ("M6", "薄荷腰线(分模线)"),
    "OutletCavity":   ("M5", "冷风道出风腔"),
    "Louver_0":       ("M6", "导风板 1"),
    "Louver_1":       ("M6", "导风板 2"),
    "Louver_2":       ("M6", "导风板 3"),
    "Display":        ("M7", "数码管字形 22.0"),
    "DisplayGlass":   ("M7", "半透数显窗"),
    "HotVent_L":      ("M5", "热风道排格栅(左)"),
    "HotVent_R":      ("M5", "热风道排格栅(右)"),
    "HotVentCavity_L": ("M5", "热排腔(左)"),
    "HotVentCavity_R": ("M5", "热排腔(右)"),
    "IntakeGrille":   ("M5", "后进风格栅"),
    "IntakeCavity":   ("M5", "进风腔"),
    "Knob":           ("M3", "旋钮(100档FOC)"),
    "CoolKey":        ("M3", "制冷键"),
}
CORE_META = {
    "M5_TEC":        ("M5", "TEC 制冷片 40×40×3.8"),
    "M5_ColdFins":   ("M5", "冷端铝鳍片组"),
    "M5_HotSink":    ("M5", "热端散热器(带鳍片)"),
    "M5_Separator":  ("M5", "冷热风道中隔板"),
    "M4_FanFrame":   ("M4", "风机框 Ø80"),
    "M4_FanHub":     ("M4", "轮毂+无刷电机"),
    "M4_FanBlades":  ("M4", "扇叶 ×7"),
    "M2_Cell_A":     ("M2", "18650 电芯 A"),
    "M2_Cell_B":     ("M2", "18650 电芯 B"),
    "M2_Bracket":    ("M2", "电池支架+保护板"),
    "M3_PCB":        ("M3", "主控 PCB"),
    "M3_ICs":        ("M3", "主要 IC(MCU/驱动/充电)"),
    "M3_Pot":        ("M3", "旋钮电位器"),
    "M1_Stepper":    ("M1", "28BYJ-48 步进电机"),
    "M1_Link":       ("M1", "导风板联动杆"),
    "M7_Module":     ("M7", "数码管模组"),
}

# 爆炸偏移（Blender 坐标系）：name → (方向, 距离)。未列出的零件按质心主轴自动计算。
CENTER = Vector((0.086, 0.0, 0.0))
XP, XN, YP, YN, ZP, ZN = (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)
EXPLODE = {
    "Body": (XP, 0.11), "Band": (XP, 0.05), "FrontPanel": (YP, 0.09),
    "OutletCavity": (YP, 0.07),
    "Louver_0": (YP, 0.13), "Louver_1": (YP, 0.13), "Louver_2": (YP, 0.13),
    "Display": (YP, 0.11), "DisplayGlass": (YP, 0.115),
    "Knob": (XP, 0.17), "CoolKey": (XP, 0.17),
    "Base": (XN, 0.06), "SkidPad": (XN, 0.115), "TypeC": (YN, 0.10),
    "HotVent_R": (ZP, 0.10), "HotVentCavity_R": (ZP, 0.075),
    "HotVent_L": (ZN, 0.10), "HotVentCavity_L": (ZN, 0.075),
    "IntakeGrille": (YN, 0.11), "IntakeCavity": (YN, 0.085),
    "M4_FanFrame": (ZN, 0.105), "M4_FanHub": (ZN, 0.105), "M4_FanBlades": (ZN, 0.105),
    "M5_ColdFins": (ZN, 0.075), "M5_TEC": (ZP, 0.032), "M5_HotSink": (ZP, 0.075),
    "M5_Separator": (XN, 0.05),
    "M2_Bracket": (ZN, 0.05), "M2_Cell_A": (ZN, 0.12), "M2_Cell_B": (ZN, 0.15),
    "M3_PCB": (YN, 0.075), "M3_ICs": (YN, 0.105), "M3_Pot": (XP, 0.155),
    "M1_Stepper": (ZP, 0.135), "M1_Link": (ZP, 0.135),
    "M7_Module": (YP, 0.06),
}

# ================= 内部核心构建 =================
def build_core(m):
    parts = []
    # ---- M5 热模块（冷风道沿 Y 轴：后进风→风机→冷鳍→前出；热端三明治沿 Z 排布） ----
    # TEC 40×40×3.8，法线 Z（冷面 -Z / 热面 +Z）
    tec = box("M5_TEC", (0.040, 0.040, 0.0038), (0.064, 0.012, 0.0019), mat=m["TEC"], bevel=0.0006)
    parts.append(tec)
    # 冷端：基板(40×40×4, 贴 TEC 冷面) + 8 片鳍(板法线 Z 沿 Z 排布, 风道沿 Y 贯通)
    cf = [box("cf_base", (0.040, 0.040, 0.004), (0.064, 0.012, -0.002), mat=m["AluFin"])]
    for i in range(8):
        z = -0.038 + i * 0.0047
        cf.append(box("cf_%d" % i, (0.040, 0.012, 0.001), (0.064, 0.012, z), mat=m["AluFin"]))
    parts.append(join_parts("M5_ColdFins", cf))
    # 热端：基板(40×40×4, 贴 TEC 热面) + 7 片鳍(板法线 Y 沿 Y 排布, 通道后→右侧排)
    hs = [box("hs_base", (0.040, 0.040, 0.004), (0.064, 0.012, 0.0058), mat=m["Copper"])]
    for i in range(7):
        y = -0.005 + i * 0.0058
        hs.append(box("hs_%d" % i, (0.040, 0.0015, 0.032), (0.064, y, 0.0238), mat=m["Copper"]))
    parts.append(join_parts("M5_HotSink", hs))
    # 中隔板（X-Y 平面, 风机前方, 开窗让 TEC/基板穿过 → 双风道物理隔离 ADR-1）
    sep = box("M5_Separator", (0.086, 0.042, 0.0016), (0.075, 0.027, 0.0008), mat=m["SepBoard"])
    win = box("cutter_sep", (0.044, 0.044, 0.016), (0.064, 0.012, 0.002))
    boolean_cut(sep, win)
    parts.append(sep)
    # ---- M4 动力：Ø80 轴向无刷风机（轴沿 Y, 向 +Y 前吹） ----
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
        bl.rotation_euler = (0.55, -a, 0.0)   # 扭角 + 周向排布
        blades.append(bl)
    parts.append(join_parts("M4_FanBlades", blades))
    # ---- M2 能源：2×18650 并排(沿 Z 躺放, 左下) + 支架/保护板 ----
    for tag, yy in (("A", -0.010), ("B", 0.012)):
        cell = [cyl("cell_%s" % tag, 0.009, 0.065, (0.029, yy, -0.062),
                    rot=(0, math.pi / 2, 0), mat=m["CellWrap"]),
                cyl("cellcap_%s" % tag, 0.0085, 0.0015, (0.029, yy, -0.0288),
                    rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
        parts.append(join_parts("M2_Cell_%s" % tag, cell))
    br = [box("br_tray", (0.006, 0.048, 0.074), (0.021, 0.001, -0.062), mat=m["Bracket"], bevel=0.002),
          box("br_bms", (0.020, 0.002, 0.012), (0.033, -0.024, -0.062), mat=m["PCBGreen"])]
    parts.append(join_parts("M2_Bracket", br))
    # ---- M3 主控：PCB(后壁右侧立板) + 主要 IC 示意块 + 旋钮电位器 ----
    parts.append(box("M3_PCB", (0.060, 0.0016, 0.060), (0.085, -0.046, 0.045),
                     mat=m["PCBGreen"], bevel=0.002))
    ics = [box("ic_mcu", (0.012, 0.002, 0.012), (0.095, -0.0445, 0.030), mat=m["ICBlack"]),
           box("ic_drv", (0.010, 0.002, 0.010), (0.075, -0.0445, 0.055), mat=m["ICBlack"]),
           box("ic_chg", (0.008, 0.002, 0.008), (0.065, -0.0445, 0.030), mat=m["ICBlack"]),
           box("ic_usbc", (0.006, 0.003, 0.010), (0.058, -0.0450, 0.058), mat=m["CellSteel"])]
    parts.append(join_parts("M3_ICs", ics))
    pot = [cyl("pot_body", 0.0085, 0.012, (0.146, 0.006, 0.062), rot=(0, math.pi / 2, 0), mat=m["FanDark"]),
           cyl("pot_shaft", 0.003, 0.010, (0.154, 0.006, 0.062), rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
    parts.append(join_parts("M3_Pot", pot))
    # ---- M1 导风机构：28BYJ-48 步进电机(Ø28×19, 轴沿 Z) + 摇臂联动杆 ----
    parts.append(cyl("M1_Stepper", 0.014, 0.019, (0.064, 0.010, 0.090),
                     rot=(math.pi / 2, 0, 0), mat=m["StepperBlue"]))
    lk = [cyl("lk_crank", 0.007, 0.003, (0.064, 0.010, 0.0795), rot=(math.pi / 2, 0, 0), mat=m["CellSteel"]),
          box("lk_rod", (0.003, 0.038, 0.002), (0.064, 0.029, 0.0835), mat=m["CellSteel"])]
    lk[1].rotation_euler = (0, 0, -0.12)
    parts.append(join_parts("M1_Link", lk))
    # ---- M7 数显模组（前壳数显窗背后） ----
    parts.append(box("M7_Module", (0.030, 0.008, 0.058), (0.118, 0.048, 0.072),
                     mat=m["ICBlack"], bevel=0.002))
    return parts

# ================= 爆炸向量 =================
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
    """Blender (x,y,z) → glTF (x,z,-y)（export_yup=True 同款变换）"""
    return [v.x, v.z, -v.y]

# ================= GLB JSON 核验 =================
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

# ================= 主流程 =================
def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    shell_names = set(SHELL_META.keys())
    have = {o.name for o in bpy.data.objects if o.type == "MESH"}
    missing = shell_names - have
    if missing:
        raise RuntimeError("form_a.blend 缺外壳件 %s —— 先跑 FAST=0 blender --background --python build_form_a.py" % missing)

    m = {
        "TEC":        new_mat("TEC", (0.94, 0.94, 0.92, 1), 0.0, 0.35),
        "AluFin":     new_mat("AluFin", (0.85, 0.87, 0.90, 1), 1.0, 0.25),
        "Copper":     new_mat("Copper", (0.72, 0.42, 0.24, 1), 1.0, 0.30),
        "SepBoard":   new_mat("SepBoard", (0.88, 0.86, 0.78, 1), 0.0, 0.6),
        "FanDark":    new_mat("FanDark", (0.10, 0.10, 0.11, 1), 0.2, 0.5),
        "BladeDark":  new_mat("BladeDark", (0.16, 0.17, 0.19, 1), 0.1, 0.45),
        "CellSteel":  new_mat("CellSteel", (0.62, 0.66, 0.70, 1), 1.0, 0.28),
        "CellWrap":   new_mat("CellWrap", (0.18, 0.44, 0.62, 1), 0.1, 0.45),
        "Bracket":    new_mat("Bracket", (0.25, 0.50, 0.38, 1), 0.0, 0.6),
        "PCBGreen":   new_mat("PCBGreen", (0.04, 0.32, 0.14, 1), 0.1, 0.5),
        "ICBlack":    new_mat("ICBlack", (0.06, 0.06, 0.07, 1), 0.3, 0.4),
        "StepperBlue": new_mat("StepperBlue", (0.16, 0.32, 0.68, 1), 0.6, 0.35),
    }
    core = build_core(m)

    # ---- 注册 extras（module/label/explode，glTF 坐标） + 收集零件表 ----
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
        json.dump({"glb": "cad/assembly_a.glb", "parts": records}, f, ensure_ascii=False, indent=1)
    print("PARTS JSON:", PARTS_JSON, "(%d parts)" % len(records))

    # ---- 导出 GLB（仅 mesh，带 extras） ----
    bpy.ops.object.select_all(action="DESELECT")
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=GLB_OUT, export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=False, export_extras=True)
    print("GLB EXPORTED:", GLB_OUT)
    verify_glb(GLB_OUT)

    # ---- 渲染 1：装配态（半透明壳 + 双风道箭头） ----
    scene = bpy.context.scene
    os.makedirs(RENDER_DIR, exist_ok=True)
    hidden = ["OutletCavity", "IntakeCavity", "HotVentCavity_L", "HotVentCavity_R"]
    saved_hide = {}
    for nm in hidden:
        ob = bpy.data.objects[nm]
        saved_hide[ob] = ob.hide_render
        ob.hide_render = True
    trans_mats = {}
    for nm in ("Body", "FrontPanel"):
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
    arrow_cold = arrow("Airflow_Cold", (0.075, -0.085, -0.025), (0.075, 0.095, -0.025),
                       new_mat("AirCold", (0.10, 0.55, 0.95, 1), 0.0, 0.4,
                               emission=(0.10, 0.55, 0.95, 1), emission_strength=1.5))
    ah = new_mat("AirHot", (0.95, 0.30, 0.12, 1), 0.0, 0.4,
                 emission=(0.95, 0.30, 0.12, 1), emission_strength=1.5)
    arrow_h1 = arrow("Airflow_Hot_in", (0.064, -0.085, 0.024), (0.064, 0.000, 0.024), ah)
    arrow_h2 = arrow("Airflow_Hot_out", (0.064, 0.012, 0.030), (0.064, 0.012, 0.140), ah)
    arrows = [arrow_cold, arrow_h1, arrow_h2]

    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    TARGET = Vector((0.086, 0.0, 0.0))

    def shoot(name, loc, target):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.data.lens = 55
        # 与 build_form_a.py aim_camera 同款基向量（X 轴竖直）
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
