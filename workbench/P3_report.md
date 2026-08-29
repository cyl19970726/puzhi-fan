# P3 交付报告 —— 工作台前端 Phase 3（六视图按冻结规格重写）

日期：2026-08-30 ｜ 入口：`workbench/dist/index.html`（旧 `dist/workbench.html` 为 legacy，保留未动）
构建：`python3 workbench/build.py` → validate 闸（保留）→ data 快照 `dist/data/`（10 拷贝 + 3 构建时解析产物）→ 拷贝 `src/`+`vendor/` → 写 `dist/index.html` 壳（import map 指向本地 vendor，无业务 HTML）。

## 1. 六视图截图（1440×900，ego-browser task space 'litecool p3'）

| 视图 | 截图 | 验收一句话 |
|---|---|---|
| ① 总览 | `workbench/dist/p3_shots/01_pipeline.png` | 与冻结稿并排无结构差异：阻塞卡置顶（2 条供应商动作，编号圆点+右端徽章）、S0–S9 横条含闸结果、最近三决策、数据新鲜度行齐全 |
| ② 市场证据 | `workbench/dist/p3_shots/02_competitors.png` | 品类结论置顶（制冷带 4 款 ¥106.25–168.3、温度数显无人做）+ S1 闸 banner + segmented 筛选行（全部/风冷 6/制冷 4/设计 3）+ 卡片网格首行可见 |
| ③ 形态决策 | `workbench/dist/p3_shots/03_forms.png` | 与冻结稿并排无结构差异：Q1 结论行（D-2026-08-29-01）、三卡 hero 四层媒体（概念图/AI皮肤/白模/3D）+ 六维星条 + 专利徽章 + W1/W2 折叠 + 均分 4.2/4.2/3.3 |
| ④ 工程实现 | `workbench/dist/p3_shots/04_assembly.png`（爆炸 75% · 16 标注）；`04_assembly_b.png`（形态 B） | 查看器占首屏 ≥60%，三形态 segmented 切换（40/35/37 件），爆炸标注 16 标签、BOM 卡、图鉴缩略图 ×3、R8 banner + BOM 八模块表 |
| ⑤ 合规 | `workbench/dist/p3_shots/05_patent.png` | §4 评级表（构建时活体解析，5 方向 badge 化）+ 逐方向规避要点 + FTO 闸状态（S3 初判 / S9 未开始）首屏可读 |
| ⑥ 决策档案 | `workbench/dist/p3_shots/06_decisions.png` | 时间线最新在上（6 条，verdict 徽章+原话+理由+物证链接），需求追溯表 4 张（§2/§3/§5/§7）在下 |

console：`window.__errs = []`（六视图依次走一遍后仍为空，error + unhandledrejection 双 hook）。

## 2. 数据元素零丢失对照（旧 build.py 六视图清单逐项打勾）

### ① 流水线总览
- [x] G-数据闸 banner（pass 14 / warn 4 / fail 1 + 「待补占位」规则）→ 进度 sec-meta 计数 + 折叠区规则文案
- [x] S0–S9 阶段：状态/闸结果（闸✓⚠✗未接）→ 横条短态 + 折叠区闸徽章
- [x] 阶段闸规则全文 / 产物清单（存在性+链接+mtime+不存在标注）/ note → 折叠「阶段产物与闸明细」（10 段，11 个产物链接）
- [x] 阻塞项 Q1–Q3（id/decision/options/blocks + 源）→ 折叠区「待拍板决策登记」
- [x] 最近三决策（id/verdict 徽章/对象/理由）→ 冻结稿 dlist
- [x] 数据新鲜度行（pipeline_status/forms/bom/decisions/competitors mtime，来自 meta.json 真实 mtime）
- [x] 新增：供应商动作阻塞卡（语蝉鸣 NDA / 臻源待复，全部字段取自 bom.json M1 candidates，禁伪造）

### ② 竞品分析
- [x] S1 数据完整度 banner（13/13 有评价原文、空壳率 0% <20%、闸过、更新日期）
- [x] 卡片：名称+「数据完整」徽章 / 主图（assets 存在才渲染）/ 价格·销量·店铺·品类 / 形态原型徽章 / 制冷 warn 徽章
- [x] 特性 chips（CLAIM_RE JS 移植：数值宣称 ⚠️ 黄底 + hover 诚实参数提示，与 validate.py 同正则）
- [x] functional 解读（pre-line）/ 好评·差评原文 details（条数）/ 商品链接
- [x] 待补灰卡占位（缺 link/评价/主图时触发，当前 13 款全完整未触发，代码路径在）
- [x] 新增：品类结论 banner（温度数显无人做）+ segmented 筛选（实测 制冷→4 款）

### ③ 形态对比
- [x] Q1 结论 banner（已选定 A · D-2026-08-29-01 · B/D 备份基线 · 决策记录链接）
- [x] 四层媒体：概念图（子项 1/2）/ AI皮肤（GLB）/ 白模（¾正侧背顶子项）/ 3D（GLB，懒加载实测有 canvas）
- [x] 状态徽章（已选定/待验收）+ 专利徽章（中/低–中/中–高 + hover note）
- [x] 六维星条（accent/空星 + hover 注记）+ 均分（六维实算 4.2/4.2/3.3）
- [x] 尺寸/特征/架构三行（architecture=engineering_cost level+note）
- [x] 备注/验收/专利规避落实 details（notes 全文）
- [x] W1/W2 探索折叠（GLB 待补 ph + 概念图 + notes）
- [x] pending_decision 字段（foot「待拍板处置」）+ AI 皮肤仅展示声明 + 预检索≠正式 FTO 提示

