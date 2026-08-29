"""workbench/build.py — 工作台生成器（取代 dashboard/，旧目录冻结）。

读 data/ + research/ → 渲染 dist/workbench.html（单文件，Three.js CDN import map，
图片一律相对路径引用，不内嵌 base64）。

G-数据闸：构建前先跑 pipeline/validate.py；任一数据对象关键字段缺失 →
对应卡片渲染为灰色「待补」占位 + 流水线总览亮黄灯，空数据不渲染成正式卡片。

用法: python3 workbench/build.py（或 python3 pipeline/run.py build）
"""
import datetime
import html
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE)
sys.path.insert(0, os.path.join(REPO_ROOT, "pipeline"))

import status as pipe_status  # noqa: E402
import validate  # noqa: E402
from validate import CLAIM_RE  # noqa: E402

DIST = os.path.join(BASE, "dist")
REL = "../../"  # workbench/dist → repo root


def esc(s):
    return html.escape(str(s), quote=True)


def load_json(rel, fallback=None):
    p = os.path.join(REPO_ROOT, rel)
    if not os.path.exists(p):
        return fallback
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def file_exists(rel):
    return bool(rel) and os.path.exists(os.path.join(REPO_ROOT, rel))


def link(rel, text=None):
    """repo 相对路径 → 工作台内链接（文件不存在则灰字不链）。"""
    if file_exists(rel):
        return '<a href="%s%s" target="_blank">%s</a>' % (REL, esc(rel), esc(text or rel))
    return '<span style="color:var(--todo)">%s（不存在）</span>' % esc(rel)


def badge(level, text):
    return '<span class="badge b-%s">%s</span>' % (level, esc(text))


# ---------------------------------------------------------------- ① 流水线总览
def render_overview(st, report):
    s = report["summary"]
    parts = []
    if s["fail"]:
        parts.append('<div class="banner warn">G-数据闸：validate %d pass / %d warn / <b>%d fail</b> —— 闸未过的数据对象在本工作台一律渲染为「待补」占位，不渲染成正式卡片。明细见 data/validation_report.json。</div>'
                     % (s["pass"], s["warn"], s["fail"]))
    else:
        parts.append('<div class="banner ok">G-数据闸：validate 全部通过（%d pass / %d warn）。</div>' % (s["pass"], s["warn"]))

    parts.append('<div class="stage-grid">')
    for stg in st["stages"]:
        g = stg["gate_result"]
        g_badge = {"pass": badge("ok", "闸 ✓"), "warn": badge("warn", "闸 ⚠"), "fail": badge("risk", "闸 ✗")}.get(g, badge("todo", "闸未接"))
        arts = "".join(
            '<div class="art">%s %s</div>' % (
                ("✅" if a["exists"] else "⬜"),
                (link(a["path"]) + (' <span style="color:var(--todo)">%s</span>' % a["mtime"] if a["mtime"] else "")) if a["exists"] else esc(a["path"]))
            for a in stg["artifacts"])
        note = '<div class="note">%s</div>' % esc(stg["note"]) if stg["note"] else ""
        parts.append(
            '<div class="card stage %s"><h3>%s %s %s</h3><div class="gate">闸：%s %s</div>%s%s</div>'
            % (stg["status"], esc(stg["id"]), esc(stg["name"]), g_badge, esc(stg["gate"]),
               {"done": badge("ok", "✅ 完成"), "doing": badge("warn", "🟡 部分完成"),
                "blocked": badge("risk", "🔴 阻塞"), "todo": badge("todo", "⬜ 未开始")}[stg["status"]],
               arts, note))
    parts.append('</div>')

    if st["blockers"]:
        parts.append('<h3 style="margin:14px 0 6px;font-size:13.5px">当前阻塞项（待用户拍板，源：%s）</h3>' % esc(st["blockers_source"]))
        parts.append('<div class="blocker-row">')
        for b in st["blockers"]:
            parts.append('<div class="blocker"><h4>%s %s</h4><div><b>选项：</b>%s</div><div><b>阻塞：</b>%s</div></div>'
                         % (esc(b["id"]), esc(b["decision"]), esc(b["options"]), esc(b["blocks"])))
        parts.append('</div>')
    return "".join(parts)


