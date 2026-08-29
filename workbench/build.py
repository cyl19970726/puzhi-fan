"""workbench/build.py — 工作台壳构建器（Phase 3 版）。

只做四件事（phase0_contract §9）：
  1. G-数据闸：跑 pipeline/validate.py + pipeline/status.py（闸逻辑保留，写 data/*.json）
  2. data 快照拷 dist/data/（含构建时活体解析产物：patent_ratings / requirements / meta）
  3. 拷贝 src/ 与 vendor/ 到 dist/
  4. 写 dist/index.html 壳（import map 指向 vendor；不生成任何业务 HTML）

旧产物 dist/workbench.html 为 legacy，保留不动。新入口 dist/index.html。
用法: python3 workbench/build.py（或 python3 pipeline/run.py build）
"""
import datetime
import json
import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(REPO_ROOT, "pipeline"))

import status as pipe_status  # noqa: E402
import validate  # noqa: E402

DIST = os.path.join(BASE, "dist")
DATA_DIST = os.path.join(DIST, "data")

# data 快照清单：dist 文件名 ← repo 相对路径
SNAPSHOTS = {
    "pipeline_status.json": "data/pipeline_status.json",
    "validation_report.json": "data/validation_report.json",
    "decisions.json": "data/decisions.json",
    "forms.json": "data/forms.json",
    "bom.json": "data/bom.json",
    "competitors.json": "research/competitors.json",
    "labels.json": "cad/infographic/labels.json",
    "assembly_a_parts.json": "cad/assembly_a_parts.json",
    "assembly_b_parts.json": "cad/assembly_b_parts.json",
    "assembly_d_parts.json": "cad/assembly_d_parts.json",
}


def load_json(rel, fallback=None):
    p = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(p):
        return fallback
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def file_exists(rel):
    return bool(rel) and os.path.exists(os.path.join(REPO_ROOT, rel))


