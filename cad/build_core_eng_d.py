"""
LiteCool S1 — 形态 D「塔·认真版」工程级（DFM 级）装配体 v1.0
用法: blender --background --python build_core_eng_d.py   （FAST=1 默认 480×640 快渲；FAST=0 768×1024 终渲；INSPECT=1 检查视角）
与 build_form_d.py（外观白模）的差异：
  1. 内部全建模：架构 §5.2 轴向塔式堆叠——底座(配重盘+硅胶圈+螺丝柱+Type-C+摇头预留位)
     → 2×18650 竖放电池仓(IF-5) → 主控 PCB → Ø80 轴流风机(轴向竖吹)
     → TEC 40×40(冷鳍朝前/热鳍朝后) → 前向百叶出风口(真贯通孔)；
     热风道：TEC 热端→背部竖向 pill 热排立柱(真孔，造型化)。
  2. 风道真实化：后进风/前百叶出风/背部 pill 热排全部 boolean 开真孔；
     L 形中隔板(竖板+底翻边)把 TEC 以上腔体全长分断冷/热腔(ADR-1)，接触边带 EVA 槽(IF-2)。
  3. 外壳 DFM：塔身 squircle(n=4) 变截面 loft 抽 2.0mm 壳(外 loft − 内 loft 差集)、
     前后壳沿 Y=0 分件(1.1mm 止口搭接=分件线)、侧壁 1.5° 拔模(沿 ±Y 脱模，逐顶点 z 收缩)、
     前网罩旋扣×3(转 15° 卡入, IF-3)、顶部 35° 斜面数显窗真孔+卡扣+遮光筋(IF-4)、
     底座 3 颗螺丝柱(Ø2.5 盲孔)+3×(Ø2.5 通孔+Ø5 沉孔)。
  4. D 无摇头机构（导风靠 20° 定角百叶，免步进电机/齿轮）；底座内预留 Ø30 摇头电机安装位。
坐标约定（同 build_form_d.py）: X=高度(竖直), Y=前后(前=+Y), Z=左右(右=+Z)
  底座 x -0.026..0（Ø110），塔身 x 0..0.203（squircle Ø90，内腔 Ø84），总高 230mm。
复用注意（assembly_eng_notes.md §3 记录的圆柱轴向系统性 bug）：Blender 圆柱默认轴向 Z，
  本机 X=高度——电芯/风机轴/轮毂/螺丝柱/旋钮全部 rot=(0,π/2,0)；扇叶面内旋转用欧拉角逐件核对。
输出:
  cad/assembly_d.glb          — 37 个命名 mesh，extras 带 module/label/explode(glTF 坐标)
  cad/assembly_d_parts.json   — 格式对齐 assembly_a_parts.json
  cad/renders_assembly_eng_d/{assembled,exploded}.png + INSPECT=1 细节图
"""
import bpy
import math
import mathutils
import os
import json
import struct
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GLB_OUT = os.path.join(BASE_DIR, "assembly_d.glb")
PARTS_JSON = os.path.join(BASE_DIR, "assembly_d_parts.json")
RENDER_DIR = os.path.join(BASE_DIR, "renders_assembly_eng_d")
FAST = os.environ.get("FAST", "1") == "1"

# ================= 总体参数（外形沿用 build_form_d.py：Ø90×230，底座 Ø110） =================
SECTION_N = 4.0                 # squircle 超椭圆指数（专利规避：非正圆）
WALL = 0.002                    # 塔身壁厚 2.0mm（DFM）
DRAFT = math.tan(math.radians(1.5))   # 拔模 1.5°（沿 ±Y 脱模：分件面 y=0 大、前后面小）
R_TOWER = 0.045
R_BASE = 0.055
BASE_H = 0.026
FLARE_L = 0.045
BOSS_AT = [(0.048, 0.0), (-0.024, -0.0416), (-0.024, 0.0416)]   # 螺丝柱 (y,z)×3（环 r48：内让配重盘 r44，外让内腔 r52.9）
# 轴向堆叠（X，架构 §5.2 适配 230mm 塔高）
STACK = dict(tray=0.015, cell_x=0.051, strap=0.0765, pcb=0.088,
             fan=0.1125, tec=0.1475, sep_top=0.190)
GRILLE = dict(x0=0.100, x1=0.168, z=0.028, bars=10, tilt=20.0)   # 前横向百叶(真孔)
INTAKE = dict(x0=0.062, x1=0.098, z=0.024, bars=6)               # 后进风(真孔)
HOTVENT = dict(x0=0.110, x1=0.168, z=0.015, bars=5)              # 背部 pill 热排(真孔)
SLANT_ANG = 35.0
SLANT_P = Vector((0.194, 0.028, 0.0))
SLANT_N = Vector((math.cos(math.radians(SLANT_ANG)), math.sin(math.radians(SLANT_ANG)), 0.0))
SLANT_U = Vector((math.sin(math.radians(SLANT_ANG)), -math.cos(math.radians(SLANT_ANG)), 0.0))
SLANT_Q = SLANT_P + SLANT_U * 0.004      # 数显窗中心（斜面平面上）

# ================= 工具（同 build_core_eng.py / build_form_d.py 风格） =================
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

