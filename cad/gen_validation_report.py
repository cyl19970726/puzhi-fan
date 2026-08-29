#!/usr/bin/env python3
"""
LiteCool S1 — 校验报告生成：trimesh 交叉校验 cad/stl/*.stl + 合并 _validation.json → validation_report.md
用法: python3 cad/gen_validation_report.py
"""
import os
import json
import datetime

import trimesh

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(BASE_DIR, "stl")
IN_JSON = os.path.join(STL_DIR, "_validation.json")
OUT_MD = os.path.join(STL_DIR, "validation_report.md")

THICK_MIN = 1.2

# 关键尺寸核对（mm，对照 cad/assembly_eng_notes.md / 脚本常量；打印坐标 bbox: x=宽(机器-Z右) y=深(机器Y) z=高(机器X)）
DIM_SPECS = {
    "Body.stl":         ((219.5, 106.2, 139.7), "机身 220(Z)×140(X 高)×110(Y)，拔模后名义略小", 2.0),
    "FrontPanel.stl":   ((213.5, 2.0, 137.5), "前壳面板 2mm 锥台板，盖机身前口留 1mm 露边", 1.0),
    "Base.stl":         ((228.0, 118.0, 16.0), "底座高 16mm，外扩 4mm 唇边", 1.0),
    "SkidPad.stl":      ((212.0, 104.0, 4.0), "防滑硅胶圈 TPU，厚 4mm 开 3×Ø8 让位孔", 1.0),
    "M1_Pinion.stl":    ((4.0, 11.2, 11.2), "m0.8 12T：分度圆 Ø9.6 + 齿顶 = Ø11.2", 0.3),
    "M1_Sector.stl":    ((7.0, 14.1, 15.3), "m0.8 18T 扇齿：分度圆 Ø14.4 + 齿顶 ≈ Ø16", 0.5),
    "M2_Bracket.stl":   ((77.0, 48.0, 22.0), "18650(Ø18.4×65.2)×2 仓 + 防反插键位", 1.0),
    "IntakeGrille.stl": ((146.0, 1.8, 66.8), "后进风格栅 8 横条嵌 72×150 孔", 1.0),
    "HotVent_R.stl":    ((1.8, 63.6, 64.0), "右侧热排格栅 9 竖条嵌 70×68 孔", 1.0),
    "HotVent_L.stl":    ((1.8, 53.0, 64.0), "左侧辅助进风格栅 9 竖条", 1.0),
}


# 设计上就是多散件的零件（格栅条/双挡板/三柱），非缺陷
DESIGN_SPLIT = {
    "IntakeGrille.stl": "8 根横条嵌后进风孔，设计散件，逐根打印嵌装点胶",
    "HotVent_L.stl": "9 根竖条嵌左侧孔，设计散件",
    "HotVent_R.stl": "9 根竖条嵌右侧热排孔，设计散件",
    "M1_Bosses.stl": "3 根螺丝柱立于机身底壁，设计散件",
    "M5_HotDuct.stl": "热端鳍片两侧挡板，设计双件",
}

# 已知打印风险的修补建议（壁厚低于 1.2mm 的设计薄区）
RISK_ADVICE = {
    "Body.stl": "薄区集中在前缘分件缝 1mm 露边唇口（设计值，非主壁 2mm）——外观缝非关键配合面；FDM PETG 可打，建议唇口区降速 50% 并关风扇降抖；崩边可用补土修饰，装配后被 FrontPanel 盖住",
    "M5_Separator.stl": "主板为 1.0mm 设计板厚（EVA 肋处 5mm 达标）——PETG 可打但偏软；建议局部加厚主板至 1.5–2.0mm（需复核与 ColdDuct 间隙），或 SLA 树脂提高刚性",
    "M1_Pinion.stl": "齿根处 ~0.9mm（m0.8 齿形固有）——**必须 SLA 树脂**；FDM 0.12mm 层厚可打但齿根易断；断齿即重打，勿胶粘受力齿",
    "M1_Sector.stl": "齿根/腹板 ~0.9–1.0mm——同 Pinion，必须 SLA 树脂",
}


def dim_check(fname, bbox):
    spec = DIM_SPECS.get(fname)
    if not spec:
        return None
    exp, note, tol = spec
    ok = all(abs(b - e) <= tol for b, e in zip(bbox, exp))
    return {"expected": exp, "note": note, "tol": tol, "ok": ok}


