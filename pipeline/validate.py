"""pipeline/validate.py — 数据完整度闸。

对 research/competitors.json、data/bom.json、data/forms.json、data/decisions.json
跑 schema 与非空率检查，输出 data/validation_report.json（含每字段缺失清单）。

实现 docs/code-architecture.md §3 三条硬规则：
  G-数据闸  : 关键字段缺失 → 工作台只渲染「待补」占位（本模块产出缺失清单，呈现层消费）
  G-验收闸  : forms.json 里标「已选定/已验收」的形态，decisions.json 必须有对应记录
  G-诚实参数: 性能宣称字段必须带测量条件（竞品 features 中的数值宣称一律标 ⚠️ 待实测）

用法: python3 pipeline/validate.py
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stages import REPO_ROOT, rp  # noqa: E402

REPORT_PATH = rp("data", "validation_report.json")

# 数值型性能宣称（dB/续航/温度/档位/功率…）——竞品话术无测量条件，引用时必须自带实测
CLAIM_RE = re.compile(r"\d+\s*(dB|分贝|小时|h\b|H\b|°C|℃|度|档|W\b|mAh|CFM|%)")


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check(id_, dataset, rule, ok, missing=None, level=None):
    """level: pass / fail / warn（不传则按 ok 推 pass/fail）。"""
    return {
        "id": id_,
        "dataset": dataset,
        "rule": rule,
        "level": level or ("pass" if ok else "fail"),
        "ok": bool(ok),
        "missing": missing or [],
    }


def validate_competitors(checks, details):
    data = load_json(rp("research", "competitors.json"))
    items = (data or {}).get("items", [])
    checks.append(check("C-文件存在", "competitors", "research/competitors.json 存在且可解析",
                        data is not None, ["research/competitors.json"] if data is None else []))
    if data is None:
        return

    no_link, no_reviews, shells, claims = [], [], [], []
    for it in items:
        name = it.get("name", "?")
        if not (it.get("link") or "").strip():
            no_link.append(name)
        n_rev = len(it.get("reviews_good", [])) + len(it.get("reviews_bad", []))
        if n_rev == 0:
            no_reviews.append(name)
            shells.append(name)
        for feat in it.get("features", []):
            if CLAIM_RE.search(feat):
                claims.append({"item": name, "claim": feat})

    checks.append(check("C-link 非空", "competitors", "每款 link 非空",
                        not no_link, no_link))
    checks.append(check("C-评价原文", "competitors", "每款 ≥1 条评价原文(好评或差评)",
                        not no_reviews, no_reviews))
    shell_rate = (len(shells) / len(items)) if items else 1.0
    checks.append(check("S1-竞品数据完整度", "competitors",
                        "空壳率 <20%（空壳=无任何评价原文）",
                        items and shell_rate < 0.20,
                        ["空壳率 %.1f%%（%d/%d）" % (shell_rate * 100, len(shells), len(items))] + shells))
    # G-诚实参数：竞品数值宣称均无测量条件 → warn（引用到详情页/设计决策前必须自行实测）
    checks.append(check("G-诚实参数(竞品宣称)", "competitors",
                        "性能宣称字段必须带测量条件；竞品宣称视为无测量条件，仅作参考",
                        True, ["%s: %s" % (c["item"], c["claim"]) for c in claims],
                        level="warn" if claims else "pass"))
    details["competitors"] = {
        "total": len(items),
        "complete": len(items) - len(shells),
        "no_link": no_link,
        "no_reviews": no_reviews,
        "shell_rate": round(shell_rate, 4),
        "unconditioned_claims": claims,
    }


def validate_bom(checks, details):
    data = load_json(rp("data", "bom.json"))
    checks.append(check("B-文件存在", "bom", "data/bom.json 存在且可解析",
                        data is not None, ["data/bom.json"] if data is None else []))
    if data is None:
        return

    modules = data.get("modules", [])
    missing_fields, no_candidate, unverified, price_missing = [], [], [], []
    for m in modules:
        mid = m.get("id", "?")
        for k in ("id", "name", "candidates", "cost_budget"):
            if k not in m or m[k] in (None, "", []):
                missing_fields.append("%s.%s" % (mid, k))
        cands = m.get("candidates", [])
        if not cands:
            no_candidate.append(mid)
        for c in cands:
            for k in ("name", "verification", "moq"):
                if not c.get(k):
                    missing_fields.append("%s.候选厂.%s" % (mid, k))
            v = c.get("verification", "")
            if v != "✅":
                unverified.append("%s → %s（%s）" % (mid, c.get("name", "?"), v or "空"))
            if c.get("unit_price") is None:
                price_missing.append("%s → %s" % (mid, c.get("name", "?")))

    expected = ["M%d" % i for i in range(1, 9)]
    got = [m.get("id") for m in modules]
    missing_mods = [x for x in expected if x not in got]
    checks.append(check("B-M1–M8 覆盖", "bom", "M1–M8 模块齐全", not missing_mods, missing_mods))
    checks.append(check("B-关键字段", "bom", "模块/候选厂关键字段非空（单价可为空=待询价）",
                        not missing_fields, missing_fields))
    checks.append(check("B-候选厂覆盖", "bom", "BOM 模块 100% 有候选厂", not no_candidate, no_candidate))
    # C3 / S4 闸：候选厂全部 ✅ 才算过
    checks.append(check("S4-供应商核验", "bom", "候选厂全部 ✅ 核验（C3）",
                        not unverified, unverified))
    checks.append(check("B-单价完整", "bom", "候选厂单价已填（空=待旺旺询价）",
                        True, price_missing, level="warn" if price_missing else "pass"))
    cost = data.get("cost_summary", {})
    gap = cost.get("gap")
    checks.append(check("S5-成本核算", "bom",
                        "出厂成本在目标 ±15% 内；超标有处置方案（Q3 类决策）",
                        False if gap else True,
                        ["出厂估算 %s vs 目标 %s，%s" % (cost.get("factory_estimate"), cost.get("factory_target"), gap)] if gap else [],
                        level="warn" if gap else "pass"))
    details["bom"] = {
        "modules": got,
        "unverified_candidates": unverified,
        "price_missing": price_missing,
        "cost_summary": cost,
    }


def validate_forms(checks, details):
    data = load_json(rp("data", "forms.json"))
    checks.append(check("F-文件存在", "forms", "data/forms.json 存在且可解析",
                        data is not None, ["data/forms.json"] if data is None else []))
    if data is None:
        return

    forms = data.get("forms", [])
    decisions = (load_json(rp("data", "decisions.json")) or {}).get("decisions", [])
    missing_fields, no_glb = [], []
    for f in forms:
        fid = f.get("id", "?")
        for k in ("id", "name", "direction", "status", "scores"):
            if k not in f or f[k] in (None, "", []):
                missing_fields.append("%s.%s" % (fid, k))
        glb = f.get("glb")
        if not glb or not glob.glob(rp(glb)):
            no_glb.append(fid)
        for r in f.get("renders", []):
            if not os.path.exists(rp(r)):
                missing_fields.append("%s.renders: %s 不存在" % (fid, r))

    checks.append(check("F-关键字段", "forms", "形态关键字段非空、渲染图路径存在",
                        not missing_fields, missing_fields))
    checks.append(check("S2-形态方向数量", "forms", "≥3 个形态语言互不重合的方向",
                        len(forms) >= 3, ["当前 %d 个" % len(forms)] if len(forms) < 3 else []))
    checks.append(check("F-GLB 产出", "forms", "每形态 GLB 已产出（cad/*.glb）",
                        True, ["形态 %s GLB 待产出" % x for x in no_glb],
                        level="warn" if no_glb else "pass"))

    # G-验收闸：标「已选定/已验收」的形态必须在 decisions.json 有对应记录
    accepted_missing = []
    for f in forms:
        if f.get("status") in ("已选定", "已验收"):
            fid = f.get("id", "?")
            hit = any(fid in (d.get("object", "") + d.get("action", "")) or
                      f.get("name", "") in (d.get("object", "") + d.get("action", ""))
                      for d in decisions)
            if not hit:
                accepted_missing.append("形态 %s（%s）标「%s」但 decisions.json 无对应记录" % (fid, f.get("name"), f.get("status")))
    checks.append(check("G-验收闸", "forms+decisions",
                        "任何形态标「已验收/已选定」，decisions.json 必须存在对应记录",
                        not accepted_missing, accepted_missing))
    details["forms"] = {
        "forms": [{"id": f.get("id"), "name": f.get("name"), "status": f.get("status"),
                   "glb": f.get("glb"), "renders": len(f.get("renders", []))} for f in forms],
        "glb_missing": no_glb,
    }


def validate_decisions(checks, details):
    data = load_json(rp("data", "decisions.json"))
    checks.append(check("D-文件存在", "decisions", "data/decisions.json 存在且可解析",
                        data is not None, ["data/decisions.json"] if data is None else []))
    if data is None:
        return

    missing = []
    for d in data.get("decisions", []):
        did = d.get("id", "?")
        for k in ("id", "date", "object", "verdict", "quote", "action"):
            if not d.get(k):
                missing.append("%s.%s" % (did, k))
    checks.append(check("D-关键字段", "decisions", "决策记录 id/日期/对象/verdict/原话/后续动作 非空",
                        not missing, missing))
    details["decisions"] = {"count": len(data.get("decisions", [])),
                            "ids": [d.get("id") for d in data.get("decisions", [])]}


def run_checks():
    checks, details = [], {}
    validate_competitors(checks, details)
    validate_bom(checks, details)
    validate_forms(checks, details)
    validate_decisions(checks, details)

    gates = {c["id"]: c for c in checks if c["id"].startswith(("G-", "S"))}
    summary = {
        "pass": sum(1 for c in checks if c["level"] == "pass"),
        "warn": sum(1 for c in checks if c["level"] == "warn"),
        "fail": sum(1 for c in checks if c["level"] == "fail"),
    }
    return {
        "generated_by": "pipeline/validate.py",
        "summary": summary,
        "hard_rules": {
            "G-数据闸": gates.get("S1-竞品数据完整度"),
            "G-验收闸": gates.get("G-验收闸"),
            "G-诚实参数": gates.get("G-诚实参数(竞品宣称)"),
        },
        "checks": checks,
        "details": details,
    }


def main():
    report = run_checks()
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    s = report["summary"]
    print("validate: %d pass / %d warn / %d fail → %s" % (s["pass"], s["warn"], s["fail"], REPORT_PATH))
    for c in report["checks"]:
        if c["level"] != "pass":
            print("  [%s] %s (%s): %d 项缺失/待办" % (c["level"].upper(), c["id"], c["dataset"], len(c["missing"])))
    return 0 if s["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
