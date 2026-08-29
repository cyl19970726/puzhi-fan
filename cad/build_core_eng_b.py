"""
LiteCool S1 — 形态 B「复古收音机」工程级（DFM 级）装配体 v1.0
用法: blender --background --python build_core_eng_b.py      （FAST=1 默认 480px 快渲；FAST=0 800px 终渲；INSPECT=1 出检查视角）
与形态 A 工程级（build_core_eng.py）同标准，差异：
  1. 布局适配 B 盒体（W200(Z)×H150(X)×D120(Y) + 4 矮圆脚 10mm）：
     冷风道 背部下段进风(真孔)→Ø80 风机→TEC 冷鳍→正面整面编织网罩(真孔经纬条)出风；
     热风道 背部上段独立进风(真孔,新增)→热端散热器(鳍片通道沿 Y)→顶部后缘热排孔(真孔)；
     L 形中隔板 = 水平臂(x=0.100, 冷下热上) + 竖直臂(y=0.020, 前冷后热) 全长分断冷热腔（ADR-1）。
  2. B 无导风板扫风机构：免 28BYJ-48/齿轮副/联动杆，改为固定 15° 导流叶片×4（M6_GuideVanes）。
  3. 其余 DFM 同 A：壁厚 2.0（外拔模锥台−内拔模锥台差集）、拔模 1.5°（沿 Y 脱模）、
     网罩面板↔主壳分件线、旋扣×3（IF-3）、数显窗卡扣+遮光筋（IF-4）、电池仓防反插+减震筋（IF-5）、
     EVA 密封槽×6（IF-2）、底脚螺丝柱×4（Ø2.5 盲孔+脚内沉孔）。
复用方式：exec 载入 build_core_eng.py（去掉末尾 main() 调用）复用其零件构造函数/工具/GLB 核验；
          exec 载入 build_form_b.py（去掉末尾渲染调用）复用顶面 7 段数码管字形。
          注意 A 记录的"圆柱轴向系统性 bug"：Blender 圆柱默认轴向 Z(=机器左右)，
          竖直(X)圆柱一律 rot=(0,π/2,0)，前后(Y)圆柱一律 rot=(π/2,0,0)，本脚本全部照此。
输出:
  cad/assembly_b.glb            — 35 个命名 mesh，extras 带 module/label/explode(glTF 坐标)
  cad/assembly_b_parts.json     — 格式对齐 assembly_a_parts.json
  cad/renders_assembly_eng_b/{assembled,exploded}.png (+INSPECT 检查图)
坐标约定（全项目统一）: X=高度, Y=前后(前=+Y), Z=左右(右=+Z)
"""
import bpy
import math
import mathutils
import os
import json
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLB_OUT = os.path.join(BASE_DIR, "assembly_b.glb")
PARTS_JSON = os.path.join(BASE_DIR, "assembly_b_parts.json")
RENDER_DIR = os.path.join(BASE_DIR, "renders_assembly_eng_b")
FAST = os.environ.get("FAST", "1") == "1"

# ================= exec 复用形态 A 工程级零件构造工具（不重写一套） =================
def _exec_without_tail(path, n_strip):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    lines = src.splitlines()
    ns = {"__file__": path}
    exec(compile("\n".join(lines[:len(lines) - n_strip]), path, "exec"), ns)
    return ns

_A = _exec_without_tail(os.path.join(BASE_DIR, "build_core_eng.py"), 1)   # 去 main()
_B = _exec_without_tail(os.path.join(BASE_DIR, "build_form_b.py"), 3)     # 去 BASE_DIR/render_set/print

new_mat = _A["new_mat"]
box = _A["box"]
cyl = _A["cyl"]
cone = _A["cone"]
frustum_y = _A["frustum_y"]
apply_bevel = _A["apply_bevel"]
boolean_cut = _A["boolean_cut"]
join_parts = _A["join_parts"]
arrow = _A["arrow"]
verify_glb = _A["verify_glb"]
build_display_top = _B["build_display_top"]   # 顶面 7 段数码管（法线 +X）

# ================= 总体参数（外形沿用形态 B：W200(Z)×H150(X)×D120(Y) + 脚 10mm） =================
WALL = 0.002                              # 外壳壁厚 2.0mm（DFM 规则）
DRAFT = math.tan(math.radians(1.5))       # 拔模 1.5°（沿 Y 脱模：后小前大）
FEET_H = 0.010
BODY_X0, BODY_X1 = 0.010, 0.160           # 机身高（脚上缘→顶）
BODY_Y0, BODY_Y1 = -0.060, 0.058          # 机身后→前（前开口，网罩面板盖到 0.060）
BODY_Z = 0.100                            # 机身半宽
DX = DRAFT * (BODY_Y1 - BODY_Y0)          # 后端拔模收缩量 ≈3.1mm
INTAKE_C = dict(x0=0.034, x1=0.078, z0=-0.070, z1=0.070, bars=6)    # 背部冷进风真孔(沿用概念位置)
INTAKE_H = dict(x0=0.110, x1=0.140, z0=-0.070, z1=0.070, bars=4)    # 背部热进风真孔(工程新增,独立进风)
HOTVENT = dict(y0=-0.054, y1=-0.034, z0=-0.072, z1=0.072, slats=6)  # 顶部后缘热排真孔(沿用概念位置)
MESH = dict(x0=0.021, x1=0.149, z=0.095, pitch=0.0022)              # 整面编织网罩(覆盖正面 81%)
DISP = dict(y=0.038, z=-0.055, r=0.012)                             # 顶面小圆数显窗(前缘左)
KNOB = dict(r=0.021, h=0.016, y=-0.012, z=0.0)                      # 顶部单颗大旋钮
COOLKEY = dict(r=0.0075, h=0.005, y=0.038, z=0.055)                 # 制冷键(前缘右)
SEP_X = 0.100                             # 中隔板水平臂（下冷上热）
SEP_Y = 0.020                             # 中隔板竖直臂（前冷后热）
TEC_C = (0.1019, -0.020, 0.0)             # TEC 中心（水平,冷面朝下 -X）
FAN_C = (0.056, -0.032, 0.0)              # Ø80 风机中心（轴沿 Y）
VANE_X = [0.040, 0.068, 0.096, 0.124]     # 固定导流叶片×4（15°）
VANE_Y = 0.048
FOOT_AT = [(sy * 0.040, sz * 0.075) for sy in (1.0, -1.0) for sz in (1.0, -1.0)]