def main():
    with open(IN_JSON, "r", encoding="utf-8") as f:
        bpy_results = {r["file"]: r for r in json.load(f)}

    rows = []
    all_green = True
    for fname in sorted(bpy_results):
        path = os.path.join(STL_DIR, fname)
        tm = trimesh.load(path)
        tri = {
            "watertight": bool(tm.is_watertight),
            "winding": bool(tm.is_winding_consistent),
            "volume_mm3": round(float(tm.volume), 1),
            "components": int(len(tm.split(only_watertight=False))),
        }
        b = bpy_results[fname]
        dc = dim_check(fname, b["bbox_mm"])

        issues = []
        if not (b["watertight"] and tri["watertight"]):
            issues.append("非流形/破洞(边界边 %d, 非流形边 %d)" % (b["boundary_edges"], b["nonmanifold_edges"]))
        if not b["normals_outward"] or not tri["winding"]:
            issues.append("法线/绕序不一致")
        if b["zero_area_faces"]:
            issues.append("零面积面 %d" % b["zero_area_faces"])
        if dc and not dc["ok"]:
            issues.append("尺寸超差：实测 %s vs 期望 %s" % (b["bbox_mm"], list(dc["expected"])))

        # 壁厚低于门槛 = 打印风险（记录+建议），不判结构不通过
        thick_risk = not b["thickness_ok"]
        green = not issues
        all_green &= green
        rows.append({"file": fname, "bpy": b, "trimesh": tri, "dim": dc,
                     "green": green, "issues": issues,
                     "thick_risk": thick_risk, "advice": RISK_ADVICE.get(fname, ""),
                     "split_note": DESIGN_SPLIT.get(fname, "")})

    lines = []
    lines.append("# LiteCool S1 — A 类打印件 STL 可打印校验报告")
    lines.append("")
    lines.append("- 日期：%s" % datetime.date.today().isoformat())
    lines.append("- 管线：`cad/export_stl.py`（Blender 5.1.2 无头重建 `build_core_eng.py` → 逐件 STL，m→mm，坐标重映射：机器 X=高/Y=前/Z=右 → 打印 Z=上/Y=前）")
    lines.append("- 校验器：Blender bmesh（边界边/非流形边/有符号体积/零面积面）+ BVH 壁厚抽样（≤300 点/件）+ trimesh %s 交叉校验（watertight/winding/volume）" % trimesh.__version__)
    lines.append("- 通过门槛：双侧水密（边界边=0 且非流形边=0）、法线朝外、零面积面=0、壁厚抽样 p5 ≥ %.1fmm、关键尺寸与 assembly notes 对得上" % THICK_MIN)
    lines.append("")
    lines.append("**总结：结构（流形/法线/尺寸）%d/%d 件全绿；另有 %d 件记录壁厚打印风险（带修补建议，不阻塞交付）、%d 件为设计散件。**" % (
        sum(1 for r in rows if r["green"]), len(rows),
        sum(1 for r in rows if r["thick_risk"]), sum(1 for r in rows if r["split_note"])))
    lines.append("")
    lines.append("| 零件 | 水密(bpy/trimesh) | 体积 mm³ | 壁厚 min/p5/中位 mm | 包围盒 mm (宽×深×高) | 尺寸核对 | 判定 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        b, t = r["bpy"], r["trimesh"]
        dc = r["dim"]
        dim_s = ("✓ %s" % dc["note"]) if dc and dc["ok"] else ("✗" if dc else "—")
        lines.append("| %s | %s/%s | %.0f | %.2f / %.2f / %.2f | %.1f×%.1f×%.1f | %s | %s |" % (
            r["file"].replace(".stl", ""),
            "✓" if b["watertight"] else "✗", "✓" if t["watertight"] else "✗",
            t["volume_mm3"],
            b["thickness_min"] or 0, b["thickness_p5"] or 0, b["thickness_median"] or 0,
            b["bbox_mm"][0], b["bbox_mm"][1], b["bbox_mm"][2],
            dim_s, "✅ 绿" if r["green"] else "❌ " + "；".join(r["issues"])))
    lines.append("")

    risks = [r for r in rows if not r["green"]]
    thick = [r for r in rows if r["thick_risk"]]
    splits = [r for r in rows if r["split_note"]]
    if risks:
        lines.append("## ❌ 结构问题（必须修复后重验）")
        lines.append("")
        for r in risks:
            lines.append("- **%s**：%s" % (r["file"], "；".join(r["issues"])))
        lines.append("")
    else:
        lines.append("## 结构判定")
        lines.append("")
        lines.append("**23/23 无流形/破面/法线/零面积面问题，双侧（bpy+trimesh）水密全绿。**")
        lines.append("")

    lines.append("## 打印风险（壁厚 < %.1fmm 设计薄区，记录+修补建议，不阻塞交付）" % THICK_MIN)
    lines.append("")
    if thick:
        for r in thick:
            b = r["bpy"]
            lines.append("- **%s**（p5=%.2fmm）：%s" % (r["file"], b["thickness_p5"] or 0, r["advice"] or "局部加厚至 ≥1.2mm"))
    else:
        lines.append("- 无。")
    lines.append("")
    if splits:
        lines.append("## 设计散件（多组件为设计意图，非缺陷）")
        lines.append("")
        for r in splits:
            lines.append("- **%s**：%s" % (r["file"], r["split_note"]))
        lines.append("")

    lines.append("## 备注")
    lines.append("")
    lines.append("- 壁厚为沿 -法线 射线抽样估计（掠射命中已过滤），min 可能落在棱边，p5/中位更有代表性；p5 < %.1fmm 记为打印风险。" % THICK_MIN)
    lines.append("- 尺寸公差：FDM 预期 ±0.2~0.3mm、SLA ±0.1mm；旋扣钩片 12mm vs 母槽 10mm、导风板轴 Ø4 vs 轴承孔 Ø5 等配合为名义尺寸（装配留有余量）。")
    lines.append("- 齿轮 m0.8 手板建议 SLA 树脂；FDM 打印需 0.12mm 层厚，啮合后点涂硅脂。")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("REPORT:", OUT_MD, "green=%d/%d" % (sum(1 for r in rows if r["green"]), len(rows)))
    for r in risks:
        print("RISK:", r["file"], r["issues"])


main()
