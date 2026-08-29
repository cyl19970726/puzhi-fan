"""pipeline/stages.py — LiteCool S1 流水线阶段注册表（S0–S9）。

依据 docs/code-architecture.md §1 表格。纯声明式数据 + 产物路径；
状态判定逻辑在 status.py，闸的检查逻辑在 validate.py。
"""
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rp(*parts):
    """repo 内相对路径 → 绝对路径。"""
    return os.path.join(REPO_ROOT, *parts)


# 每条: id, name, inputs/outputs(repo 相对路径), gate(闸描述), gate_key(validation_report 里对应的闸 id)
STAGES = [
    {
        "id": "S0",
        "name": "需求基线",
        "inputs": ["用户意图"],
        "outputs": ["requirements/requirements-brief.md"],
        "gate": "每条需求有证据溯源；硬约束与待决策分离",
        "gate_key": None,
    },
    {
        "id": "S1",
        "name": "竞品调研",
        "inputs": ["淘宝/天猫实抓"],
        "outputs": ["research/competitors.json", "research/taobao_desktop_fans.md", "research/taobao_competitor_deepdive.md"],
        "gate": "每款 ≥1 条评价原文 + link 非空；空壳率 <20%",
        "gate_key": "S1-竞品数据完整度",
    },
    {
        "id": "S2",
        "name": "形态设计",
        "inputs": ["S0", "S1"],
        "outputs": ["design/form-directions.md", "data/forms.json"],
        "gate": "≥3 个形态语言互不重合的方向",
        "gate_key": "S2-形态方向数量",
    },
    {
        "id": "S3",
        "name": "专利查询",
        "inputs": ["S2"],
        "outputs": ["research/patent_avoidance.md"],
        "gate": "每条专利有 URL；每方向有逐元素规避说明",
        "gate_key": None,
    },
    {
        "id": "S4",
        "name": "供应商询价",
        "inputs": ["架构模块表"],
        "outputs": ["research/1688_factories.md"],
        "gate": "BOM 模块 100% 有候选厂且 ✅；整机 ODM ≥3 家有旺旺记录",
        "gate_key": "S4-供应商核验",
    },
    {
        "id": "S5",
        "name": "BOM 核算",
        "inputs": ["S4 单价"],
        "outputs": ["data/bom.json"],
        "gate": "每 SKU 出厂成本±15% 内；超标有处置方案（Q3 类决策）",
        "gate_key": "S5-成本核算",
    },
    {
        "id": "S6",
        "name": "3D 建模",
        "inputs": ["选定方向"],
        "outputs": ["cad/*.glb"],
        "gate": "agent 亲自看图验收；mesh 命名映射 M1–M8",
        "gate_key": None,
    },
    {
        "id": "S7",
        "name": "人类验收",
        "inputs": ["交付包"],
        "outputs": ["data/decisions.json"],
        "gate": "每个「已验收/已选定」状态必须有 decision 记录（口头验收不算）",
        "gate_key": "G-验收闸",
    },
    {
        "id": "S8",
        "name": "手板验证",
        "inputs": ["样机"],
        "outputs": ["reports/手板实测报告.md"],
        "gate": "R2/R3/R5/R6 全过（降温/噪音/凝露/温升）",
        "gate_key": None,
    },
    {
        "id": "S9",
        "name": "正式 FTO+开模",
        "inputs": ["S3", "S8"],
        "outputs": ["reports/fto_report.md"],
        "gate": "外部机构比对无近似",
        "gate_key": None,
    },
]

STAGE_BY_ID = {s["id"]: s for s in STAGES}