### ④ 3D 拆分 + 供应链
- [x] 装配体 banner（三形态件数 + DFM/爆炸向量说明）+ GLB 文件链接 foot
- [x] 查看器五功能（见 §4 断言）：加载 / 爆炸滑块 / 透视 / 标注 16 标签 / BOM 卡；三形态切换懒加载 + 离场重置滑块（实测 B 切换后 A 滑块归 0）
- [x] 零件清单按 M1–M8 分组（40/35/37 件）
- [x] 图鉴缩略图 ×3（点击放大）
- [x] R8 banner（≈¥73 / ≈¥82 vs ¥55–65，差 ≈¥20）+ gap 处置全文 foot
- [x] BOM 八模块表（候选厂核验三态徽章/单价/MOQ/联系 + 成本预算 basis）
- [x] foot：bom.source / updated / 标准件 / note
- [x] 空架子 empty（GLB/parts 缺失时，具名+动作，当前未触发）

### ⑤ 专利规避
- [x] S3 预检索 banner（12 件确认 / 2 件查无证伪 / FTO 不可跳过 + 全文链接）
- [x] §4 方向风险评级表（构建时活体解析 → patent_ratings.json，5 行）
- [x] 逐方向规避要点（A/B/C/D + forms patent_risk 徽章）+ 防御建议（自有申请）
- [x] FTO 闸状态（S3 进行·初判 / S9 未开始 + 闸规则 + 待核验重点）
- [x] foot 档案链接（patents_desktop_fans.md / form-directions.md §8）
- [x] §4 缺失时具名 empty（当前未触发）

### ⑥ 需求与决策
- [x] 决策时间线最新在上（6 条：date/id/verdict 徽章/对象/原话/理由/后续动作/物证链接）
- [x] 需求追溯表 §2 硬约束 / §3 用户需求 / §5 商业约束 / §7 待拍板（构建时解析 → requirements.json）
- [x] foot：Q1–Q3 处置指引 + requirements-brief.md 链接

## 3. computed style 采样（证明 tokens 生效）

| 采样项 | 期望值 | 实测值 |
|---|---|---|
| 顶栏高 | 48px | `48px` ✓ |
| 侧栏宽 | 232px | `232px` ✓ |
| H1 | 28px serif | `28px` `"Songti SC","Noto Serif CJK SC",serif` ✓ |
| badge tint ok | #EEF4F0 | `rgb(238, 244, 240)` ✓ |
| badge tint warn | #F7F1E3 | `rgb(247, 241, 227)` ✓ |
| badge tint risk | #F8EEEC | `rgb(248, 238, 236)` ✓ |
| 章节间距 | 48px | `marginBottom: 48px` ✓ |

## 4. 机械验证清单（spec §6）

1. [x] `node --input-type=module --check` 全部 17 个 src js 通过（`node --check` 直查 .js 会被当 CJS 误报 ESM，故用 stdin+input-type=module 口径）
2. [x] ego-browser 六视图 1440×900 截图并逐张 ReadMediaFile 对照冻结稿（见 §1）
3. [x] computed 采样（见 §3）
4. [x] 查看器五功能 DOM 断言：canvas 加载 ✓ / 爆炸滑块 input 生效 ✓ / 透视 toggle active ✓ / 爆炸 80% 后 `.asm-label`=16 ✓ / 点零件 BOM 卡出模块候选厂 ✓（另测：形态 B 懒加载 canvas ✓、离场滑块重置 ✓、图鉴 ×3 ✓）
5. [x] 数据元素零丢失对照（见 §2）
6. [x] console 无错：六视图遍历后 `window.__errs=[]`

构建输出：`snapshots: 10+3 | assets missing: 0 | validate: pass 14 / warn 4 / fail 1`。

## 5. 遗留（诚实清单）

1. **③ 媒体层标签与冻结稿措辞差异**：冻结稿按钮为「概念图/渲染/五视图/3D」，实现按任务书+spec §3 用「概念图/AI皮肤/白模/3D」（四层媒体口径）；布局形态一致。
2. **① 阻塞卡为两条活跃 ODM**（对齐冻结稿两条）：第三条候选（鑫创纪元，可信度降级）未上卡，数据仍在 BOM 表可见。
3. **专利徽章未含旧版「预检索/初判⚠️」tag**：level+hover note 保留；主三形态均 provisional=false，仅 W1/W2 为初判（折叠区「待补」徽章表达）。
4. **③ 白模子项标签 B 卡带 CMF 前缀**（¾奶/正奶/…/¾绿/正绿），为双 CMF 文件名实映射，冻结稿未展示该态。
5. **node --check 口径**：如 CI 直接 `node --check file.js` 需 Node ≥22 的模块自动检测；本报告已用 ESM 口径全量验证。
6. dist/p3_shots/ 为本次验收证据截图，随 dist 保留。
