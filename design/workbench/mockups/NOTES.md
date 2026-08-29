# Phase 1 出稿 NOTES（2026-08-30）

三稿内容完全相同（A/B/D 形态卡 + concepts_v2 概念图相对路径 + 六维评分一行 + 状态/专利徽章 + Q1 已定 banner + 六视图导航 + W1/W2 折叠），仅视觉语言不同。1440×900 桌面视口，首屏露出完整判读区。
截图：`shot_jia.png` / `shot_yi.png` / `shot_bing.png`；对比图：`contact_sheet.png`（`make_contact_sheet.py` 生成）。
视觉判断权归 Owner；本文件只记录方向信条与 token 速记（Phase 2 测量起点），不写"好看"结论。

## 方向甲「工程极简」— `html/甲_linear.html`

信条：信息密度优先、发丝线分区、单强调色只给交互态与评分，等宽字体承载一切数据（时间戳/尺寸/来源），视觉锚点=形态大图。

token 速记（抄自 CSS `:root`）：
- 底色 `#FAFAFA` / 卡片 `#FFFFFF` / 发丝线 `#E4E4E7`（软 `#EEEEF0`）
- 墨色 `#18181B`（次 `#52525B` / 弱 `#A1A1AA`）/ 强调 `#5E6AD2`（软底 `#EEF0FC`）
- 语义色 ok `#16A34A` warn `#B45309` risk `#DC2626`
- 字阶：base 13px sans / 卡名 14px 600 / 主张 12.5px / 数据 10–11px mono；顶栏 48px、banner 34px、hero 300px、圆角 8px（控件 5–7px）

实现备注：
- 已选定卡用 `box-shadow:0 0 0 1px accent` 描边，不用填充色块。
- 状态徽章浮于大图左上、专利徽章右上，媒体分层 segmented 浮于大图底中（半透明白底）。
- 六维评分单行 `flex-wrap:wrap`（卡宽 457px 下刚好一行）；mono 星号，空星 `#D4D4D8`。

## 方向乙「产品画廊」— `html/乙_gallery.html`

信条：大图即全部。无卡片边框，靠留白分栏；细字重层级替代线条；密度最低，胶囊控件全圆角。

token 速记：
- 底色 `#FFFFFF` / 图井 `#F5F5F7` / 发丝线 `rgba(0,0,0,.08)`
- 墨色 `#1D1D1F`（次 `#6E6E73` / 弱 `#AEAEB2`）/ 强调 `#0066CC`（仅链接）
- 语义色 ok `#248A3D` warn `#B25000` risk `#D70015`
- 字阶：H1 30px 700 / 卡名 19px 700 / 主张 13px / 规格 12.5px / 评分 10–11px mono；顶栏 52px（毛玻璃）、banner 40px、hero 296px、圆角 20px（图井）/980px（胶囊）

实现备注：
- 评分行必须用 mono 字族且 `.card{min-width:0}`——sans 星号过宽会把 grid 列撑爆（已踩过，横向溢出裁掉第三卡）。
- banner 居中、无底色块，靠 `已选定` 绿字起强调；顶栏 `backdrop-filter:blur(12px)`。
- 六视图导航与媒体分层同为 980px 胶囊 segmented，保持 §4 单一控件语言。

## 方向丙「文档排印」— `html/丙_doc.html`

信条：页面即文档。衬线标题+正文流，形态卡降级为"记录块"（图左表右），六维评分进表格单元格，打印感。

token 速记：
- 底色 `#F7F7F5` / 纸面 `#FFFFFF` / 侧栏 `#F1F1EF` / 发丝线 `#E3E2DE`
- 墨色 `#37352F`（次 `#73716C` / 弱 `#A6A49D`）/ 强调 `#2F6B4F`
- 语义色 ok `#1F7A45` warn `#A86B00` risk `#C1352B`
- 字阶：H1 26px serif 700 / 记录标题 16px serif 600 / 正文 13–14px / 表格 11–12px / 来源 10px mono；顶栏 44px、记录图 240×150、圆角 3–6px

实现备注：
- 导航下沉左侧栏（Notion 式列表），顶栏只留品牌+时间戳+面包屑+图例——这是对 §3.1"导航居顶栏"的有意偏离，方向固有，若 Owner 选丙需在 Phase 2 合同中追认。
- banner 为文档 callout：左侧 3px 强调色边条；已选定记录块同样 3px 左边条。
- 表格键列 `td.k` 浅底窄列；三记录块+折叠区压进 900px 的代价是图高只有 150px（图不再是绝对主角，文档方向固有取舍）。

## 三稿共性决策（Phase 2 继承）

- 六视图导航与卡内媒体分层（渲染/五视图/概念图）统一为 segmented 一种控件语言（核销病灶 2）。
- banner 严格一行：结论+一个链接（核销病灶 5）；数据时间戳常驻顶栏左（核销病灶 7）。
- 卡内三级：卡名+主张（大）/ 尺寸·特征·架构（中）/ 来源 glb 路径（小、mono 弱化）（核销病灶 4）。
- D 塔为竖图，`object-fit:contain` 防裁顶（`img.tall`）；A/B 横图用 `cover`。
- 徽章专利风险等级随卡：A 中（warn）/ B 低–中（ok）/ D 中–高（risk）。
- W1/W2 收 `<details>` 折叠，summary 内置具名待补占位（W1 GLB 待补—S6 建模中 / W2 未排期）。
- 概念图相对路径 `../../../../concepts_v2/*.png`（html/ → repo 根上四级）。
