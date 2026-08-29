# LiteCool S1 —— 代码架构设计 v1.0

> 本文档定义项目的**流水线阶段、数据层、代码结构、工作台设计**。
> 核心教训（来自 dsh 会话 22dbccff 审计）：呈现层先于数据层 = 空壳进工作台 = 用户判 naive。
> 因此本架构第一原则：**数据层与呈现层严格分离，数据完整度闸不过关，呈现层只渲染"待补"占位。**

## 1. 流水线阶段（S0–S9）

```
S0 需求基线 ──▶ S1 竞品调研 ──▶ ┬─ S2 形态设计 ──┐
 (requirements/   (research/     ├─ S3 专利查询 ──┼─▶ S5 BOM核算 ──▶ S6 3D建模 ──▶ S7 人类验收
  requirements-    competitors/   ├─ S4 供应商询价─┘    (data/bom)     (cad/)        (data/decisions)
  brief.md)        insights)      └──────────────────────────────────────────────┘
                                                                            │
                          S9 正式FTO+开模 ◀── S8 手板验证 ◀── 选定形态 ◀──────┘
                           (外部机构)        (热/声/结构实测)
```

| 阶段 | 输入 → 输出 | 闸（不过不得进入下一阶段） |
|---|---|---|
| S0 需求基线 | 用户意图 → `requirements/requirements-brief.md` | 每条需求有证据溯源；硬约束与待决策分离 |
| S1 竞品调研 | 淘宝/天猫实抓 → `research/competitors.json` + `taobao_*.md` | 每款 ≥1 条评价原文 + link 非空；空壳率 <20% |
| S2 形态设计 | S0+S1 → `design/form-directions.md` | ≥3 个形态语言互不重合的方向 |
| S3 专利查询 | S2 → `research/patent_avoidance.md` | 每条专利有 URL；每方向有逐元素规避说明 |
| S4 供应商询价 | 架构模块表 → `research/1688_*.md/json` | BOM 模块 100% 有候选厂且 ✅；整机 ODM ≥3 家有旺旺记录 |
| S5 BOM 核算 | S4 单价 → `data/bom.json` | 每 SKU 出厂成本±15% 内；超标有处置方案（Q3 类决策） |
| S6 3D 建模 | 选定方向 → `cad/*.glb` + 五视图 | agent 亲自看图验收；mesh 命名映射 M1–M8 |
| S7 人类验收 | 交付包 → `data/decisions.json` | **每个"已验收"状态必须有 decision 记录**（口头验收不算） |
| S8 手板验证 | 样机 → 实测报告 | R2/R3/R5/R6 全过（降温/噪音/凝露/温升） |
| S9 FTO+开模 | S3+S8 → 正式 FTO 报告 | 外部机构比对无近似 |

## 2. 数据层（单一事实源，schema 化）

```
data/
  bom.json          ← M1–M8 模块: {id, 名称, 候选厂[{名,核验✅/⚠️,单价,MOQ,联系}], 成本预算}
  forms.json        ← 形态注册表: {id, 名称, 方向(A/B/D), 状态(设计中/建模中/待验收/已选定/已否决),
                      glb, renders[5], notes, 专利风险, 工程代价, 对比维度评分}
  decisions.json    ← 人类验收记录: [{id(Q1..), 日期, 对象, verdict(认可/否决/转向), 原话, 后续动作}]
research/           ← 原始调研档案（已有，不动结构）: competitors.json, 1688_*.md, patent_avoidance.md, ...
requirements/ architecture/ design/ docs/   ← 文档层（已有）
```

- 数据层只被**生成器写**（脚本或 agent），呈现层只读。
- `decisions.json` 是 S7 的物证化：修复"交付→否决"循环无记录的问题（上轮 5 次口头否决全部散落在会话里）。

## 3. 代码结构

