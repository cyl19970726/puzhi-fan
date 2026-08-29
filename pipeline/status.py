"""pipeline/status.py — 汇总各阶段状态 → data/pipeline_status.json。

状态判定 = 产物存在性 + 闸结果（validate.run_checks()）+ 人工事实（从数据层推导）。
诚实标注：产物在但闸未过 = 🟡 部分完成，不标 ✅。

用法: python3 pipeline/status.py
"""
import datetime
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stages import REPO_ROOT, STAGES, rp  # noqa: E402
import validate  # noqa: E402

STATUS_PATH = rp("data", "pipeline_status.json")

DONE, DOING, TODO, BLOCKED = "done", "doing", "todo", "blocked"
LABEL = {DONE: "✅ 完成", DOING: "🟡 进行中/部分完成", TODO: "⬜ 未开始", BLOCKED: "🔴 阻塞"}


def artifact(rel):
    """产物存在性 + mtime。支持 glob。"""
    matches = glob.glob(rp(rel))
    exists = bool(matches) and any(os.path.isfile(m) for m in matches)
    mtime = None
    if exists:
        mtime = datetime.datetime.fromtimestamp(
            max(os.path.getmtime(m) for m in matches if os.path.isfile(m))
        ).strftime("%Y-%m-%d %H:%M")
    return {"path": rel, "exists": exists, "mtime": mtime}


def parse_blockers():
    """从 requirements-brief.md §7 表格解析待拍板决策（Q1–Q3），单一事实源。"""
    path = rp("requirements", "requirements-brief.md")
    blockers = []
    if not os.path.exists(path):
        return blockers
    text = open(path, encoding="utf-8").read()
    m = re.search(r"##\s*7\..*?\n(.*?)(\n##|\Z)", text, re.S)
    if not m:
        return blockers
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.match(r"^Q\d+$", cells[0]):
            blockers.append({"id": cells[0], "decision": re.sub(r"<[^>]+>", "", cells[1]),
                             "options": cells[2], "blocks": cells[3]})
    return blockers


def gate_map(report):
    return {c["id"]: c for c in report["checks"]}


def build_status(report=None):
    report = report or validate.run_checks()
    gates = gate_map(report)
    details = report["details"]
    blockers = parse_blockers()

    def gate_state(key):
        if not key or key not in gates:
            return None
        return gates[key]["level"]

    stages = []
    for s in STAGES:
        sid = s["id"]
        arts = [artifact(p) for p in s["outputs"]]
        all_exist = all(a["exists"] for a in arts)
        g = gate_state(s["gate_key"])
        status, note = TODO, ""

        if sid == "S0":
            status = DONE if all_exist else TODO
        elif sid == "S1":
            if all_exist:
                comp = details.get("competitors", {})
                status = DOING
                note = "数据存在但闸未过：空壳率 %.0f%%（%d/%d 无评价原文），%d 款缺 link" % (
                    comp.get("shell_rate", 0) * 100, len(comp.get("no_reviews", [])),
                    comp.get("total", 0), len(comp.get("no_link", [])))
        elif sid == "S2":
            status = DONE if all_exist and g != "fail" else (DOING if any(a["exists"] for a in arts) else TODO)
            if status == DONE:
                note = "方向稿 A–E 已产出；A/B/D 已登记 forms.json（Q1 待用户拍板选定）"
        elif sid == "S3":
            status = DOING if all_exist else TODO
            if all_exist:
                note = "patent_avoidance.md 检索中（初判），每条专利 URL 与逐方向规避说明回填中"
        elif sid == "S4":
            if all_exist:
                unv = details.get("bom", {}).get("unverified_candidates", [])
                status = DOING
                note = "候选厂已建账，但 %d 个候选未达 ✅（C3 闸未过）；整机 ODM 旺旺询价未完成" % len(unv)
        elif sid == "S5":
            if all_exist:
                gap = details.get("bom", {}).get("cost_summary", {}).get("gap")
                status = DOING
                note = "BOM 已核算（≈¥73/出厂≈¥82），但 %s → Q3" % gap if gap else "BOM 已核算"
        elif sid == "S6":
            forms = details.get("forms", {}).get("forms", [])
            glb_missing = details.get("forms", {}).get("glb_missing", [])
            modeling = [f["id"] for f in forms if f.get("status") in ("建模中", "待验收")]
            if all_exist and not glb_missing:
                status = DONE
            elif all_exist or modeling:
                status = DOING
                have = [f["id"] for f in forms if f.get("id") not in glb_missing and f.get("glb")]
                note = "形态 %s GLB+五视图已产出（待人类验收）；形态 %s GLB 待产出" % (
                    "/".join(have) or "—", "/".join(glb_missing) or "—")
        elif sid == "S7":
            if all_exist:
                if blockers:
                    status = BLOCKED
                    note = "%s 待用户拍板（阻塞 S6 落地/选型）" % "/".join(b["id"] for b in blockers)
                else:
                    status = DOING
        elif sid in ("S8", "S9"):
            status = TODO
            note = "前置阶段未完成"

        stages.append({
            "id": sid,
            "name": s["name"],
            "status": status,
            "status_label": LABEL[status],
            "artifacts": arts,
            "gate": s["gate"],
            "gate_result": g,
            "note": note,
        })

    return {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "generated_by": "pipeline/status.py",
        "stages": stages,
        "blockers": blockers,
        "blockers_source": "requirements/requirements-brief.md §7",
        "validation_summary": report["summary"],
    }


def main():
    status = build_status()
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    for s in status["stages"]:
        print("%s %-8s %s %s" % (s["id"], s["name"], s["status_label"], ("— " + s["note"]) if s["note"] else ""))
    print("→ %s" % STATUS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
