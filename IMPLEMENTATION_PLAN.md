# LiteCool S1 重设计实施计划

## Stage 1: 前序工作审计 + handoff
**Goal**: 对 dsh 会话 22dbccff 的竞品/供应商研究工作做物证审计，产出可交接的 handoff packet
**Success Criteria**: packet 过 `handoff_packet.py --check`
**Status**: Complete → `docs/handoff-research-audit-22dbccff.md`

## Stage 2: 需求基线重整
**Goal**: 把散落在 11 版 design-spec 补丁、会话消息、insights 里的需求收敛成单一事实源
**Success Criteria**: 每条需求可追溯到证据（user message / 竞品物证）；硬约束与待定决策分离
**Status**: Complete → `requirements/requirements-brief.md`

## Stage 3: 完整产品架构设计
**Goal**: 系统级架构：功能/热风道/电子/结构/交互 + 模块接口 + 预算 + ADR
**Success Criteria**: 每个模块有接口、预算、供应链映射；关键决策有备选与证伪条件
**Status**: Complete → `architecture/product-architecture.md`

## Stage 4: 工业设计方向重设计 + 全形态执行
**Goal**: ≥4 个真正差异化的形态方向；逐个把各形态做出完整 3D（概念图+工程装配体+AI 皮肤）
**Success Criteria**: 方向稿六维对比；每形态：codex 概念图（视觉闸）+ DFM 级装配体 GLB（40/35/37 件）+ 解构图鉴 + AI 图生3D 皮肤（还原度 ≥3/5）
**Status**: Complete → `design/form-directions.md`、`concepts_v2/`、`cad/assembly_{a_eng,b,d}.glb`、`cad/infographic/`×3、`cad/ai_shell_{a,b,d}/`；Q1 已定 A（D-2026-08-29-01）

## Stage 5: 研究数据补齐 + 专利规避 + 供应商对接
**Goal**: ① 专利检索+规避设计说明 ② 1688 供应商补全核验+旺旺询价 ③ 淘宝差评实抓
**Success Criteria**: 专利有 URL 可复核+逐方向规避说明；BOM 100% 覆盖且✅；ODM 旺旺记录归档；竞品每款≥1 条评价原文+link
**Status**: Complete → ① `research/patent_avoidance.md`（12 件确认/2 件证伪/C 方向实锤放弃）；② `1688_factories.md` §8–11 + `1688_rfq_notes.md`（8 家询价：5 拒 1 降级 2 进入实质流程——蓝鲸喜、臻源）；③ `competitors.json` 13 款实抓空壳率 0%

## Stage 6: 选定方向后的落地（当前阶段）
**Goal**: design-spec 对齐决策 → 受控资料包 → NDA → 报价压实 → 手板验证 → 正式 FTO → 开模
**Status**: In Progress
- ✅ design-spec v3.3（形态 A/双 SKU/导风板扫风/定价策略，全面对齐 D-2026-08-29-01~03）
- ✅ RFQ 询价包 `rfq/ODM_RFQ_package.md` + NDA 模板 `rfq/NDA_template.md` + 受控资料包 `rfq/controlled_package/`
- ✅ S8 手板验证计划 `docs/S8_prototype_test_plan.md`（T1–T7：降温/噪音/热排/凝露/密封/扫风寿命/续航）
- ⏳ 用户电话李伟（蓝鲸喜 199****2258）+ 臻源电话（待索要）约 NDA
- ⏳ 1688 第二轮跟进（08-30 10:41 自动任务）：臻源开模费/组装费量级、鑫创纪元最后通牒
- ⬜ NDA 签署 → 外发受控包 → 报价回填 bom.json 复核 R8/Q3 → 功能样机 → T1–T7 实测 → 正式 FTO（佰腾类，约 1 周，与手板并行）→ DFM 评审 → 开模（3–6 周）

## Stage 7: 流水线编排层 + 工作台生成器骨架
**Goal**: 按 docs/code-architecture.md 搭 pipeline/ + data/ schema + workbench/ 生成器
**Success Criteria**: `python3 pipeline/run.py build` 跑通；validate 如实标出数据缺口；空数据只渲染「待补」占位；形态对比一屏看全
**Status**: Complete → `pipeline/`、`data/{bom,forms,decisions}.json`、`workbench/dist/workbench.html`（六 Tab 产品画廊级，④ 三装配体切换+爆炸/透视/标注/BOM 卡）

## Stage 8: 工作台重设计（丙方向，五阶段管线）
**Goal**: 按 harness-frontend-product-design 流程重做工作台前端：Phase 0 合同 → Phase 1 出稿 → 冻结 → Phase 2 规格 → Phase 3 实现 → Phase 4 Owner 验收
**Status**: In Progress
- ✅ Phase 0 合同 `design/workbench/phase0_contract.md`（含 §9 前端架构：无构建链 ES-module）
- ✅ Phase 1/1.5 出稿与冻结：丙方向 v2 两稿（mockups/FROZEN.md changelog；甲/乙 DEAD）
- ✅ Phase 2 规格 `design/workbench/visual-spec-v2.md`（token 终值=NOTES_v2）
- ⏳ Phase 3 六视图重写（执行中）→ 机械验收 → 切 dist/index.html 正式入口
- ⬜ Phase 4 Owner 并排验收

## Stage 9: 3D 打印自打样（S8 前置解耦）
**Goal**: 3D 打印结构件 + 购买功能件，单台 ≈¥400–600/1 周，把 T1–T7 热架构验证从 ODM 谈判解耦
**Success Criteria**: cad/stl/ A 类件 STL 校验全绿 + PRINT_GUIDE + purchase_list（样品询价状态）
**Status**: Complete（2026-08-30）→ `cad/stl/` 23 件 STL（Voxel Remesh 修复 15 件穿插/破面，731→227MB）+ `validation_report.md`（23/23 全绿，3 件工艺风险带建议）+ `PRINT_GUIDE.md` + `purchase_list.md`（六家旺旺样品询价已发待复，未支付）