def top_x_at(yy):
    """拔模后顶面（前高后低）"""
    return (BODY_X1 - DX) + DX * ((yy - BODY_Y0) / (BODY_Y1 - BODY_Y0))

# ================= 零件注册表（命名体系同 A：语义延续件同名，新增件同前缀） =================
SHELL_META = {
    "Feet":            ("M1", "矮圆脚×4(Ø2.5通孔+Ø5沉孔)"),
    "TypeC":           ("M1", "Type-C 进线口"),
    "M1_Bosses":       ("M1", "底脚螺丝柱×4(Ø8柱+Ø2.5盲孔)"),
    "Body":            ("M6", "主壳(2mm壁厚+1.5°拔模+真孔:冷/热进风+顶热排+数显窗)"),
    "FrontMesh":       ("M6", "整面编织网罩面板(真孔经纬条+边框,覆盖正面81%)"),
    "Band":            ("M6", "装饰腰线(随拔模锥度)"),
    "MintLine":        ("M6", "薄荷绿品牌细线"),
    "M6_TwistLock":    ("M6", "网罩旋扣×3(转15°卡入, IF-3)"),
    "M6_GuideVanes":   ("M6", "固定15°导流叶片×4(替代导风板机构)"),
    "Display":         ("M7", "数码管字形 22.0(顶面)"),
    "DisplayGlass":    ("M7", "半透数显圆窗 PMMA Ø24"),
    "DisplayBezel":    ("M7", "数显窗压圈"),
    "M7_Clip":         ("M7", "数显窗卡扣×4+遮光筋(IF-4)"),
    "HotVent":         ("M5", "顶部后缘热排格栅(真孔横槽×6)"),
    "IntakeGrille":    ("M5", "背部冷进风格栅(真孔横条×6)"),
    "HotIntakeGrille": ("M5", "背部热进风格栅(真孔横条×4,独立进风)"),
    "Knob":            ("M3", "顶部单颗大旋钮 Ø42(100档FOC)"),
    "CoolKey":         ("M3", "制冷键"),
}
CORE_META = {
    "M5_TEC":        ("M5", "TEC 制冷片 40×40×3.8(水平,冷面朝下)"),
    "M5_ColdFins":   ("M5", "冷端铝鳍片组(悬挂于冷风道,通道沿Y)"),
    "M5_HotSink":    ("M5", "热端散热器(立于热腔,鳍片通道沿Y)"),
    "M5_Separator":  ("M5", "L形全风道中隔板(ADR-1,水平臂+竖直臂,带EVA槽)"),
    "M5_EVA":        ("M5", "EVA密封棉条×6(IF-2,3×1.5槽)"),
    "M5_ColdDuct":   ("M5", "冷风道(背进风→风机→冷鳍→整面网罩贯通腔)"),
    "M5_HotDuct":    ("M5", "热风道导流板(挡板强制S流:进风→鳍片→顶排)"),
    "M4_FanFrame":   ("M4", "风机框 Ø80"),
    "M4_FanHub":     ("M4", "轮毂+无刷电机"),
    "M4_FanBlades":  ("M4", "扇叶 ×7"),
    "M2_Cell_A":     ("M2", "18650 电芯 A(右)"),
    "M2_Cell_B":     ("M2", "18650 电芯 B(左)"),
    "M2_Bracket":    ("M2", "电池仓(防反插+减震筋,IF-5)"),
    "M3_PCB":        ("M3", "主控 PCB(冷腔背进风后方)"),
    "M3_ICs":        ("M3", "主要 IC(MCU/驱动/充电/USB-C)"),
    "M3_Pot":        ("M3", "旋钮电位器(热腔顶,轴穿顶壁)"),
    "M7_Module":     ("M7", "数码管模组(冷腔前顶)"),
}