# ---------------------------------------------------------------- ② 竞品分析
def render_competitors(comp, report):
    items = comp.get("items", [])
    det = report["details"].get("competitors", {})
    total = det.get("total", len(items))
    shell_rate = det.get("shell_rate", 0)
    claims = {(c["item"], c["claim"]) for c in det.get("unconditioned_claims", [])}

    parts = ['<div class="banner warn">S1 数据完整度：<b>%d/%d</b> 款有评价原文，空壳率 <b>%.0f%%</b>（闸要求 &lt;20%%）——闸未过。空壳款按 G-数据闸渲染为灰色「待补」占位，不是正式卡片。数据更新：%s</div>'
             % (det.get("complete", 0), total, shell_rate * 100, esc(comp.get("updated", "—")))]
    parts.append('<div class="comp-grid">')
    for it in items:
        name = it.get("name", "?")
        n_rev = len(it.get("reviews_good", [])) + len(it.get("reviews_bad", []))
        complete = bool((it.get("link") or "").strip()) and n_rev > 0
        if not complete:
            missing = []
            if not (it.get("link") or "").strip():
                missing.append("商品链接")
            if n_rev == 0:
                missing.append("评价原文（好评/差评）")
            if not it.get("image"):
                missing.append("竞品主图")
            parts.append(
                '<div class="card comp placeholder"><h3>%s</h3>'
                '<div>%s · %s · <b>¥%s</b> · 销量 %s</div>'
                '<div class="missing">⬜ <b>待补</b>（S1 补抓中）：%s<br>空数据按纪律不渲染正式卡片。</div></div>'
                % (esc(name), esc(it.get("brand", "—")), esc(it.get("shop", "—")),
                   esc(it.get("price", "—")), esc(it.get("sales", "—")), esc("、".join(missing))))
            continue

        img = ""
        if file_exists(it.get("image", "")):
            img = '<img src="%s%s" alt="%s" loading="lazy">' % (REL, esc(it["image"]), esc(name))
        chips = "".join(
            '<span class="chip%s"%s>%s%s</span>' % (
                " claim" if (name, f) in claims or CLAIM_RE.search(f) else "",
                ' title="竞品宣称，未附测量条件（G-诚实参数）：引用到设计决策/详情页前必须自行实测"' if CLAIM_RE.search(f) else "",
                "⚠️ " if CLAIM_RE.search(f) else "", esc(f))
            for f in it.get("features", []))
        good = "".join("<li>%s</li>" % esc(r) for r in it.get("reviews_good", []))
        bad = "".join("<li>%s</li>" % esc(r) for r in it.get("reviews_bad", []))
        revs = '<div class="revs">'
        if good:
            revs += '<details open><summary class="good">好评原文 %d 条</summary><ul class="good">%s</ul></details>' % (len(it["reviews_good"]), good)
        if bad:
            revs += '<details open><summary class="bad">差评/质疑原文 %d 条</summary><ul class="bad">%s</ul></details>' % (len(it["reviews_bad"]), bad)
        revs += '</div>'
        parts.append(
            '<div class="card comp"><h3>%s %s</h3>%s'
            '<div><span class="price">¥%s</span> · 销量 %s · %s · %s</div>'
            '<div>%s %s</div>'
            '<div class="chips">%s</div>'
            '<div class="fn">%s</div>%s'
            '<div><a href="%s" target="_blank">商品链接 →</a></div></div>'
            % (esc(name), badge("ok", "数据完整"), img, esc(it.get("price", "—")), esc(it.get("sales", "—")),
               esc(it.get("shop", "—")), esc(it.get("category", "—")),
               badge("todo", "形态原型: " + it["form"]) if it.get("form") else "",
               badge("warn", it["category"]) if it.get("category") == "制冷" else "",
               chips, esc(it.get("functional", "")), revs, esc(it.get("link", "#"))))
    parts.append('</div>')
    return "".join(parts)


# ---------------------------------------------------------------- ③ 形态对比
def stars(n, risk=False):
    cls = "on" if n >= 4 else ("mid" if n >= 3 else "off2")
    return '<span class="stars"><span class="%s">%s</span><span class="off">%s</span></span>' % (
        cls, "★" * n, "☆" * (5 - n))


VIEW_LABELS = {"three_quarter": "¾", "front": "正", "side": "侧", "back": "背", "top": "顶"}