# ---------------------------------------------------------------- 活体解析（防数据腐化）
def md_table_rows(md_path, section_marker):
    """从 md 文件中提取指定章节后的第一张表格（research/patent_avoidance.md §4 评级表）。"""
    try:
        with open(os.path.join(REPO_ROOT, md_path), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except Exception:
        return []
    in_sec, rows = False, []
    for ln in lines:
        if section_marker in ln:
            in_sec = True
            continue
        if in_sec:
            if ln.startswith("## ") and section_marker not in ln:
                break
            if ln.strip().startswith("|") and "---" not in ln:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                rows.append(cells)
    return rows


def parse_md_tables(path):
    """解析 markdown 全部表格：[(nearest_heading, headers, rows)]。通用解析，不做列语义假设。"""
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return []
    tables, heading, cur = [], "", None
    for line in open(full, encoding="utf-8"):
        s = line.strip()
        if s.startswith("#"):
            heading = s.lstrip("#").strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # 分隔行
            if cur is None:
                cur = (heading, cells, [])
                tables.append(cur)
            else:
                cur[2].append(cells)
        else:
            cur = None
    return tables


def build_requirements():
    """需求追溯表（§2 硬约束 / §3 用户需求 / §5 商业约束 / §7 待用户拍板）。"""
    wanted = ("2. 硬约束", "3. 用户需求", "5. 商业约束", "7. 待用户拍板")
    tables = []
    for heading, headers, rows in parse_md_tables("requirements/requirements-brief.md"):
        if not any(heading.startswith(w) for w in wanted):
            continue
        strip = lambda c: re.sub(r"\*\*", "", c)  # noqa: E731
        tables.append({"heading": heading, "headers": [strip(c) for c in headers],
                       "rows": [[strip(c) for c in r] for r in rows]})
    return {"source": "requirements/requirements-brief.md", "tables": tables}


def build_meta():
    """meta.json：快照 mtime（① 数据新鲜度行）+ repo 资产存在性地图（替代旧 build 的 file_exists）。"""
    mtimes = {}
    for key, rel in [("pipeline_status", "data/pipeline_status.json"), ("forms", "data/forms.json"),
                     ("bom", "data/bom.json"), ("decisions", "data/decisions.json"),
                     ("competitors", "research/competitors.json")]:
        p = os.path.join(REPO_ROOT, rel)
        if os.path.exists(p):
            mtimes[key] = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")

    assets = set()
    forms = load_json("data/forms.json", {}) or {}
    for f in forms.get("forms", []):
        assets.update(f.get("concept_images") or [])
        assets.update(f.get("renders") or [])
        for k in ("glb", "glb_alt", "ai_shell"):
            if f.get(k):
                assets.add(f[k])
    comp = load_json("research/competitors.json", {}) or {}
    for it in comp.get("items", []):
        if it.get("image"):
            assets.add(it["image"])
    assets.update([
        "cad/infographic/LiteCool_S1_解构图鉴.png",
        "cad/infographic/LiteCool_S1_解构图鉴_B.png",
        "cad/infographic/LiteCool_S1_解构图鉴_D.png",
        "research/patent_avoidance.md",
        "research/patents_desktop_fans.md",
        "design/form-directions.md",
        "requirements/requirements-brief.md",
        "rfq/NDA_template.md",
    ])
    return {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mtimes": mtimes,
        "assets": {rel: file_exists(rel) for rel in sorted(assets)},
    }


INDEX_HTML = """<!doctype>
<html lang="zh-CN" data-data-base="./data/">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1440">
<title>LiteCool S1 Workbench</title>
<link rel="stylesheet" href="./src/styles/tokens.css">
<link rel="stylesheet" href="./src/styles/base.css">
<link rel="stylesheet" href="./src/styles/components.css">
<link rel="stylesheet" href="./src/styles/views.css">
<script>
  // 验收钩子：ego-browser 读 window.__errs 判 console 无错（spec §6-6）
  window.__errs = [];
  addEventListener('error', e => window.__errs.push(String(e.message)));
  addEventListener('unhandledrejection', e => window.__errs.push('rejection: ' + String(e.reason)));
</script>
<script type="importmap">
{ "imports": {
  "three": "./vendor/three/build/three.module.js",
  "three/addons/": "./vendor/three/examples/jsm/"
} }
</script>
</head>
<body>
<div id="app"></div>
<script type="module">
  import { startApp } from './src/main.js';
  startApp(document.getElementById('app'));
</script>
</body>
</html>
"""


def main():
    # 1. G-数据闸：构建前先跑闸（写 data/validation_report.json + data/pipeline_status.json）
    report = validate.run_checks()
    with open(validate.REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    st = pipe_status.build_status(report)
    with open(pipe_status.STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

    # 2. data 快照 → dist/data/
    os.makedirs(DATA_DIST, exist_ok=True)
    copied = []
    for name, rel in SNAPSHOTS.items():
        src = os.path.join(REPO_ROOT, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(DATA_DIST, name))
            copied.append(name)
    generated = {
        "patent_ratings.json": {
            "source": "research/patent_avoidance.md §4（构建时活体解析）",
            "ratings": md_table_rows("research/patent_avoidance.md", "## §4"),
        },
        "requirements.json": build_requirements(),
        "meta.json": build_meta(),
    }
    for name, obj in generated.items():
        with open(os.path.join(DATA_DIST, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # 3. 拷贝 src/ 与 vendor/ → dist/
    for d in ("src", "vendor"):
        shutil.copytree(os.path.join(BASE, d), os.path.join(DIST, d), dirs_exist_ok=True)

    # 4. 壳（不生成任何业务 HTML；旧 dist/workbench.html 保留不动）
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)

    missing_assets = [k for k, v in generated["meta.json"]["assets"].items() if not v]
    print("BUILT: %s | snapshots: %d+%d | assets missing: %d | validate: pass %d / warn %d / fail %d"
          % (os.path.join(DIST, "index.html"), len(copied), len(generated),
             len(missing_assets), report["summary"]["pass"],
             report["summary"]["warn"], report["summary"]["fail"]))
    if missing_assets:
        print("  待补资产: " + ", ".join(missing_assets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