# 爆炸偏移（Blender 坐标系）
CENTER = Vector((0.085, 0.0, 0.0))
XP, XN, YP, YN, ZP, ZN = (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)
EXPLODE = {
    "Body": (XP, 0.11), "Band": (XN, 0.04), "MintLine": (XN, 0.06),
    "FrontMesh": (YP, 0.10), "M6_TwistLock": (YP, 0.13), "M6_GuideVanes": (YP, 0.16),
    "DisplayBezel": (XP, 0.14), "DisplayGlass": (XP, 0.155), "Display": (XP, 0.17),
    "M7_Clip": (XP, 0.12), "M7_Module": (XP, 0.095),
    "Knob": (XP, 0.20), "CoolKey": (XP, 0.20),
    "Feet": (XN, 0.06), "M1_Bosses": (XN, 0.095), "TypeC": (YN, 0.10),
    "HotVent": (XP, 0.13), "IntakeGrille": (YN, 0.11), "HotIntakeGrille": (YN, 0.14),
    "M4_FanFrame": (ZN, 0.105), "M4_FanHub": (ZN, 0.105), "M4_FanBlades": (ZN, 0.105),
    "M5_ColdFins": (ZN, 0.075), "M5_TEC": (ZP, 0.032), "M5_HotSink": (ZP, 0.075),
    "M5_Separator": (XN, 0.05), "M5_EVA": (XN, 0.075),
    "M5_ColdDuct": (ZN, 0.045), "M5_HotDuct": (ZP, 0.10),
    "M2_Bracket": (XN, 0.045), "M2_Cell_A": (ZP, 0.12), "M2_Cell_B": (ZN, 0.12),
    "M3_PCB": (YN, 0.075), "M3_ICs": (YN, 0.105), "M3_Pot": (XP, 0.155),
}