def _view_label(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    return VIEW_LABELS.get(stem, stem)


def _form_media(f):
    """形态画廊媒体区：概念图（主）/ 白模五视图 / 3D GLB 三组，组内子项可切换。"""
    fid = f.get("id", "?")
    concepts = [c for c in f.get("concept_images", []) if file_exists(c)]
    renders = [r for r in f.get("renders", []) if file_exists(r)]
    has_glb = file_exists(f.get("glb") or "")

    items, group_btns, sub_pills = [], [], []
    groups = []  # (key, label, sub-labels)
    if concepts:
        groups.append(("concept", "概念图", [str(i + 1) for i in range(len(concepts))]))
        items += ['<img class="m-item" data-g="concept" src="%s%s" alt="形态%s 概念图 %d" loading="lazy" hidden>'
                  % (REL, esc(c), esc(fid), i + 1) for i, c in enumerate(concepts)]
    if renders:
        groups.append(("render", "白模视图", [_view_label(r) for r in renders]))
        items += ['<img class="m-item" data-g="render" src="%s%s" alt="形态%s 白模 %s" loading="lazy" hidden>'
                  % (REL, esc(r), esc(fid), esc(_view_label(r))) for r in renders]
    if has_glb:
        groups.append(("glb", "3D", []))
        items.append('<div class="glb-view m-item" data-g="glb" data-glb="%s%s" hidden></div>' % (REL, esc(f["glb"])))
    ai_shell = f.get("ai_shell")
    if ai_shell and file_exists(ai_shell):
        groups.append(("shell", "AI 皮肤", []))
        items.append('<div class="glb-view m-item" data-g="shell" data-glb="%s%s" hidden title="图生3D 外观网格（Meshy），仅展示；尺寸/结构以工程装配体为准"></div>' % (REL, esc(ai_shell)))

    if not groups:
        ph = '<div class="ph">概念图 / 渲染待产出<br>（S6：形态 %s %s，cad/build_form_%s.py）</div>' % (
            esc(fid), esc(f.get("status", "")), esc(fid.lower()))
        return '<div class="form-media">%s</div>' % ph

    first = groups[0][0]
    for key, label, sublabels in groups:
        group_btns.append('<button data-g="%s"%s>%s</button>'
                          % (key, ' class="active"' if key == first else "", label))
        if len(sublabels) > 1:
            pills = "".join('<button data-i="%d"%s>%s</button>'
                            % (i, ' class="active"' if key == first and i == 0 else "", esc(s))
                            for i, s in enumerate(sublabels))
            sub_pills.append('<div class="media-subs" data-g="%s"%s>%s</div>'
                             % (key, "" if key == first else " hidden", pills))
    glb_btn = '' if has_glb else '<button data-g="glb" disabled title="GLB 待 S6 产出">3D 待产出</button>'
    # 首组第一项默认可见：去掉其 hidden
    for i, it in enumerate(items):
        if 'data-g="%s"' % first in it:
            items[i] = it.replace(" hidden>", ">", 1)
            break
    return ('<div class="form-media">%s'
            '<div class="media-ctl"><div class="media-subs-wrap">%s</div>'
            '<div class="media-groups">%s%s</div></div></div>'
            % ("".join(items), "".join(sub_pills), "".join(group_btns), glb_btn))


def _form_card(f, explore=False):
    fid = f.get("id", "?")
    status_badge = {"建模中": "warn", "设计中": "warn", "待验收": "warn", "已选定": "ok", "已否决": "risk", "探索": "todo"}
    dims = ["制冷可读性", "差异化", "专利风险", "工程代价", "价位匹配", "架构影响"]

    pr = f.get("patent_risk", {})
    pr_level = pr.get("level", "")
    pr_tag = "初判⚠️" if pr.get("provisional") else "预检索"
    pr_badge = badge("risk" if "高" in pr_level else ("warn" if "中" in pr_level else ("todo" if "未评估" in pr_level else "ok")),
                     "专利 %s·%s" % (pr_tag, pr_level))
    ec = f.get("engineering_cost", {})
    ec_badge = '<span class="badge b-todo" title="%s">工程代价 %s</span>' % (
        esc(ec.get("note", "")), esc(ec.get("level", "—")))

    scores = "".join(
        '<div class="score" title="%s"><span>%s</span>%s</div>'
        % (esc("%s：%s" % (d, f["scores"][d]["note"])), esc(d), stars(f["scores"][d]["stars"]))
        for d in dims if d in f.get("scores", {}))

    notes = f.get("notes", "")
    notes_html = ""
    if notes:
        notes_html = ('<details class="form-notes"><summary>备注 / 验收 / 专利规避落实</summary><div>%s</div></details>'
                      % esc(notes))

    return (
        '<article class="form-card%s">'
        '%s'
        '<div class="form-body">'
        '<div class="form-head"><span class="form-id">形态 %s</span><span class="form-name">%s</span>%s</div>'
        '<p class="form-claim">%s</p>'
        '<div class="form-lang" title="%s">%s</div>'
        '<div class="score-grid">%s</div>'
        '<div class="form-tags">%s%s%s</div>'
        '%s'
        '</div></article>'
        % (" explore" if explore else "", _form_media(f),
           esc(fid), esc(f.get("name", "")),
           badge(status_badge.get(f.get("status"), "todo"), f.get("status", "—")),
           esc(f.get("claim", "")),
           esc(f.get("language", "")), esc(f.get("language", "")),
           scores, pr_badge, ec_badge,
           badge("warn", "探索向") if explore else "",
           notes_html))


def render_forms(forms_data, st):
    forms = forms_data.get("forms", [])
    main = [f for f in forms if f.get("status") != "探索"]
    explore = [f for f in forms if f.get("status") == "探索"]

    parts = ['<div class="banner ok">Q1 已定：<b>形态 A 桌面挂机</b>（决策 D-2026-08-29-01，B/D 保留为备份基线）——主栏 %s，探索向 %s。每卡媒体分层：概念图 / AI 皮肤（图生3D 外观网格，仅展示）/ 白模视图 / 3D（工程装配体=尺寸与结构唯一真源）。专利风险为预检索确认；开模前仍须正式 FTO。</div>'
             % (" / ".join(f.get("id", "?") for f in main), " / ".join(f.get("id", "?") for f in explore) or "—")]
    parts.append('<div class="forms-main">')
    parts += [_form_card(f) for f in main]
    parts.append('</div>')
    if explore:
        parts.append('<div class="forms-sub">探索向 —— 未进 FTO 预检索范围，工程未评估，仅作方向感参考</div>')
        parts.append('<div class="forms-explore">')
        parts += [_form_card(f, explore=True) for f in explore]
        parts.append('</div>')

    q1 = next((b for b in st["blockers"] if b["id"] == "Q1"), None)
    q1_text = (forms_data.get("pending_decision") or "")
    if q1:
        q1_text += "（%s：%s｜阻塞：%s）" % (q1["id"], q1["decision"], q1["blocks"])
    parts.append('<div class="banner risk q1-banner">⏳ <b>待用户拍板 Q1</b>：%s</div>' % esc(q1_text))
    return "".join(parts)


# ---------------------------------------------------------------- ④ 3D 拆分 + 供应链
ASM_FORMS = [
    # (id, 名称, parts json, 解构图鉴)
    ("a", "A 桌面挂机", "cad/assembly_a_parts.json", "cad/infographic/LiteCool_S1_解构图鉴.png"),
    ("b", "B 复古收音机", "cad/assembly_b_parts.json", "cad/infographic/LiteCool_S1_解构图鉴_B.png"),
    ("d", "D 塔·认真版", "cad/assembly_d_parts.json", "cad/infographic/LiteCool_S1_解构图鉴_D.png"),
]


def _json_blob(obj):
    """嵌进 <script type="application/json"> 的 JSON（防 </script> 闭合）。"""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def render_assembly(bom, asm, form_id, form_name, key_labels, infographic, hidden):
    """单形态装配体拆分视图：GLB 查看器 + 爆炸滑块 + 零件列表 + BOM 卡 + 图鉴缩略图。"""
    plist = asm.get("parts", [])
    by_mod = {}
    for p in plist:
        by_mod.setdefault(p.get("module", "?"), []).append(p)
    groups = []
    for m in bom.get("modules", []):
        mid = m.get("id", "?")
        if mid not in by_mod:
            continue
        btns = "".join(
            '<button class="asm-part" data-part="%s">%s<span class="pn">%s</span></button>'
            % (esc(p["name"]), esc(p.get("label", p["name"])), esc(p["name"]))
            for p in by_mod[mid])
        groups.append('<div class="asm-mod">%s %s（%d）</div>%s'
                      % (esc(mid), esc(m.get("name", "")), len(by_mod[mid]), btns))
    n = len(plist)
    blob = dict(asm)
    blob["key_labels"] = key_labels     # 查看器浮动标注清单（labels.json 单一事实源）
    if file_exists(infographic):
        info = ('<div class="asm-info"><a href="%s%s" target="_blank" title="点击新窗口打开原图">'
                '<img src="%s%s" alt="形态%s 产品解构图鉴" loading="lazy">'
                '<span>产品解构图鉴 · 形态%s（点击放大）</span></a></div>'
                % (REL, esc(infographic), REL, esc(infographic), esc(form_name), esc(form_name)))
    else:
        info = ('<div class="asm-info"><span style="color:var(--todo)">产品解构图鉴 · 形态%s 待产出（%s）</span></div>'
                % (esc(form_name), esc(infographic)))
    return "".join([
        '<div class="asm-form" data-form="%s"%s>' % (esc(form_id), " hidden" if hidden else ""),
        '<div class="asm">',
        '<script type="application/json" class="asm-data" data-kind="parts">%s</script>' % _json_blob(blob),
        '<script type="application/json" class="asm-data" data-kind="bom">%s</script>'
        % _json_blob({"modules": bom.get("modules", [])}),
        '<div class="asm-stage card">',
        '<div class="asm-view" data-glb="%s%s"></div>' % (REL, esc(asm.get("glb", ""))),
        '<div class="asm-bar"><span class="asm-bar-label">装配</span>'
        '<input type="range" class="asm-explode" min="0" max="100" value="0" step="1">'
        '<span class="asm-bar-label">爆炸</span>'
        '<button type="button" class="asm-mode" data-mode="xray" title="外壳类零件半透明，看内部结构（对标透视图）">透视</button>'
        '<button type="button" class="asm-mode active" data-mode="labels" title="爆炸滑块 >30%% 时显示关键零件中文标注">标注</button>'
        '<span class="asm-hint">拖拽旋转 · 滚轮缩放 · 点零件高亮</span></div>',
        '</div>',
        '<div class="asm-side">',
        '<div class="asm-parts card"><h3>零件清单（%d 件，按 M1–M8 分组）</h3>%s</div>' % (n, "".join(groups)),
        '<div class="asm-bom card"><h3>BOM 卡</h3><div class="fn">点击零件查看。</div></div>',
        '</div>',
        '</div>',
        info,
        '</div>',
    ])


def render_supply(bom):
    parts = []
    with open(os.path.join(REPO_ROOT, "cad/infographic/labels.json"), encoding="utf-8") as fp:
        key_labels = {k: [row[0] for row in v] for k, v in json.load(fp).items()}
    forms = []
    for fid, fname, pj, info in ASM_FORMS:
        asm = load_json(pj, None)
        if asm and file_exists(asm.get("glb", "")):
            forms.append((fid, fname, asm, info))
    if forms:
        desc = " / ".join("%s（%d 件）" % (fname, len(asm.get("parts", []))) for _, fname, asm, _ in forms)
        parts.append(
            '<div class="banner ok">三形态装配体可切换：%s —— DFM 级，Blender 5.1 无头 build_core_eng*.py 产出，爆炸向量存于 GLB node extras。'
            '点下方形态按钮切换（GLB 懒加载，切到才载入；切换自动重置爆炸滑块与选中态）；'
            '拖<b>爆炸滑块</b>拆解，点右侧零件（或直接点 3D 模型）高亮并弹 BOM 卡（M1–M8 模块映射，三形态通用）。'
            '每个视图下方挂该形态的「产品解构图鉴」缩略图。GLB：%s</div>'
            % (esc(desc), " ".join(link(asm.get("glb")) for _, _, asm, _ in forms)))
        btns = "".join(
            '<button type="button" class="asm-form-btn%s" data-form="%s">%s <span class="cnt">%d 件</span></button>'
            % ("" if i else " active", esc(fid), esc(fname), len(asm.get("parts", [])))
            for i, (fid, fname, asm, _) in enumerate(forms))
        parts.append('<div class="asm-multi"><div class="asm-form-bar">%s</div>' % btns)
        for i, (fid, fname, asm, info) in enumerate(forms):
            parts.append(render_assembly(bom, asm, fid, fname, key_labels.get(fid, []), info, hidden=i > 0))
        parts.append('</div>')
    else:
        parts.append('<div class="shelf"><b>3D 拆分热点标注 —— 空架子</b><br>'
                     'cad/assembly_{a,b,d}*.glb / *_parts.json 缺失 —— 先跑 '
                     '<code>blender --background --python cad/build_core_eng.py</code>。</div>')
    cost = bom.get("cost_summary", {})
    parts.append('<div class="banner risk">R8：BOM 合计 ≈¥%s，出厂估算 ≈¥%s vs 目标 %s —— %s</div>'
                 % (esc(cost.get("bom_total", "—")), esc(cost.get("factory_estimate", "—")),
                    esc(cost.get("factory_target", "—")), esc(cost.get("gap", "—"))))
    rows = []
    for m in bom.get("modules", []):
        cands = []
        for c in m.get("candidates", []):
            v = c.get("verification", "")
            vb = badge("ok", "✅ 已核验") if v == "✅" else (
                badge("risk", "⬜ 待补采") if v == "待补" else badge("warn", "⚠️ 候选未核验"))
            price = ("¥%s" % c["unit_price"]) if c.get("unit_price") is not None else "待询价"
            cands.append('<div style="margin-bottom:4px">%s <b>%s</b><br><span style="color:var(--muted)">单价 %s · MOQ %s · %s</span></div>'
                         % (vb, esc(c.get("name", "?")), esc(price), esc(c.get("moq", "—")), esc(c.get("contact", "—"))))
        cb = m.get("cost_budget", {})
        rows.append('<tr><th>%s %s</th><td>%s</td><td>%s</td><td>¥%s<br><span style="color:var(--muted);font-size:11px">%s</span></td></tr>'
                    % (esc(m.get("id", "?")), esc(m.get("name", "")), esc(m.get("function", "")),
                       "".join(cands), esc(cb.get("amount", "—")), esc(cb.get("basis", ""))))
    parts.append('<table><thead><tr><th>模块</th><th>功能</th><th>候选厂（核验/单价/MOQ/联系）</th><th>成本预算</th></tr></thead><tbody>%s</tbody></table>'
                 % "".join(rows))
    parts.append('<div class="foot">数据源：%s（%s）｜标准件 ¥%s（%s）｜注：%s</div>'
                 % (esc(bom.get("source", "")), esc(bom.get("updated", "")),
                    esc(bom.get("standard_parts", {}).get("amount", "—")),
                    esc(bom.get("standard_parts", {}).get("basis", "")), esc(bom.get("note", ""))))
    return "".join(parts)


# ---------------------------------------------------------------- ⑤ 专利规避
def _md_table_rows(md_path, section_marker):
    """从 md 文件中提取指定章节后的第一张表格（活体解析，防数据腐化）。"""
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


def render_patent():
    has = file_exists("research/patent_avoidance.md")
    if not has:
        return ('<div class="banner risk">research/patent_avoidance.md 尚未产出 —— S3 未开始。</div>'
                '<div class="shelf"><b>专利规避 —— 空架子</b></div>')
    parts = ['<div class="banner ok">S3 已完成（2026-08-28 预检索）：12 件专利逐条在 Google Patents 打开确认（含 URL 可复核），2 件种子专利号查无证伪。全文：%s。⚠️ 这是研发级预检索不是法律意见，开模前正式 FTO（佰腾或同级）是不可跳过的闸（C2 / 架构 R1 / S9）。</div>'
             % link("research/patent_avoidance.md")]
    rows = _md_table_rows("research/patent_avoidance.md", "## §4")
    if rows:
        trs = []
        for i, cells in enumerate(rows):
            tag = "th" if i == 0 else "td"
            trs.append("<tr>%s</tr>" % "".join("<%s>%s</%s>" % (tag, esc(re.sub(r"\*\*", "", c)), tag) for c in cells))
        parts.append('<h3>§4 方向风险评级（构建时从 md 活体解析）</h3><table><tbody>%s</tbody></table>' % "".join(trs))
    parts.append('<div class="shelf"><b>逐方向规避设计考量</b>（已注册元素 → 规避决策 → 替代元素）见 %s §3：A 挂机比例/单层百叶/独立数显视窗/背部整面热排；B 整面细网 81%%/无收音机构图/单旋钮；C 放弃（几素在权族+诉讼）；D squircle 截面/百叶网罩纹样/数显位置。防御建议：squircle 截面+温度数显窗+独立热排组合尽早申请<b>自有</b>外观+实用新型。</div>'
                 % link("research/patent_avoidance.md"))
    parts.append('<div class="foot">相关档案：%s ｜ %s</div>'
                 % (link("research/patents_desktop_fans.md"), link("design/form-directions.md", "design/form-directions.md §8 专利规避设计说明框架")))
    return "".join(parts)


# ---------------------------------------------------------------- ⑥ 需求与决策
def parse_md_tables(path):
    """解析 markdown：[(nearest_heading, headers, rows)]。通用解析，不做列语义假设。"""
    if not os.path.exists(path):
        return []
    tables, heading, cur = [], "", None
    for line in open(path, encoding="utf-8"):
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


def render_requirements(decisions):
    parts = []
    brief = os.path.join(REPO_ROOT, "requirements", "requirements-brief.md")
    tables = parse_md_tables(brief)
    wanted = ("2. 硬约束", "3. 用户需求", "5. 商业约束", "7. 待用户拍板")
    parts.append('<div class="req-sec"><h3>需求追溯表（源：%s，每条需求挂证据 [U-Lxxxx]/[R-文件]/[D]）</h3></div>'
                 % link("requirements/requirements-brief.md"))
    for heading, headers, rows in tables:
        if not any(heading.startswith(w) for w in wanted):
            continue
        head = "".join("<th>%s</th>" % esc(h) for h in headers)
        body = "".join("<tr>%s</tr>" % "".join(
            "<td>%s</td>" % (esc(re.sub(r"\*\*", "", c)) if i == 0 else esc(re.sub(r"\*\*", "", c)))
            for i, c in enumerate(row)) for row in rows)
        parts.append('<div class="req-sec"><h3>%s</h3><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                     % (esc(heading), head, body))

    parts.append('<div class="req-sec"><h3>决策时间线（data/decisions.json —— S7 物证：口头验收不算，每个「已验收」必须有记录）</h3>')
    parts.append('<div class="timeline">')
    for d in sorted(decisions.get("decisions", []), key=lambda x: x.get("date", "")):
        vb = {"认可": "ok", "否决": "risk", "转向": "warn"}.get(d.get("verdict"), "todo")
        ev = "、".join(link(e.split(" ")[0].split("§")[0], e) for e in d.get("evidence", []))
        parts.append('<div class="tl-item"><b>%s</b> %s %s<br><b>对象：</b>%s<br><span class="q">原话：%s</span><br><b>后续动作：</b>%s%s</div>'
                     % (esc(d.get("date", "")), badge(vb, d.get("verdict", "")), esc(d.get("id", "")),
                        esc(d.get("object", "")), esc(d.get("quote", "")), esc(d.get("action", "")),
                        ("<br><b>物证：</b>" + ev) if ev else ""))
    parts.append('</div></div>')
    parts.append('<div class="foot">Q1–Q3 待拍板项见「① 流水线总览」底部阻塞项与 %s §7。' % link("requirements/requirements-brief.md"))
    return "".join(parts)


# ---------------------------------------------------------------- main
def main():
    # G-数据闸：构建前先跑闸（写 data/validation_report.json + data/pipeline_status.json）
    report = validate.run_checks()
    with open(validate.REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    st = pipe_status.build_status(report)
    with open(pipe_status.STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=2)

    comp = load_json("research/competitors.json", {"items": []})
    bom = load_json("data/bom.json", {"modules": []})
    forms = load_json("data/forms.json", {"forms": []})
    decisions = load_json("data/decisions.json", {"decisions": []})

    tpl = open(os.path.join(BASE, "templates", "workbench.html"), encoding="utf-8").read()
    out = (tpl
           .replace("__GENERATED_AT__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
           .replace("__TAB_OVERVIEW__", render_overview(st, report))
           .replace("__TAB_COMPETITORS__", render_competitors(comp, report))
           .replace("__TAB_FORMS__", render_forms(forms, st))
           .replace("__TAB_SUPPLY__", render_supply(bom))
           .replace("__TAB_PATENT__", render_patent())
           .replace("__TAB_REQUIREMENTS__", render_requirements(decisions)))

    os.makedirs(DIST, exist_ok=True)
    out_path = os.path.join(DIST, "workbench.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print("BUILT: %s | size KB: %d | competitors: %d | forms: %d | bom modules: %d"
          % (out_path, len(out) // 1024, len(comp.get("items", [])),
             len(forms.get("forms", [])), len(bom.get("modules", []))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