def boolean_op(target, cutter, operation="DIFFERENCE"):
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("bool_" + cutter.name, "BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

def boolean_cut(target, cutter):
    boolean_op(target, cutter, "DIFFERENCE")

def join_parts(name, objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]

def superellipse_pts(a, b, n, N=96, draft=False):
    """squircle 截面点 (y,z)；draft=True 时 z 随 |y| 线性收缩 = 侧壁 1.5° 拔模(±Y 脱模)"""
    pts = []
    for i in range(N):
        ang = 2 * math.pi * i / N
        c, s = math.cos(ang), math.sin(ang)
        py = math.copysign(abs(c) ** (2.0 / n), c) * a
        pz = math.copysign(abs(s) ** (2.0 / n), s) * b
        if draft:
            pz *= (1.0 - DRAFT * abs(py) / b)
        pts.append((py, pz))
    return pts

def prism(name, a, b, length, loc, mat=None, bevel_w=0.0, n=SECTION_N):
    """超椭圆截面棱柱（长轴 X，截面 YZ），沿用 build_form_d.py（无拔模：底座单独开模）"""
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

def tower_radius(x):
    if x >= FLARE_L:
        return R_TOWER
    return R_TOWER + (R_BASE - R_TOWER) * (1.0 - smoothstep(x / FLARE_L))

def loft(name, rings, mat, draft=False, n=SECTION_N, N=96):
    """变截面超椭圆放样；rings=[(x,a,b),...] 自下而上，两端封口；draft=侧壁 1.5° 拔模"""
    import bmesh
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bm = bmesh.new()
    all_rings = []
    for (x, a, b) in rings:
        pts = superellipse_pts(a, b, n, N, draft=draft)
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

# 7 段数码管字形（沿用 build_form_d.py，原点清零供旋转就位）
SEG_MAP = {
    "0": "top ul ur ll lr bot", "1": "ur lr", "2": "top ur mid ll bot",
    "3": "top ur mid lr bot", "4": "ul ur mid lr", "5": "top ul mid lr bot",
    "6": "top ul mid ll lr bot", "7": "top ur lr", "8": "top mid bot ul ur ll lr",
    "9": "top ul ur mid lr bot",
}

def build_display_text(text, mat):
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
    off = d.location.copy()
    for v in d.data.vertices:
        v.co += off
    d.location = (0, 0, 0)
    return d

def fill_empty_slots(obj):
    """boolean 刀具无材质会留下空槽（切面引用空槽=丢材质）：用本件首个非空材质回填"""
    mats = obj.data.materials
    if len(mats) == 0:
        return
    first = next((mt for mt in mats if mt is not None), None)
    if first is None:
        return
    for i in range(len(mats)):
        if mats[i] is None:
            mats[i] = first

# ================= 零件注册表（命名体系同 A：语义延续件同名，新增件同前缀） =================
SHELL_META = {
    "Base":           ("M1", "配重底座Ø110(3×Ø2.5通孔+Ø5沉孔+配重袋)"),
    "WeightPlate":    ("M1", "钢配重盘 Ø88×3(低重心F3)"),
    "SkidPad":        ("M1", "防滑硅胶圈(3×Ø8让位孔)"),
    "TypeC":          ("M1", "Type-C 进线口"),
    "M1_Bosses":      ("M1", "塔底螺丝柱×3(Ø2.5盲孔留4mm咬合)"),
    "M1_OscPad":      ("M1", "摇头电机预留安装位(Ø30+2×Ø2,D款不装)"),
    "ShellFront":     ("M6", "前壳(2mm壁+1.5°拔模+出风/数显真孔+分件线)"),
    "ShellRear":      ("M6", "后壳(2mm壁+1.5°拔模+进风/pill热排真孔)"),
    "Band":           ("M6", "薄荷腰线(外观分色)"),
    "GrilleFrame":    ("M6", "前百叶网罩框(旋扣母座)"),
    "GrilleLouvers":  ("M6", "横向百叶×10(定角20°,非放射辐条)"),
    "M6_TwistLock":   ("M6", "网罩旋扣×3(转15°卡入,IF-3)"),
    "IntakeGrille":   ("M5", "后进风横条×6(真孔嵌条)"),
    "HotVentPillar":  ("M5", "背部pill热排立柱框(造型化设计元素)"),
    "HotVentFins":    ("M5", "热排竖格栅×5(真孔嵌条)"),
    "DisplayGlass":   ("M7", "斜面数显窗 PMMA(搭接唇边2mm)"),
    "Display":        ("M7", "数码管字形 22.0(出风温度)"),
    "M7_Clip":        ("M7", "数显窗卡扣×4+遮光筋(IF-4)"),
    "M7_Module":      ("M7", "数码管模组(斜面背面)"),
    "Knob":           ("M3", "旋钮(100档FOC)"),
    "CoolKey":        ("M3", "制冷键"),
}
CORE_META = {
    "M5_TEC":        ("M5", "TEC 制冷片 40×40×3.8(冷面+Y/热面-Y)"),
    "M5_ColdFins":   ("M5", "冷端铝鳍片组(风道沿Y朝前百叶)"),
    "M5_HotSink":    ("M5", "热端铜鳍片组(风道沿Y朝背部pill)"),
    "M5_Separator":  ("M5", "L形全长中隔板(ADR-1,竖板+底翻边,带EVA槽)"),
    "M5_EVA":        ("M5", "EVA密封棉条×4(IF-2,3×1.5槽)"),
    "M5_ColdDuct":   ("M5", "冷风道(风机→冷鳍→前百叶贯通腔)"),
    "M5_HotDuct":    ("M5", "热风道导流(热鳍→背部pill立柱)"),
    "M4_FanFrame":   ("M4", "风机框 Ø80(轴向竖吹)"),
    "M4_FanHub":     ("M4", "轮毂+无刷电机(轴沿X)"),
    "M4_FanBlades":  ("M4", "扇叶 ×7"),
    "M2_Cell_A":     ("M2", "18650 电芯 A(竖放)"),
    "M2_Cell_B":     ("M2", "18650 电芯 B(竖放)"),
    "M2_Bracket":    ("M2", "电池仓(防反插+减震筋,IF-5)"),
    "M3_PCB":        ("M3", "主控 PCB(冷侧进风路径上)"),
    "M3_ICs":        ("M3", "主要 IC(MCU/驱动/充电)"),
    "M3_Pot":        ("M3", "旋钮电位器(顶部,走线开模阶段)"),
}

# 爆炸偏移（Blender 坐标系，任意方向向量自动归一化；轴向堆叠以 ±X 为主）
CENTER = Vector((0.10, 0.0, 0.0))
XP, XN, YP, YN, ZP, ZN = (1,0,0), (-1,0,0), (0,1,0), (0,-1,0), (0,0,1), (0,0,-1)
EXPLODE = {
    "Base": (XN, 0.090), "WeightPlate": (XN, 0.160), "SkidPad": (XN, 0.210),
    "M1_Bosses": (XN, 0.130), "M1_OscPad": (XN, 0.185), "TypeC": (YN, 0.120),
    "ShellFront": (YP, 0.150), "ShellRear": (YN, 0.150), "Band": (ZN, 0.120),
    "GrilleFrame": (YP, 0.230), "GrilleLouvers": (YP, 0.280), "M6_TwistLock": (YP, 0.330),
    "IntakeGrille": (YN, 0.230), "HotVentPillar": (YN, 0.280), "HotVentFins": (YN, 0.330),
    "DisplayGlass": ((0.819, 0.574, 0), 0.120), "Display": ((0.819, 0.574, 0), 0.155),
    "M7_Clip": ((0.819, 0.574, 0), 0.090), "M7_Module": ((0.819, 0.574, 0), 0.060),
    "Knob": (XP, 0.110), "CoolKey": (XP, 0.110), "M3_Pot": (XP, 0.080),
    "M5_TEC": (XP, 0.160),
    "M5_ColdFins": ((0.25, 1.0, 0), 0.150), "M5_HotSink": ((0.25, -1.0, 0), 0.150),
    "M5_Separator": (XP, 0.240), "M5_EVA": (XP, 0.280),
    "M5_ColdDuct": (ZP, 0.130), "M5_HotDuct": (ZN, 0.130),
    "M4_FanFrame": (XP, 0.100), "M4_FanHub": (XP, 0.100), "M4_FanBlades": ((1, 0, 0.45), 0.110),
    "M2_Bracket": (XN, 0.075), "M2_Cell_A": (ZP, 0.075), "M2_Cell_B": (ZN, 0.075),
    "M3_PCB": (XP, 0.035), "M3_ICs": (XP, 0.060),
}

# ================= 外壳（DFM 级重建） =================
def build_shell(m):
    parts = []
    # ---- 塔身壳体：外 loft(带 1.5° 拔模) − 内 loft = 2.0mm 薄壁 tub，再沿 Y=0 分前后壳 ----
    rings_out = []
    for x in (0.0, 0.006, 0.012, 0.020, 0.030, FLARE_L):
        r = tower_radius(x)
        rings_out.append((x, r, r))
    rings_out += [(0.100, R_TOWER, R_TOWER), (0.190, R_TOWER, R_TOWER),
                  (0.197, 0.0438, 0.0438), (0.2005, 0.0395, 0.0395),
                  (0.2030, 0.0320, 0.0320)]
    rings_in = [(0.002, tower_radius(0.002) - WALL, tower_radius(0.002) - WALL)]
    for x in (0.006, 0.012, 0.020, 0.030, FLARE_L, 0.100, 0.190):
        r = tower_radius(x) - WALL
        rings_in.append((x, r, r))
    rings_in += [(0.197, 0.0418, 0.0418), (0.2005, 0.0375, 0.0375), (0.2010, 0.0300, 0.0300)]
    outer = loft("outer", rings_out, None, draft=True)
    inner = loft("inner", rings_in, None, draft=True)
    boolean_cut(outer, inner)
    # 前后壳分件：前壳留 1.1mm 止口搭接（y≥-0.0008），后壳到 y=+0.0003 = 分件线
    front = outer
    front.name = "ShellFront"
    front.data.materials.append(m["BodyIvory"])
    rear = front.copy()
    rear.data = front.data.copy()
    rear.name = "ShellRear"
    bpy.context.collection.objects.link(rear)
    rear.data.materials.clear()
    rear.data.materials.append(m["BodyIvory"])
    boolean_op(front, box("cutter_half_f", (0.5, 0.5, 0.5), (0.10, 0.2492 + 0.0000, 0)),
               "INTERSECT")  # y ≥ -0.0008
    boolean_op(rear, box("cutter_half_r", (0.5, 0.5, 0.5), (0.10, -0.2497 + 0.0000, 0)),
               "INTERSECT")   # y ≤ +0.0003
    # 顶部 35° 斜面（两壳同切；切面平直着色）
    for sh in (front, rear):
        cutter = box("cutter_slant", (0.20, 0.20, 0.20), SLANT_P + SLANT_N * 0.10)
        cutter.rotation_euler = (0, 0, math.radians(SLANT_ANG))
        bpy.context.view_layer.objects.active = cutter
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        boolean_cut(sh, cutter)
    for p in front.data.polygons:
        if p.normal.dot(SLANT_N) > 0.9:
            p.use_smooth = False
    # ---- 前壳：百叶出风真孔（squircle 前平面贯通，圆角口） ----
    gr_x = (GRILLE["x0"] + GRILLE["x1"]) / 2
    boolean_cut(front, box("cutter_grille",
                           (GRILLE["x1"] - GRILLE["x0"], 0.030, GRILLE["z"] * 2),
                           (gr_x, R_TOWER - 0.012, 0), bevel=0.010, bevel_seg=5))
    # 旋扣母槽×3（开孔周缘贯通槽 10×10mm，IF-3）
    boolean_cut(front, box("cutter_lock_t", (0.010, 0.030, 0.010), (0.170, R_TOWER - 0.012, 0)))
    for sz in (1.0, -1.0):
        boolean_cut(front, box("cutter_lock_s", (0.010, 0.030, 0.010),
                               (gr_x, R_TOWER - 0.012, sz * 0.0305)))
    # 数显窗真孔（斜面贯通 26×44mm，窗框止口由玻璃唇边搭接）
    dw = box("cutter_disp", (0.014, 0.026, 0.044), SLANT_Q)
    dw.rotation_euler = (0, 0, math.radians(SLANT_ANG))
    bpy.context.view_layer.objects.active = dw
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    boolean_cut(front, dw)
    parts.append(front)
    # ---- 后壳：后进风真孔 + 背部 pill 热排真孔（长圆角=造型化立柱口） ----
    in_x = (INTAKE["x0"] + INTAKE["x1"]) / 2
    boolean_cut(rear, box("cutter_intake",
                          (INTAKE["x1"] - INTAKE["x0"], 0.030, INTAKE["z"] * 2),
                          (in_x, -R_TOWER + 0.012, 0), bevel=0.008, bevel_seg=4))
    hv_x = (HOTVENT["x0"] + HOTVENT["x1"]) / 2
    boolean_cut(rear, box("cutter_hotvent",
                          (HOTVENT["x1"] - HOTVENT["x0"], 0.030, HOTVENT["z"] * 2),
                          (hv_x, -R_TOWER + 0.012, 0), bevel=0.014, bevel_seg=6))
    parts.append(rear)
    # ---- 前网罩：框 + 横向百叶×10(定角20°) + 旋扣×3（已转 15° 锁止态） ----
    frame = box("GrilleFrame", (0.072, 0.004, 0.060), (gr_x, 0.0445, 0),
                mat=m["BodyIvory"], bevel=0.006, bevel_seg=4)
    boolean_cut(frame, box("cutter_gf", (0.064, 0.012, 0.052), (gr_x, 0.0445, 0),
                           bevel=0.009, bevel_seg=4))
    parts.append(frame)
    slats = []
    pitch = (GRILLE["x1"] - GRILLE["x0"]) / GRILLE["bars"]
    for i in range(GRILLE["bars"]):
        xx = GRILLE["x0"] + (i + 0.5) * pitch
        b = box("lv_%d" % i, (0.0035, 0.0022, GRILLE["z"] * 2 - 0.004),
                (xx, R_TOWER - 0.005, 0), mat=m["Grid"])
        b.rotation_euler = (0, 0, math.radians(GRILLE["tilt"]))
        slats.append(b)
    parts.append(join_parts("GrilleLouvers", slats))
    locks = []
    st = box("lk_stem_t", (0.002, 0.005, 0.003), (0.170, 0.0405, 0), mat=m["BodyIvory"])
    tb = box("lk_tab_t", (0.002, 0.0016, 0.012), (0.170, 0.0375, 0), mat=m["BodyIvory"])
    tb.rotation_euler = (0, math.radians(15), 0)
    locks += [st, tb]
    for sz in (1.0, -1.0):
        st = box("lk_stem_s", (0.003, 0.005, 0.002), (gr_x, 0.0405, sz * 0.0305), mat=m["BodyIvory"])
        tb = box("lk_tab_s", (0.012, 0.0016, 0.002), (gr_x, 0.0375, sz * 0.0305), mat=m["BodyIvory"])
        tb.rotation_euler = (0, math.radians(15), 0)
        locks += [st, tb]
    parts.append(join_parts("M6_TwistLock", locks))
    # ---- 后进风横条 + pill 热排立柱框 + 竖格栅（真孔内嵌条，条间真实开口） ----
    bars = []
    pitch = (INTAKE["x1"] - INTAKE["x0"]) / INTAKE["bars"]
    for i in range(INTAKE["bars"]):
        xx = INTAKE["x0"] + (i + 0.5) * pitch
        bars.append(box("in_%d" % i, (0.0035, 0.0022, INTAKE["z"] * 2 - 0.006),
                        (xx, -R_TOWER + 0.005, 0), mat=m["Grid"]))
    parts.append(join_parts("IntakeGrille", bars))
    pillar = box("HotVentPillar", (0.066, 0.004, 0.038), (hv_x, -0.0445, 0),
                 mat=m["BodyIvory"], bevel=0.006, bevel_seg=4)
    boolean_cut(pillar, box("cutter_hp", (0.058, 0.012, 0.030), (hv_x, -0.0445, 0),
                            bevel=0.013, bevel_seg=6))
    parts.append(pillar)
    fins = []
    pitch = (HOTVENT["z"] * 2 - 0.006) / HOTVENT["bars"]
    for i in range(HOTVENT["bars"]):
        zz = -HOTVENT["z"] + 0.003 + (i + 0.5) * pitch
        fins.append(box("hv_%d" % i, (HOTVENT["x1"] - HOTVENT["x0"] - 0.010, 0.0022, 0.0035),
                        (hv_x, -R_TOWER + 0.005, zz), mat=m["Grid"]))
    parts.append(join_parts("HotVentFins", fins))
    # ---- 数显：斜面窗孔内 PMMA 玻璃 + 数码管 + 卡扣×4 + 遮光筋（IF-4） ----
    glass = box("DisplayGlass", (0.0016, 0.028, 0.046), (0, 0, 0),
                mat=m["GlassDark"], bevel=0.0007, bevel_seg=3)
    glass.rotation_euler = (0, 0, math.radians(SLANT_ANG))
    glass.location = SLANT_Q + SLANT_N * 0.0002
    parts.append(glass)
    digits = build_display_text("22.0", m["DigitGlow"])
    digits.rotation_euler = (0, 0, math.radians(SLANT_ANG) - math.pi / 2)   # +Y→n, +X→u
    digits.location = SLANT_Q - SLANT_N * 0.0035
    parts.append(digits)
    # 遮光筋整圈（窗孔背面 1.2×3mm）+ 卡扣×4，先建局部系(法线=局部X)再旋转就位
    clips = []
    clips.append(box("rib_u0", (0.003, 0.0012, 0.048), (0, -0.0144, 0), mat=m["BodyIvory"]))
    clips.append(box("rib_u1", (0.003, 0.0012, 0.048), (0, 0.0144, 0), mat=m["BodyIvory"]))
    clips.append(box("rib_z0", (0.003, 0.030, 0.0012), (0, 0, -0.0234), mat=m["BodyIvory"]))
    clips.append(box("rib_z1", (0.003, 0.030, 0.0012), (0, 0, 0.0234), mat=m["BodyIvory"]))
    for dy in (-0.012, 0.012):
        for dz in (-0.020, 0.020):
            clips.append(box("clip", (0.0026, 0.004, 0.002), (-0.001, dy, dz),
                             mat=m["BodyIvory"], bevel=0.0005))
    clip = join_parts("M7_Clip", clips)
    off = clip.location.copy()
    for v in clip.data.vertices:
        v.co += off
    clip.location = (0, 0, 0)
    clip.rotation_euler = (0, 0, math.radians(SLANT_ANG))
    clip.location = SLANT_Q - SLANT_N * 0.0042
    parts.append(clip)
    modu = box("M7_Module", (0.006, 0.030, 0.048), (0, 0, 0), mat=m["ICBlack"], bevel=0.0015)
    modu.rotation_euler = (0, 0, math.radians(SLANT_ANG))
    modu.location = SLANT_Q - SLANT_N * 0.009
    parts.append(modu)
    # ---- 底座：Ø110 配重盘(配重袋+3×Ø2.5通孔+Ø5沉孔) + 硅胶圈 + Type-C + 摇头预留位 ----
    base = prism("Base", R_BASE, R_BASE, BASE_H - 0.005, (-(BASE_H - 0.005) / 2, 0, 0),
                 mat=m["BodyIvory"], bevel_w=0.004)
    # 顶部配重袋（Ø89 深 5mm，钢配重盘沉入，塔身底面盖住）
    boolean_cut(base, cyl("cutter_pocket", 0.0445, 0.006, (-0.002, 0, 0), rot=(0, math.pi / 2, 0)))
    for i, (by, bz) in enumerate(BOSS_AT):
        boolean_cut(base, cyl("cutter_screw_%d" % i, 0.00125, 0.030, (-0.006, by, bz), rot=(0, math.pi / 2, 0)))
        boolean_cut(base, cyl("cutter_sink_%d" % i, 0.0025, 0.004, (-0.019, by, bz), rot=(0, math.pi / 2, 0)))
    parts.append(base)
    parts.append(prism("WeightPlate", 0.044, 0.044, 0.003, (-0.003, 0, 0), mat=m["CellSteel"]))
    skid = prism("SkidPad", R_BASE - 0.002, R_BASE - 0.002, 0.006, (-BASE_H + 0.003, 0, 0),
                 mat=m["FrameDark"])
    for i, (by, bz) in enumerate(BOSS_AT):
        boolean_cut(skid, cyl("cutter_skid_%d" % i, 0.004, 0.008, (-0.023, by, bz), rot=(0, math.pi / 2, 0)))
    parts.append(skid)
    parts.append(box("TypeC", (0.006, 0.003, 0.010), (-0.012, -R_BASE + 0.0005, 0),
                     mat=m["VoidDark"], bevel=0.0015, bevel_seg=3))
    # 塔底螺丝柱×3（立于塔身底壁 x0.002 上，Ø2.5 盲孔留 4mm 咬合料）
    bosses = []
    for i, (by, bz) in enumerate(BOSS_AT):
        bo = cyl("boss_%d" % i, 0.004, 0.012, (0.008, by, bz), rot=(0, math.pi / 2, 0), mat=m["BodyIvory"])
        boolean_cut(bo, cyl("cutter_boss_%d" % i, 0.00125, 0.010, (0.0055, by, bz), rot=(0, math.pi / 2, 0)))
        bosses.append(bo)
    parts.append(join_parts("M1_Bosses", bosses))
    # 摇头电机预留安装位（Ø30 环+2×Ø2 定位孔；D 款固定式不装电机，免步进/同步电机）
    pad = cyl("M1_OscPad", 0.015, 0.002, (-0.0005, 0, 0), rot=(0, math.pi / 2, 0), mat=m["Bracket"])
    boolean_cut(pad, cyl("cutter_pad_c", 0.008, 0.004, (-0.0005, 0, 0), rot=(0, math.pi / 2, 0)))
    for sy in (1.0, -1.0):
        boolean_cut(pad, cyl("cutter_pad_h", 0.001, 0.004, (-0.0005, sy * 0.011, 0), rot=(0, math.pi / 2, 0)))
    parts.append(pad)
    # ---- 薄荷腰线（flare 结束处整圈，品牌基因/附加区分层） ----
    parts.append(prism("Band", 0.047, 0.047, 0.006, (0.052, 0, 0), mat=m["BandMint"]))
    # ---- 顶部后区：旋钮 + 制冷键（沿用白模语言；轴沿 X 竖直） ----
    knob = cyl("knob_body", 0.013, 0.010, (0.2020, -0.010, 0.000), rot=(0, math.pi / 2, 0), mat=m["FrameDark"])
    cap = cyl("knob_cap", 0.013 * 0.82, 0.002, (0.2070, -0.010, 0.000), rot=(0, math.pi / 2, 0), mat=m["Aluminum"])
    mark = box("knob_mark", (0.0012, 0.008, 0.0022), (0.2073, -0.0165, 0.000), mat=m["VoidDark"])
    parts.append(join_parts("KnobAsm", [knob, cap, mark]))
    parts[-1].name = "Knob"
    ck = cyl("ck_body", 0.007, 0.006, (0.2025, -0.010, 0.026), rot=(0, math.pi / 2, 0), mat=m["FrameDark"])
    dot = cyl("ck_dot", 0.007 * 0.45, 0.0015, (0.2057, -0.010, 0.026), rot=(0, math.pi / 2, 0), mat=m["BandMint"])
    parts.append(join_parts("CoolKeyAsm", [ck, dot]))
    parts[-1].name = "CoolKey"
    return parts

# ================= 内部核心（轴向竖直堆叠 + 双风道真实化 + 密封） =================
def build_core(m):
    parts = []
    TX = STACK["tec"]           # TEC 三明治 X 中心 0.1475（冷面 +Y / 热面 -Y）
    # ---- M5 热模块：TEC 40×40×3.8（法线 Y，冷面 +Y 朝前百叶 / 热面 -Y 朝背部 pill） ----
    parts.append(box("M5_TEC", (0.040, 0.0038, 0.040), (TX, 0, 0), mat=m["TEC"], bevel=0.0006))
    # 冷端：基板(y 0.0019..0.0059) + 8 鳍（板薄沿 Z，风道沿 Y 贯通朝前百叶）
    cf = [box("cf_base", (0.040, 0.004, 0.040), (TX, 0.0039, 0), mat=m["AluFin"])]
    for i in range(8):
        z = -0.0175 + i * 0.005
        cf.append(box("cf_%d" % i, (0.040, 0.018, 0.001), (TX, 0.0149, z), mat=m["AluFin"]))
    parts.append(join_parts("M5_ColdFins", cf))
    # 热端：基板(y -0.0059..-0.0019) + 9 鳍（板薄沿 Z，风道沿 Y 朝背部 pill 立柱）
    hs = [box("hs_base", (0.040, 0.004, 0.040), (TX, -0.0039, 0), mat=m["Copper"])]
    for i in range(9):
        z = -0.016 + i * 0.004
        hs.append(box("hs_%d" % i, (0.040, 0.016, 0.0012), (TX, -0.0139, z), mat=m["Copper"]))
    parts.append(join_parts("M5_HotSink", hs))
    # ---- L 形全长中隔板（ADR-1）：竖板(X-Z@y=-0.002, x0.125..0.190) + 底翻边(Y-Z@x=0.125) ----
    # 尺寸受 squircle 内腔约束：竖板 z±0.038（侧壁 z0.0429），翻边 z±0.028（背壁转角内收），
    # 密封肋仅嵌入壁厚内（不穿外皮）——R4 曾全宽穿出背壁/侧壁，已修。
    sep = [box("sep_main", (0.065, 0.0016, 0.076), (0.1575, -0.002, 0), mat=m["SepBoard"]),
           box("sep_flange", (0.0016, 0.040, 0.056), (0.125, -0.022, 0), mat=m["SepBoard"])]
    # (名字, 肋尺寸, 肋中心, 槽刀尺寸, 槽刀中心, EVA尺寸, EVA中心) — 槽 3mm 宽 ×1.5mm 深
    ribs = [
        ("rib_t", (0.004, 0.0016, 0.076), (0.192, -0.002, 0),           # 竖板顶边（肋面 x=0.194）
         (0.0015, 0.003, 0.076), (0.19325, -0.002, 0),
         (0.0009, 0.0024, 0.075), (0.1942, -0.002, 0)),
        ("rib_zp", (0.065, 0.0016, 0.004), (0.1575, -0.002, 0.040),     # 竖板右边（肋面 z=0.042）
         (0.065, 0.003, 0.0015), (0.1575, -0.002, 0.04125),
         (0.064, 0.0024, 0.0009), (0.1575, -0.002, 0.0422)),
        ("rib_zn", (0.065, 0.0016, 0.004), (0.1575, -0.002, -0.040),    # 竖板左边
         (0.065, 0.003, 0.0015), (0.1575, -0.002, -0.04125),
         (0.064, 0.0024, 0.0009), (0.1575, -0.002, -0.0422)),
        ("rib_bk", (0.0016, 0.004, 0.048), (0.125, -0.041, 0),          # 翻边后边（肋面 y=-0.043；z 限 ±0.024：squircle 背面随 |z| 内收，直条全长会穿出外皮）
         (0.0016, 0.0015, 0.048), (0.125, -0.04225, 0),
         (0.0014, 0.0009, 0.036), (0.125, -0.0433, 0)),
    ]
    eva = []
    for nm, rs, rc, gs, gc, es, ec in ribs:
        rib = box(nm, rs, rc, mat=m["SepBoard"])
        boolean_cut(rib, box("g_" + nm, gs, gc))
        sep.append(rib)
        # EVA 棉条：嵌槽内、外凸 ~0.5mm（与壳体内壁压缩量示意）
        eva.append(box("eva_" + nm, es, ec, mat=m["EVA"]))
    sepall = join_parts("M5_Separator", sep)
    # TEC 窗（冷/热基板穿过，2mm 间隙）
    boolean_cut(sepall, box("cutter_sepwin", (0.044, 0.010, 0.044), (TX, -0.002, 0)))
    parts.append(sepall)
    parts.append(join_parts("M5_EVA", eva))
    # ---- 冷风道（M5_ColdDuct）：左右颊板 + 前下挡板(防短路) + 顶板 = 风机→冷鳍→前百叶贯通腔 ----
    duct = [box("duct_cz_p", (0.070, 0.036, 0.0016), (0.137, 0.024, 0.021), mat=m["DuctWall"]),
            box("duct_cz_n", (0.070, 0.036, 0.0016), (0.137, 0.024, -0.021), mat=m["DuctWall"]),
            box("duct_front", (0.0275, 0.0016, 0.0436), (0.11375, 0.020, 0), mat=m["DuctWall"]),
            box("duct_ceil", (0.0016, 0.036, 0.0436), (0.1712, 0.024, 0), mat=m["DuctWall"])]
    parts.append(join_parts("M5_ColdDuct", duct))
    # ---- 热风道导流（M5_HotDuct）：热鳍 → 背部 pill 立柱的两侧挡板 + 顶板 ----
    hd = [box("hd_cz_p", (0.045, 0.036, 0.0016), (0.1475, -0.024, 0.0175), mat=m["DuctWall"]),
          box("hd_cz_n", (0.045, 0.036, 0.0016), (0.1475, -0.024, -0.0175), mat=m["DuctWall"]),
          box("hd_ceil", (0.0016, 0.036, 0.0366), (0.1712, -0.024, 0), mat=m["DuctWall"])]
    parts.append(join_parts("M5_HotDuct", hd))
    # ---- M4 动力：Ø80 轴流无刷风机（轴沿 X，向 +X 竖吹，后进风静压腔上方） ----
    fc = (STACK["fan"], 0, 0)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.0385, minor_radius=0.0022,
                                     major_segments=48, minor_segments=12, location=fc)
    frame = bpy.context.active_object
    frame.name = "M4_FanFrame"
    frame.rotation_euler = (0, math.pi / 2, 0)      # 环面轴线 Z→X
    frame.data.materials.append(m["FanDark"])
    parts.append(frame)
    parts.append(cyl("M4_FanHub", 0.012, 0.020, fc, rot=(0, math.pi / 2, 0), mat=m["FanDark"]))
    blades = []
    for i in range(7):
        a = i * 2 * math.pi / 7
        r = 0.0255
        bl = box("bl_%d" % i, (0.003, 0.026, 0.015),
                 (fc[0], r * math.cos(a), r * math.sin(a)), mat=m["BladeDark"])
        bl.rotation_euler = (a, 0.55, 0.0)          # 面内径向 + 35° 桨距
        blades.append(bl)
    parts.append(join_parts("M4_FanBlades", blades))
    # ---- M2 能源：2×18650 竖放（轴沿 X，x0.0185..0.0835）+ 电池仓（防反插+减震筋, IF-5） ----
    for tag, zz in (("A", 0.011), ("B", -0.011)):
        cell = [cyl("cell_%s" % tag, 0.009, 0.065, (STACK["cell_x"], 0.004, zz),
                    rot=(0, math.pi / 2, 0), mat=m["CellWrap"]),
                cyl("cellcap_%s" % tag, 0.0085, 0.0015, (0.0843, 0.004, zz),
                    rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
        parts.append(join_parts("M2_Cell_%s" % tag, cell))
    strap = box("br_strap", (0.002, 0.048, 0.052), (STACK["strap"], 0.004, 0), mat=m["Bracket"])
    for zz in (0.011, -0.011):                       # strap 2×Ø17 过孔：电芯肩定位、正极帽穿出
        boolean_cut(strap, cyl("cutter_strap", 0.0085, 0.006, (STACK["strap"], 0.004, zz),
                               rot=(0, math.pi / 2, 0)))
    br = [box("br_tray", (0.002, 0.048, 0.052), (0.015, 0.004, 0), mat=m["Bracket"]),
          box("br_side1", (0.060, 0.048, 0.002), (0.046, 0.004, 0.0225), mat=m["Bracket"]),
          box("br_side2", (0.060, 0.048, 0.002), (0.046, 0.004, -0.0225), mat=m["Bracket"]),
          box("br_end1", (0.060, 0.002, 0.047), (0.046, -0.019, 0), mat=m["Bracket"]),
          box("br_end2", (0.060, 0.002, 0.047), (0.046, 0.027, 0), mat=m["Bracket"]),
          strap,
          # 防反插：端壁单侧键位凸台（不对称）+ 偏心 JST 座
          box("br_key", (0.004, 0.008, 0.006), (0.079, 0.024, 0.014), mat=m["Bracket"]),
          box("br_jst", (0.008, 0.008, 0.006), (0.080, -0.012, -0.016), mat=m["ICBlack"]),
          # 减震筋 ×3（两侧壁+仓底 EVA 凸筋，与电芯 0.5mm 压缩量）
          box("br_r1", (0.054, 0.030, 0.0012), (0.046, 0.004, 0.0212), mat=m["EVA"]),
          box("br_r2", (0.054, 0.030, 0.0012), (0.046, 0.004, -0.0212), mat=m["EVA"]),
          box("br_r3", (0.001, 0.040, 0.040), (0.0165, 0.004, 0), mat=m["EVA"]),
          # BMS 保护板
          box("br_bms", (0.030, 0.018, 0.0016), (0.046, 0.004, 0.0243), mat=m["PCBGreen"])]
    parts.append(join_parts("M2_Bracket", br))
    # ---- M3 主控：PCB（横置，电池仓上方冷侧进风路径）+ IC + 顶部旋钮电位器 ----
    parts.append(box("M3_PCB", (0.0016, 0.056, 0.056), (STACK["pcb"], 0.004, 0),
                     mat=m["PCBGreen"], bevel=0.002))
    px = STACK["pcb"] + 0.0018
    ics = [box("ic_mcu", (0.002, 0.012, 0.012), (px, -0.006, -0.010), mat=m["ICBlack"]),
           box("ic_drv", (0.002, 0.010, 0.010), (px, 0.012, 0.012), mat=m["ICBlack"]),
           box("ic_chg", (0.002, 0.008, 0.008), (px, -0.008, 0.014), mat=m["ICBlack"]),
           box("ic_usbc", (0.003, 0.006, 0.010), (px + 0.0005, 0.016, -0.014), mat=m["CellSteel"])]
    parts.append(join_parts("M3_ICs", ics))
    pot = [cyl("pot_body", 0.0085, 0.012, (0.194, -0.010, 0.0), rot=(0, math.pi / 2, 0), mat=m["FanDark"]),
           cyl("pot_shaft", 0.003, 0.012, (0.200, -0.010, 0.0), rot=(0, math.pi / 2, 0), mat=m["CellSteel"])]
    parts.append(join_parts("M3_Pot", pot))
    return parts

# ================= 爆炸向量 / GLB 核验（同 build_core_eng.py，支持任意方向向量） =================
def part_centroid(obj):
    return obj.matrix_world.translation.copy()

def explode_vec(name, obj):
    if name in EXPLODE:
        d, mag = EXPLODE[name]
        return Vector(d).normalized() * mag
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
TARGET = Vector((0.095, 0.0, 0.0))

def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 480 if FAST else 768
    scene.render.resolution_y = 640 if FAST else 1024
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
    add_area("KeyLight", (0.45, 0.40, 0.35), 4.0)
    add_area("FillLight", (0.20, -0.15, -0.55), 1.5)
    add_area("RimLight", (0.55, -0.45, 0.25), 2.5)
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
    }

# ================= 主流程 =================
def main():
    scene = setup_scene()
    m = make_mats()
    shell = build_shell(m)
    core = build_core(m)

    meta = dict(SHELL_META)
    meta.update(CORE_META)
    for o in bpy.data.objects:
        if o.type == "MESH":
            fill_empty_slots(o)
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
        json.dump({"glb": "cad/assembly_d.glb", "parts": records}, f, ensure_ascii=False, indent=1)
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
    for nm in ("ShellFront", "ShellRear", "Base"):
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
    ac = new_mat("AirCold", (0.10, 0.55, 0.95, 1), 0.0, 0.4,
                 emission=(0.10, 0.55, 0.95, 1), emission_strength=1.5)
    ah = new_mat("AirHot", (0.95, 0.30, 0.12, 1), 0.0, 0.4,
                 emission=(0.95, 0.30, 0.12, 1), emission_strength=1.5)
    arrows = [
        arrow("Airflow_Cold_in", (0.080, -0.075, 0.0), (0.080, -0.012, 0.0), ac),
        arrow("Airflow_Cold_up", (0.095, -0.005, 0.0), (0.140, -0.005, 0.0), ac),
        arrow("Airflow_Cold_out", (0.145, 0.008, 0.0), (0.145, 0.080, 0.0), ac),
        arrow("Airflow_Hot_out", (0.145, -0.014, 0.0), (0.145, -0.080, 0.0), ah),
    ]

    def shoot(name, loc, target, lens=55, up_hint=Vector((1.0, 0.0, 0.0))):
        bpy.ops.object.camera_add(location=loc)
        cam = bpy.context.active_object
        cam.data.lens = lens
        fwd = (Vector(target) - Vector(loc)).normalized()
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
        scene.camera = cam
        scene.render.filepath = os.path.join(RENDER_DIR, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED:", scene.render.filepath)
        bpy.data.objects.remove(cam, do_unlink=True)

    shoot("assembled", (0.42, 0.42, 0.48), TARGET)

    if os.environ.get("INSPECT") == "1":
        # 半透检查视角：分层堆叠 / 双风道 / 隔板密封 / 电池仓
        shoot("inspect_right", (0.10, 0.02, 0.62), TARGET)                 # 右侧半透：竖向分层可读
        shoot("inspect_back_ghost", (0.30, -0.42, -0.30), TARGET)          # 后半透：热腔/pill/翻边
        shoot("inspect_separator", (0.20, 0.30, 0.35), (0.150, -0.005, 0)) # 隔板+TEC窗+EVA槽
        shoot("inspect_battery", (0.02, 0.32, 0.30), (0.050, 0.0, 0))      # 电池仓/PCB/风机
        # 恢复不透明材质，拍外观/真孔/DFM 细节
        for nm, src in trans_mats.items():
            bpy.data.objects[nm].data.materials[0] = src
        for a in arrows:
            a.hide_render = True
        scene.view_settings.exposure = 0.1
        shoot("inspect_ext_front", (0.10, 0.60, 0.0), TARGET)
        shoot("inspect_ext_back", (0.10, -0.60, 0.0), TARGET)
        shoot("inspect_front_close", (0.134, 0.30, 0.06), (0.134, 0.040, 0.0))
        shoot("inspect_disp_close", (0.40, 0.28, 0.10), (0.196, 0.025, 0.0))
        shoot("inspect_back_close", (0.139, -0.30, 0.06), (0.139, -0.040, 0.0))
        shoot("inspect_base_bottom", (-0.32, 0.10, 0.15), (-0.010, 0.0, 0.0))
        print("INSPECT DONE")
        return

    # ---- 渲染 2：爆炸态（竖向爆炸为主） ----
    for a in arrows:
        a.hide_render = True
    moved = []
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name in meta:
            v = explode_vec(o.name, o)
            o.location += v
            moved.append((o, v))
    shoot("exploded", (0.70, 0.78, 0.90), (0.10, 0.0, 0.0), lens=50)
    for o, v in moved:
        o.location -= v
    print("ALL DONE")

main()