# ================= 外壳（DFM 级重建，外形/分件沿用形态 B 概念稿） =================
def build_shell(m):
    parts = []
    # ---- 主壳 Body：外拔模锥台(R14 圆角) − 内拔模锥台(前开口) = 2.0mm 壁厚 tub ----
    body = frustum_y("Body", BODY_Y0, BODY_Y1,
                     (BODY_X0, BODY_X1 - DX), (-BODY_Z + DX, BODY_Z - DX),
                     (BODY_X0, BODY_X1), (-BODY_Z, BODY_Z), mat=m["BodyCream"])
    apply_bevel(body, 0.014, seg=5)
    cav = frustum_y("cutter_cav", BODY_Y0 + WALL, BODY_Y1 + 0.010,
                    (BODY_X0 + WALL, BODY_X1 - DX - WALL),
                    (-BODY_Z + DX + WALL, BODY_Z - DX - WALL),
                    (BODY_X0 + WALL, BODY_X1 - WALL), (-BODY_Z + WALL, BODY_Z - WALL))
    boolean_cut(body, cav)
    # 背部冷进风真孔 + 背部热进风真孔（后壁 2mm 贯通）
    for tag, vent in (("c", INTAKE_C), ("h", INTAKE_H)):
        boolean_cut(body, box("cutter_intake_" + tag,
                              (vent["x1"] - vent["x0"], 0.010, vent["z1"] - vent["z0"]),
                              ((vent["x0"] + vent["x1"]) / 2, BODY_Y0 + WALL / 2, 0), bevel=0.004))
    # 顶部后缘热排真孔（顶壁 2mm 贯通，沿用概念 y/z 位置）
    hv_y = (HOTVENT["y0"] + HOTVENT["y1"]) / 2
    boolean_cut(body, box("cutter_hv",
                          (0.010, HOTVENT["y1"] - HOTVENT["y0"], HOTVENT["z1"] - HOTVENT["z0"]),
                          (top_x_at(hv_y), hv_y, 0), bevel=0.003))
    # 顶面数显圆窗 / 旋钮孔 / 制冷键孔（顶壁贯通）
    boolean_cut(body, cyl("cutter_disp", DISP["r"] - 0.001, 0.010,
                          (top_x_at(DISP["y"]), DISP["y"], DISP["z"]), rot=(0, math.pi / 2, 0)))
    boolean_cut(body, cyl("cutter_knob", 0.005, 0.010,
                          (top_x_at(KNOB["y"]), KNOB["y"], KNOB["z"]), rot=(0, math.pi / 2, 0)))
    boolean_cut(body, cyl("cutter_ck", 0.004, 0.010,
                          (top_x_at(COOLKEY["y"]), COOLKEY["y"], COOLKEY["z"]), rot=(0, math.pi / 2, 0)))
    # 旋扣母槽×3（前缘顶壁/左右壁贯通槽 10×10mm，IF-3）
    boolean_cut(body, box("cutter_lock_t", (0.010, 0.012, 0.010), (0.159, 0.054, 0)))
    for sz in (1.0, -1.0):
        boolean_cut(body, box("cutter_lock_s", (0.010, 0.012, 0.010), (0.085, 0.054, sz * 0.099)))
    # 底壁 4×Ø2.5 通孔（底脚螺丝过孔）
    for i, (fy, fz) in enumerate(FOOT_AT):
        boolean_cut(body, cyl("cutter_foot_%d" % i, 0.00125, 0.006,
                              (BODY_X0 + WALL / 2, fy, fz), rot=(0, math.pi / 2, 0)))
    parts.append(body)
    # ---- 整面编织网罩面板 FrontMesh：边框 + 真实经纬条（条间真实开口, 覆盖正面 81%） ----
    mesh_h = MESH["x1"] - MESH["x0"]
    mesh_xc = (MESH["x0"] + MESH["x1"]) / 2
    fm = [
        box("fm_top", (BODY_X1 - MESH["x1"] - 0.001, 0.003, 0.199),
            ((MESH["x1"] + BODY_X1) / 2, 0.0585, 0), mat=m["BodyCream"], bevel=0.002),
        box("fm_bot", (MESH["x0"] - BODY_X0 - 0.001, 0.003, 0.199),
            ((BODY_X0 + MESH["x0"]) / 2, 0.0585, 0), mat=m["BodyCream"], bevel=0.002),
        box("fm_sl", (mesh_h + 0.002, 0.003, BODY_Z - MESH["z"] - 0.001),
            (mesh_xc, 0.0585, -(MESH["z"] + BODY_Z) / 2), mat=m["BodyCream"], bevel=0.002),
        box("fm_sr", (mesh_h + 0.002, 0.003, BODY_Z - MESH["z"] - 0.001),
            (mesh_xc, 0.0585, (MESH["z"] + BODY_Z) / 2), mat=m["BodyCream"], bevel=0.002),
    ]
    nz = int((2 * MESH["z"]) / MESH["pitch"])          # 经条（沿 X 竖）
    for i in range(nz):
        zz = -MESH["z"] + (i + 0.5) * 2 * MESH["z"] / nz
        fm.append(box("fm_w%d" % i, (mesh_h, 0.0006, 0.0007), (mesh_xc, 0.0580, zz), mat=m["MeshBronze"]))
    nx = int(mesh_h / MESH["pitch"])                    # 纬条（沿 Z 横）
    for j in range(nx):
        xx = MESH["x0"] + (j + 0.5) * mesh_h / nx
        fm.append(box("fm_f%d" % j, (0.0007, 0.0006, 2 * MESH["z"]), (xx, 0.0588, 0), mat=m["MeshBronze"]))
    parts.append(join_parts("FrontMesh", fm))
    # ---- 旋扣×3（网罩面板背面 L 钩，钩片 12mm>槽 10mm，已转 15° 锁止态，IF-3） ----
    locks = []
    st = box("lk_stem_t", (0.002, 0.005, 0.003), (0.157, 0.0555, 0), mat=m["BodyCream"])
    tb = box("lk_tab_t", (0.002, 0.0016, 0.012), (0.157, 0.0528, 0), mat=m["BodyCream"])
    tb.rotation_euler = (0, math.radians(15), 0)
    locks += [st, tb]
    for sz in (1.0, -1.0):
        st = box("lk_stem_s", (0.003, 0.005, 0.002), (0.085, 0.0555, sz * 0.0975), mat=m["BodyCream"])
        tb = box("lk_tab_s", (0.012, 0.0016, 0.002), (0.085, 0.0528, sz * 0.0975), mat=m["BodyCream"])
        tb.rotation_euler = (0, math.radians(15), 0)
        locks += [st, tb]
    parts.append(join_parts("M6_TwistLock", locks))
    # ---- 进风/热排格栅条（真孔内的横条，条间为真实开口） ----
    bars = []
    for i in range(INTAKE_C["bars"]):
        xx = INTAKE_C["x0"] + (i + 0.5) * (INTAKE_C["x1"] - INTAKE_C["x0"]) / INTAKE_C["bars"]
        bars.append(box("in_%d" % i, (0.0038, 0.0018, INTAKE_C["z1"] - INTAKE_C["z0"] - 0.004),
                        (xx, BODY_Y0 + WALL / 2, 0), mat=m["Grid"]))
    parts.append(join_parts("IntakeGrille", bars))
    bars = []
    for i in range(INTAKE_H["bars"]):
        xx = INTAKE_H["x0"] + (i + 0.5) * (INTAKE_H["x1"] - INTAKE_H["x0"]) / INTAKE_H["bars"]
        bars.append(box("hin_%d" % i, (0.0038, 0.0018, INTAKE_H["z1"] - INTAKE_H["z0"] - 0.004),
                        (xx, BODY_Y0 + WALL / 2, 0), mat=m["Grid"]))
    parts.append(join_parts("HotIntakeGrille", bars))
    slats = []
    for i in range(HOTVENT["slats"]):
        yy = HOTVENT["y0"] + (i + 0.5) * (HOTVENT["y1"] - HOTVENT["y0"]) / HOTVENT["slats"]
        slats.append(box("hv_%d" % i, (0.0018, 0.002, HOTVENT["z1"] - HOTVENT["z0"] - 0.006),
                         (top_x_at(yy) - 0.0005, yy, 0), mat=m["VentSlat"]))
    parts.append(join_parts("HotVent", slats))
    # ---- 固定 15° 导流叶片×4（B 无扫风机构；叶片两端沉入风道侧板槽） ----
    vanes = []
    for i, xx in enumerate(VANE_X):
        v = box("vane_%d" % i, (0.014, 0.0022, 0.186), (xx, VANE_Y, 0), mat=m["VentSlat"], bevel=0.001)
        v.rotation_euler = (0, 0, math.radians(15))
        vanes.append(v)
    parts.append(join_parts("M6_GuideVanes", vanes))
    # ---- 数显：顶面圆窗玻璃 + 压圈 + 数码管字形 + 卡扣×4 + 遮光筋（IF-4） ----
    tx = top_x_at(DISP["y"])
    bezel = cyl("DisplayBezel", DISP["r"] + 0.0018, 0.0012, (tx + 0.0004, DISP["y"], DISP["z"]),
                rot=(0, math.pi / 2, 0), mat=m["Wood"])
    # 压圈为圆环（内孔 Ø23 让玻璃/字形露出，非实心盖）
    boolean_cut(bezel, cyl("cutter_bezel", 0.0115, 0.006, (tx + 0.0004, DISP["y"], DISP["z"]),
                           rot=(0, math.pi / 2, 0)))
    parts.append(bezel)
    # 玻璃在下(深色衬底)、字形在上(同概念稿叠层,否则深色玻璃盖住发光字)
    parts.append(cyl("DisplayGlass", DISP["r"], 0.001, (tx - 0.0012, DISP["y"], DISP["z"]),
                     rot=(0, math.pi / 2, 0), mat=m["GlassDark"]))
    parts.append(build_display_top("22.0", tx - 0.0004, DISP["y"], DISP["z"], m["DigitGlow"]))
    clips = []
    # 遮光筋：窗孔背面整圈方环筋（26×26，高 3mm，防数码管光晕串到壳内）
    r_out, r_in = DISP["r"] + 0.002, DISP["r"] + 0.0008
    xc = tx - 0.0025
    clips.append(box("rib_y0", (0.003, 0.0012, 2 * r_out), (xc, DISP["y"] - r_in, DISP["z"]), mat=m["BodyCream"]))
    clips.append(box("rib_y1", (0.003, 0.0012, 2 * r_out), (xc, DISP["y"] + r_in, DISP["z"]), mat=m["BodyCream"]))
    clips.append(box("rib_z0", (0.003, 2 * r_out, 0.0012), (xc, DISP["y"], DISP["z"] - r_in), mat=m["BodyCream"]))
    clips.append(box("rib_z1", (0.003, 2 * r_out, 0.0012), (xc, DISP["y"], DISP["z"] + r_in), mat=m["BodyCream"]))
    # 卡扣×4（咬住玻璃背缘的斜钩，玻璃 Ø24 比孔 Ø22 大 2mm=搭接唇边）
    for dy, dz in ((0.008, 0.008), (0.008, -0.008), (-0.008, 0.008), (-0.008, -0.008)):
        clips.append(box("clip", (0.0026, 0.004, 0.004), (tx - 0.0018, DISP["y"] + dy, DISP["z"] + dz),
                         mat=m["BodyCream"], bevel=0.0005))
    parts.append(join_parts("M7_Clip", clips))
    parts.append(box("M7_Module", (0.005, 0.030, 0.030), (tx - 0.0065, DISP["y"], DISP["z"]),
                     mat=m["ICBlack"], bevel=0.0015))
    # ---- 矮圆脚×4（squat 圆脚，Ø2.5 通孔+Ø5×3 沉孔） + 底脚螺丝柱×4（Ø8 柱 Ø2.5 盲孔） ----
    feet = []
    for i, (fy, fz) in enumerate(FOOT_AT):
        f = cyl("foot_%d" % i, 0.009, FEET_H, (FEET_H / 2, fy, fz),
                rot=(0, math.pi / 2, 0), mat=m["Wood"], verts=32)
        boolean_cut(f, cyl("cutter_fh_%d" % i, 0.00125, 0.014, (FEET_H / 2, fy, fz), rot=(0, math.pi / 2, 0)))
        boolean_cut(f, cyl("cutter_fs_%d" % i, 0.0025, 0.004, (0.0015, fy, fz), rot=(0, math.pi / 2, 0)))
        feet.append(f)
    parts.append(join_parts("Feet", feet))
    bosses = []
    for i, (fy, fz) in enumerate(FOOT_AT):
        bo = cyl("boss_%d" % i, 0.004, 0.016, (0.020, fy, fz), rot=(0, math.pi / 2, 0), mat=m["BodyCream"])
        # 盲孔：柱顶留 6mm 咬合料
        boolean_cut(bo, cyl("cutter_boss_%d" % i, 0.00125, 0.010, (0.017, fy, fz), rot=(0, math.pi / 2, 0)))
        bosses.append(bo)
    parts.append(join_parts("M1_Bosses", bosses))
    parts.append(box("TypeC", (0.005, 0.003, 0.011), (0.020, BODY_Y0 - 0.0005, 0.050),
                     mat=m["VoidDark"], bevel=0.0015))
    # ---- 装饰腰线 + 薄荷细线（随体拔模锥度的锥台环；正面藏于网罩底梁后） ----
    band = frustum_y("Band", BODY_Y0 - 0.0005, 0.0555,
                     (0.0128, 0.0182), (-BODY_Z + DX - 0.0005, BODY_Z - DX + 0.0005),
                     (0.0128, 0.0182), (-BODY_Z - 0.0005, BODY_Z + 0.0005), mat=m["Wood"])
    apply_bevel(band, 0.0015, seg=3)
    parts.append(band)
    mint = frustum_y("MintLine", BODY_Y0 - 0.0005, 0.0555,
                     (0.0185, 0.0201), (-BODY_Z + DX - 0.0005, BODY_Z - DX + 0.0005),
                     (0.0185, 0.0201), (-BODY_Z - 0.0005, BODY_Z + 0.0005), mat=m["BandMint"])
    apply_bevel(mint, 0.0008, seg=3)
    parts.append(mint)
    # ---- 顶部大旋钮 + 制冷键 ----
    kx = top_x_at(KNOB["y"])
    knob = cyl("knob", KNOB["r"], KNOB["h"], (kx + KNOB["h"] / 2 - 0.002, KNOB["y"], KNOB["z"]),
               rot=(0, math.pi / 2, 0), mat=m["Wood"])
    cap = cyl("knobcap", KNOB["r"] * 0.80, 0.0015, (kx + KNOB["h"] - 0.0025, KNOB["y"], KNOB["z"]),
              rot=(0, math.pi / 2, 0), mat=m["WoodCap"])
    mark = box("knobmark", (0.0012, 0.008, 0.0022), (kx + KNOB["h"] - 0.0012, KNOB["y"] - 0.008, KNOB["z"]),
               mat=m["VoidDark"])
    parts.append(join_parts("Knob", [knob, cap, mark]))
    ckx = top_x_at(COOLKEY["y"])
    ck = cyl("ck", COOLKEY["r"], COOLKEY["h"], (ckx + COOLKEY["h"] / 2 - 0.001, COOLKEY["y"], COOLKEY["z"]),
             rot=(0, math.pi / 2, 0), mat=m["BodyCream"])
    ck_dot = cyl("ckdot", COOLKEY["r"] * 0.45, 0.0015, (ckx + COOLKEY["h"] - 0.0005, COOLKEY["y"], COOLKEY["z"]),
                 rot=(0, math.pi / 2, 0), mat=m["BandMint"])
    parts.append(join_parts("CoolKey", [ck, ck_dot]))
    return parts

