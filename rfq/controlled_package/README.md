# 受控外发资料包 —— 登记册（NDA 签署后方可外发）

> 纪律（rfq/NDA_template.md 第二条）：外发前确认 ① NDA 已双方签署 ② 本登记册填写接收方与日期 ③ 只发本目录内容，BOM 价格/供应商联系方式/专利检索结论一律不发。

## 包内容（v1，2026-08-29 备）

| # | 文件 | 用途 | 来源 |
|---|---|---|---|
| 1 | `assembly_a_eng.glb`（849KB，40 命名零件） | 结构预评估：可旋转/爆炸拆分，零件含 module/label/explode 元数据 | `cad/assembly_a_eng.glb`（DFM 级，build_core_eng.py） |
| 2 | `LiteCool_S1_解构图鉴.png`（1600×2200） | 结构解析总览：16 件引线标注+双风道+DFM 要点 | `cad/infographic/` |
| 3 | 目标规格表（含测量条件） | 报价确认口径 | `rfq/ODM_RFQ_package.md` §2（外发时另存 PDF） |
| 4 | 结构接口控制表 IF-1~IF-5 | 配合面/密封/装配要求 | `architecture/product-architecture.md` §5.3（外发时另存 PDF） |

## 外发登记

| 日期 | 接收方 | 对接人 | NDA 编号/日期 | 外发内容版本 | 发送人 |
|---|---|---|---|---|---|
| （待填） | 语蝉鸣/蓝鲸喜 | 李伟 199****2258 | （待签） | v1 | |
| （待填） | 东莞臻源电子 | zhenyuan0068（电话待索要） | （待签） | v1 | |

## 注意事项

- GLB 查看：Windows 3D Viewer / Blender / Three.js 均可打开；爆炸向量在 node extras 中。
- 对方如需 STEP：说明本 GLB 为设计意图模型（网格），正式 B-rep STEP 由乙方结构工程师按接口表重建（这也是验对方工程能力的第一题）。
- 本包不含：专利预检索文件、BOM 价格与供应商、概念图源文件、AI 皮肤网格（营销资产）。