```
puzhi-fan/
├── pipeline/                  ← 编排层（纯 Python 标准库，零新依赖）
│   ├── stages.py              ← 阶段注册表: {id, 名称, 输入路径, 输出路径, 闸函数}
│   ├── validate.py            ← 数据完整度闸: 对 data/ + research/ 跑 schema 与非空率检查,
│   │                            输出 data/validation_report.json（含每字段缺失清单）
│   ├── status.py              ← 汇总各阶段状态(产物存在性+闸结果+mtime) → data/pipeline_status.json
│   └── run.py                 ← CLI: `python3 pipeline/run.py {status|validate|build}`
├── cad/                       ← 每形态一个 build_<form>.py（已有模式，保留）
├── workbench/                 ← 工作台生成器（取代 dashboard/，旧目录冻结保留）
│   ├── build.py               ← 读 data/ + research/ → 渲染 dist/workbench.html（单文件, Three.js CDN）
│   ├── templates/*.html       ← 视图模板（字符串模板，不引 Jinja）
│   └── dist/
├── research/ data/ requirements/ architecture/ design/ docs/
└── dashboard/                 ← 旧版冻结，不再更新
```

三条硬规则：

1. **G-数据闸**：`workbench/build.py` 先跑 `validate.py`；任一数据对象关键字段缺失 → 对应卡片渲染为灰色"待补"占位 + 流水线总览亮黄灯。**不允许空数据渲染成正式卡片。**
2. **G-验收闸**：`forms.json` 里任何形态标"已验收/已选定"，`decisions.json` 必须存在对应记录，否则 validate 报错。
3. **G-诚实参数**：性能宣称字段必须带 `测量条件`，缺失则工作台在该参数旁显示 ⚠️。

## 4. 工作台设计（核心交付物）

单文件静态页（Three.js CDN import map，沿用现有 dashboard 技术栈），六个视图：

| Tab | 内容 | 数据源 |
|---|---|---|
| ① 流水线总览 | S0–S9 状态板：每阶段状态灯（✅完成/🟡进行中/⬜未开始/🔴阻塞）+ 产物链接 + 当前阻塞项（Q1–Q3） | pipeline_status.json |
| ② 竞品分析 | 卡片：主图/价格/销量/评价原文（好评+差评）/评价标签/形态原型分类；数据缺口显示"待补" | competitors.json + competitor_images/ |
| ③ **形态对比**（本架构新增的核心视图） | **A/B/D 多形态同屏对比**：每形态一栏 = 渲染图轮播 + 点击切 3D（GLB 轨道控制）+ 对比表（制冷可读性/差异化/专利风险/工程代价/价位匹配/架构影响）+ 方向主张；底部 Q1 待决提示 | forms.json + cad/*.glb + renders |
| ④ 3D 拆分+供应链 | 选定形态 GLB 热点标注：部件→材质工艺→候选厂（✅/⚠️）→单价→MOQ→联系方式 | bom.json + form GLB |
| ⑤ 专利规避 | 专利清单表（含 URL）+ 每方向"已注册元素→规避决策"对照 | patent_avoidance.md 结构化 |
| ⑥ 需求与决策 | 需求追溯表（C/F/B 系列→证据→验收标准）+ decisions 时间线 | requirements-brief + decisions.json |

设计要求（"做得很好"的判据）：
- 数据密度优先于装饰——这是工程工作台不是营销页；但排版必须有层级（参考上一版 14.9MB 单文件的教训：体积来自 base64 内嵌图，本版图片一律相对路径引用，不内嵌）。
- 所有 ⚠️/待补/假设必须用视觉语言区分于已核验事实（颜色纪律：绿=实测/已核验，黄=候选/待补，红=风险/阻塞）。
- 形态对比视图默认三栏等宽同屏，1080p 下一屏看全三个形态——这是用户点名的验收场景（"同时看到几个产品形态"）。

## 5. 与现网工作的衔接

- 进行中：S1 补抓（agent-2）、S3（agent-0）、S4（agent-1）、S6 形态A（agent-3）。
- 骨架搭建（本次）：pipeline/ + data/ schema + workbench/ 生成器 + 视图 ①②③ 先用现有数据跑通（竞品数据现状即"待补"占位的真实演示）；形态 A 的 GLB 落地后接入视图③，B/D 依次追加。
- 旧 dashboard/ 冻结，工作台以 workbench/ 为准（C5 的验收对象）。