# ================= 内部核心（布局适配 B；零件构造复用 A 的工具函数） =================
def build_core(m):
    parts = []
    TX, TY, TZ = TEC_C
    # ---- M5 热模块：TEC 40×40×3.8 水平（冷面 -X 朝下入冷风道 / 热面 +X 朝上入热腔） ----
    parts.append(box("M5_TEC", (0.0038, 0.040, 0.040), (TX, TY, TZ), mat=m["TEC"], bevel=0.0006))
    # 冷端：基板（x 0.096..0.100）+ 9 鳍（板法线 Z,通道沿 Y,悬挂入冷风道 x 0.066..0.096）
    cf = [box("cf_base", (0.004, 0.040, 0.040), (0.098, TY, TZ), mat=m["AluFin"])]
    for i in range(9):
        z = -0.0176 + i * 0.0044
        cf.append(box("cf_%d" % i, (0.030, 0.036, 0.001), (0.081, TY, z), mat=m["AluFin"]))
    parts.append(join_parts("M5_ColdFins", cf))
    # 热端：基板（x 0.1038..0.1078）+ 9 鳍（板法线 Z,通道沿 Y,立于热腔 x 0.1078..0.139）
    hs = [box("hs_base", (0.004, 0.040, 0.040), (0.1058, TY, TZ), mat=m["Copper"])]
    for i in range(9):
        z = -0.020 + i * 0.005
        hs.append(box("hs_%d" % i, (0.0312, 0.040, 0.0012), (0.1234, TY, z), mat=m["Copper"]))
    parts.append(join_parts("M5_HotSink", hs))
    # ---- L 形全风道中隔板（ADR-1）：水平臂(X=Y=Z 板@x=0.100) + 竖直臂(@y=0.020) ----
    # 边缘密封肋（加厚 5mm,开 3mm 宽×1.5mm 深 EVA 槽,IF-2）；6 条接触边全部带槽
    sep = [box("sep_h", (0.002, 0.078, 0.193), (SEP_X, -0.019, 0), mat=m["SepBoard"]),
           box("sep_v", (0.0565, 0.002, 0.193), (0.12825, SEP_Y, 0), mat=m["SepBoard"])]
    ribs = [
        # (名, 肋尺寸, 肋中心, 槽 cutter 尺寸, 槽中心) — 槽开在与外壳接触的肋面
        ("rib_hb", (0.005, 0.006, 0.193), (SEP_X, -0.0555, 0),      # 水平臂后边（贴后壁 y=-0.058）
         (0.003, 0.002, 0.193), (SEP_X, -0.0575, 0)),
        ("rib_hl", (0.005, 0.078, 0.006), (SEP_X, -0.019, -0.094),  # 水平臂左边（贴左壁）
         (0.003, 0.078, 0.002), (SEP_X, -0.019, -0.0965)),
        ("rib_hr", (0.005, 0.078, 0.006), (SEP_X, -0.019, 0.094),   # 水平臂右边
         (0.003, 0.078, 0.002), (SEP_X, -0.019, 0.0965)),
        ("rib_vt", (0.006, 0.005, 0.193), (0.1535, SEP_Y, 0),       # 竖直臂顶边（贴顶壁）
         (0.002, 0.003, 0.193), (0.156, SEP_Y, 0)),
        ("rib_vl", (0.0565, 0.005, 0.006), (0.12825, SEP_Y, -0.094),  # 竖直臂左边
         (0.0565, 0.003, 0.002), (0.12825, SEP_Y, -0.0965)),
        ("rib_vr", (0.0565, 0.005, 0.006), (0.12825, SEP_Y, 0.094),   # 竖直臂右边
         (0.0565, 0.003, 0.002), (0.12825, SEP_Y, 0.0965)),
    ]
    eva = []
    for nm, rs, rc, gs, gc in ribs:
        rib = box(nm, rs, rc, mat=m["SepBoard"])
        boolean_cut(rib, box("g_" + nm, gs, gc))
        sep.append(rib)
        # EVA 棉条：嵌槽内、外凸 ~0.5mm（与壳体内壁压缩量示意）
        eva.append(box("eva_" + nm,
                       (gs[0] - 0.0006, gs[1] - 0.0006, gs[2] - 0.0006),
                       (gc[0] + (0.0005 if gc[0] > 0.14 else 0),
                        gc[1] + (-0.0005 if gc[1] < -0.05 else 0),
                        gc[2] + (0.0005 if gc[2] > 0.09 else (-0.0005 if gc[2] < -0.09 else 0))),
                       mat=m["EVA"]))
    sepall = join_parts("M5_Separator", sep)
    # TEC 窗（冷/热基板穿过水平臂,2mm 间隙）
    boolean_cut(sepall, box("cutter_sepwin", (0.012, 0.044, 0.044), (SEP_X, TY, TZ)))
    parts.append(sepall)
    parts.append(join_parts("M5_EVA", eva))
    # ---- 冷风道（M5_ColdDuct）：底板 + 左右侧板 = 背进风→风机→冷鳍→整面网罩 贯通腔 ----
    duct = [box("duct_floor", (0.002, 0.112, 0.192), (0.014, 0.0, 0), mat=m["DuctWall"]),
            box("duct_sideL", (0.140, 0.112, 0.002), (0.086, 0.0, -0.095), mat=m["DuctWall"]),
            box("duct_sideR", (0.140, 0.112, 0.002), (0.086, 0.0, 0.095), mat=m["DuctWall"])]
    floor = duct[0]
    for i, (fy, fz) in enumerate(FOOT_AT):                # 底板让位螺丝柱（Ø8.5 通孔）
        boolean_cut(floor, cyl("cutter_df_%d" % i, 0.00425, 0.006, (0.014, fy, fz), rot=(0, math.pi / 2, 0)))
    parts.append(join_parts("M5_ColdDuct", duct))
    # ---- 热风道导流板（M5_HotDuct）：顶挡板(x=0.141)强制 S 流 + 两侧挡板(z=±0.030) ----
    hd = [box("hd_top", (0.002, 0.058, 0.060), (0.141, -0.029, 0), mat=m["DuctWall"]),
          box("hd_sl", (0.034, 0.058, 0.002), (0.124, -0.029, -0.030), mat=m["DuctWall"]),
          box("hd_sr", (0.034, 0.058, 0.002), (0.124, -0.029, 0.030), mat=m["DuctWall"])]
    parts.append(join_parts("M5_HotDuct", hd))
    # ---- M4 动力：Ø80 轴流无刷风机（轴沿 Y,向 +Y 吹,背部冷进风后方） ----
    fc = FAN_C
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
    # ---- M2 能源：2×18650（沿 Y 躺放,冷腔底部两侧）+ 电池仓（防反插键位+减震筋, IF-5） ----
    for tag, zz in (("A", 0.070), ("B", -0.070)):
        cell = [cyl("cell_%s" % tag, 0.009, 0.065, (0.024, -0.0175, zz),
                    rot=(math.pi / 2, 0, 0), mat=m["CellWrap"]),
                cyl("cellcap_%s" % tag, 0.0085, 0.0015, (0.024, 0.0157, zz),
                    rot=(math.pi / 2, 0, 0), mat=m["CellSteel"])]
        parts.append(join_parts("M2_Cell_%s" % tag, cell))
    br = []
    for zz in (0.070, -0.070):
        szz = 1.0 if zz > 0 else -1.0
        br += [box("br_end1", (0.024, 0.003, 0.024), (0.024, -0.0515, zz), mat=m["Bracket"]),
               box("br_end2", (0.024, 0.003, 0.024), (0.024, 0.0165, zz), mat=m["Bracket"]),
               box("br_side", (0.024, 0.068, 0.002), (0.024, -0.0175, zz + szz * 0.0095), mat=m["Bracket"]),
               # 减震筋×3（外侧壁+两端 EVA 凸筋,与电芯 0.5mm 压缩量）
               box("br_r1", (0.016, 0.060, 0.0012), (0.024, -0.0175, zz + szz * 0.0082), mat=m["EVA"]),
               box("br_r2", (0.016, 0.0012, 0.018), (0.024, -0.0498, zz), mat=m["EVA"]),
               box("br_r3", (0.016, 0.0012, 0.018), (0.024, 0.0148, zz), mat=m["EVA"])]
    # 防反插：A 仓端壁单侧键位凸台（不对称,反向放不进）+ 偏心 JST 座 + BMS 保护板
    br += [box("br_key", (0.006, 0.004, 0.008), (0.030, 0.0205, 0.062), mat=m["Bracket"]),
           box("br_jst", (0.008, 0.006, 0.008), (0.026, 0.0205, 0.076), mat=m["ICBlack"]),
           box("br_bms", (0.018, 0.0016, 0.030), (0.024, 0.0225, 0.070), mat=m["PCBGreen"])]
    parts.append(join_parts("M2_Bracket", br))
    # ---- M3 主控：PCB（冷腔背进风后方右侧立板）+ IC + 旋钮电位器 ----
    parts.append(box("M3_PCB", (0.052, 0.0016, 0.056), (0.056, -0.053, 0.062),
                     mat=m["PCBGreen"], bevel=0.002))
    ics = [box("ic_mcu", (0.012, 0.002, 0.012), (0.066, -0.0513, 0.048), mat=m["ICBlack"]),
           box("ic_drv", (0.010, 0.002, 0.010), (0.046, -0.0513, 0.076), mat=m["ICBlack"]),
           box("ic_chg", (0.008, 0.002, 0.008), (0.066, -0.0513, 0.076), mat=m["ICBlack"]),
           box("ic_usbc", (0.006, 0.003, 0.010), (0.031, -0.0515, 0.050), mat=m["CellSteel"])]
    parts.append(join_parts("M3_ICs", ics))
    pot = [cyl("pot_body", 0.0085, 0.012, (0.150, KNOB["y"], KNOB["z"]), rot=(0, math.pi / 2, 0), mat=m["FanDark"]),
           cyl("pot_shaft", 0.003, 0.014, (0.159, KNOB["y"], KNOB["z"]), rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
    parts.append(join_parts("M3_Pot", pot))
    return parts

# ================= 爆炸向量（同 A 规则） =================
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

# ================= 场景（同 A 标定：EEVEE + Filmic + 三点光） =================
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

    TARGET = Vector((0.085, 0.0, 0.0))

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
        "BodyCream":  new_mat("BodyCream", (0.955, 0.940, 0.905, 1), 0.0, 0.48),
        "MeshBronze": new_mat("MeshBronze", (0.24, 0.20, 0.15, 1), 0.85, 0.42),
        "Wood":       new_mat("Walnut", (0.24, 0.13, 0.06, 1), 0.0, 0.45),
        "WoodCap":    new_mat("WalnutCap", (0.30, 0.17, 0.08, 1), 0.0, 0.40),
        "VentSlat":   new_mat("VentSlatCream", (0.90, 0.885, 0.85, 1), 0.0, 0.5),
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
        json.dump({"glb": "cad/assembly_b.glb", "parts": records}, f, ensure_ascii=False, indent=1)
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
    for nm in ("Body",):
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
    arrow_cold = arrow("Airflow_Cold", (0.056, -0.080, 0.0), (0.056, 0.085, 0.0),
                       new_mat("AirCold", (0.10, 0.55, 0.95, 1), 0.0, 0.4,
                               emission=(0.10, 0.55, 0.95, 1), emission_strength=1.5))
    ah = new_mat("AirHot", (0.95, 0.30, 0.12, 1), 0.0, 0.4,
                 emission=(0.95, 0.30, 0.12, 1), emission_strength=1.5)
    arrow_h1 = arrow("Airflow_Hot_in", (0.125, -0.080, 0.0), (0.125, -0.028, 0.0), ah)
    arrow_h2 = arrow("Airflow_Hot_out", (0.150, -0.044, 0.030), (0.190, -0.044, 0.030), ah)
    arrows = [arrow_cold, arrow_h1, arrow_h2]

    TARGET = Vector((0.085, 0.0, 0.0))

    def shoot(name, loc, target, lens=55):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.data.lens = lens
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

    shoot("assembled", (0.36, 0.40, 0.44), TARGET)

    if os.environ.get("INSPECT") == "1":
        # 半透检查视角：背视（双进风真孔/风机/PCB）+ 顶后视（热排真孔/热腔）+ 右侧（隔板/风道）
        shoot("inspect_back", (0.30, -0.46, -0.28), TARGET)
        shoot("inspect_toprear", (0.42, -0.30, 0.30), (0.110, -0.020, 0.0))
        shoot("inspect_right", (0.30, 0.02, 0.55), TARGET)
        shoot("inspect_duct", (0.32, 0.34, -0.34), (0.070, 0.0, 0.0))
        # 恢复不透明材质，拍外观/特写（验证真孔与 DFM 特征可读）
        for nm, src in trans_mats.items():
            bpy.data.objects[nm].data.materials[0] = src
        for a in arrows:
            a.hide_render = True
        scene.view_settings.exposure = 0.1
        shoot("inspect_ext_front", (0.085, 0.55, 0.10), TARGET)
        shoot("inspect_ext_back", (0.085, -0.55, 0.0), TARGET)
        shoot("inspect_ext_top", (0.55, -0.06, 0.02), TARGET)
        shoot("inspect_front_close", (0.085, 0.30, 0.02), (0.085, 0.030, 0.0))
        shoot("inspect_disp_close", (0.42, 0.038, -0.055), (0.159, 0.038, -0.055))
        shoot("inspect_bottom", (-0.28, 0.12, 0.16), (0.010, 0.0, 0.0))
        # 裸内部正视（去壳+去网罩，核验网后内部件布局/无穿插/风道贯通）
        hide_objs = [bpy.data.objects[n] for n in ("Body", "FrontMesh", "Band", "MintLine")]
        for ob in hide_objs:
            ob.hide_render = True
        shoot("inspect_naked_front", (0.085, 0.50, 0.0), TARGET)
        shoot("inspect_naked_top", (0.50, -0.02, 0.0), TARGET)
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
    shoot("exploded", (0.64, 0.72, 0.82), (0.10, 0.0, 0.0))
    for o, v in moved:
        o.location -= v
    print("ALL DONE")

main()
