# 丙 v2 出稿 NOTES（2026-08-30，Phase 1.5）

> 依据 `../design_goal.md`（质量目标 v2）+ FROZEN.md（丙方向选定，质量远超 v1）。
> 两稿：`html/丙_v2_总览.html`（① 总览，新设计）、`html/丙_v2_形态对比.html`（③ v1 丙稿全面升级）。
> 截图：`shot_bing_v2_overview.png` / `shot_bing_v2_forms.png`（ego-browser，1440×900，`pageInfo` 实测两页 ph=900，首屏合同满足）。
> 两稿共用同一套内联 design tokens（`:root` 块逐字一致）；内容硬拷贝自 `data/forms.json` / `data/decisions.json` / `data/pipeline_status.json` / `data/bom.json` / `IMPLEMENTATION_PLAN.md`。
> 视觉判断权归 Owner；本文件只记 token 终值、与 v1 差异及理由、自查打勾，不写"好看"结论。

## 1. Token 终值表（Phase 2 测量底稿）

### 色
| token | 值 | 用途 |
|---|---|---|
| `--bg` | `#F7F7F5` | 页面底 |
| `--paper` | `#FFFFFF` | 卡面/顶栏 |
| `--side` | `#F1F1EF` | 侧栏底/图井/active segmented |
| `--hairline` | `#E3E2DE` | 发丝线（仅分隔） |
| `--ink` | `#37352F` | 主墨 |
| `--ink-2` | `#73716C` | 次墨 |
| `--ink-3` | `#A3A29C` | 弱墨/meta |
| `--accent` = `--ok` | `#2F6B4F` | 强调=已核验（唯一绿色系） |
| `--warn` | `#9A7B2D` | 待补/候选 |
| `--risk` | `#B4544A` | 风险/阻塞 |
| `--ok-tint` / `--ok-line` | `#EEF4F0` / `#CBDDD2` | ok badge 底/边、banner 底/边 |
| `--warn-tint` / `--warn-line` | `#F7F1E3` / `#E3D4B2` | warn badge 底/边 |
| `--risk-tint` / `--risk-line` | `#F8EEEC` / `#E7C8C3` | risk badge 底/边、阻塞卡边 |
| `--star-off` | `#D8D6D0` | 空星/未开始阶段条/灰状态点 |
| （局部常量） | `#E8E7E3` | 侧栏导航 active 底（v1 沿用值） |

### 字阶（5 种，≤6）
| 级别 | 规格 | 字族 |
|---|---|---|
| H1 | 28px / 700 / lh 1.45 | serif（New York/Georgia/Songti SC） |
| 章节题 | 20px / 600 / lh 1.45 | serif |
| 卡片题 | 15px / 600 / lh 1.45 | sans |
| 正文 | 13px / 400 / lh 1.6 | sans |
| meta | 11px / 400 | sans；id/时间戳/数字用 mono + `font-variant-numeric:tabular-nums` |

### 间距（5 档）与圆角
- `--sp-1:8px`（紧凑行距/内边距）· `--sp-2:16px`（常规 gap/卡 padding 档 1）· `--sp-3:20px`（卡 padding 档 2）· `--sp-4:24px`（卡 padding 档 3/区块 gap）· `--sp-5:48px`（章节间距，≥48 达标）
- 圆角：`--r-card:6px`（卡/导航项）· `--r-ctl:4px`（badge/banner/segmented）
- 组件内微值（声明为例外，不计入 5 档）：badge 纵向 padding 2px、媒体 segmented 纵向 6px、图例点-字距 5px、语义边条 3px、阻塞序号圆 22px、导航项 gap 2px。理由：这些是小控件内部尺寸，强行套 8px 档会破坏密度；若 Phase 2 机械测量要求零例外，可全部归并到 8px（已在稿中验证过 8px 变体不溢出）。

### 布局常量
- 顶栏 48px · 侧栏 232px · 正文左右 padding 40px · 正文文本块 max-width 880px（≈67 全角字符，≤72 达标）
- ③ 卡区：`grid 3列 gap 24`，卡宽 ≈360px；hero 图高 172px（A/B `cover`，D 竖图 `contain` 防裁顶）
- 行长实测最长行：① 决策行 D-2026-08-29-03 ≈63 字符 ✓

## 2. 与 v1（丙_doc.html）的 5 条最大差异及理由

1. **语义色全面对齐 design_goal §3，绿色双轨并一轨**：ok `#1F7A45`→`#2F6B4F`（与 accent 合并，v1 同时存在两种绿，违反"强调=唯一非语义色"的单一性）、warn `#A86B00`→`#9A7B2D`、risk `#C1352B`→`#B4544A`、ink-3 `#A6A49D`→`#A3A29C`。badge 底/边 tint 随之重调（更灰、更文档级）。
2. **字阶从 7 档收敛到 5 档**：v1 实际用了 26/16/14/13/12/11/10；v2 = 28/20/15/13/11（§3 条文值）。H1 26→28（§3 值）；卡片题 16 serif→15 sans——15px 衬线在 1x dpi 下发虚，衬线只保留 H1/章节题做"文档排印"签名；正文 13–14 统一 13；来源 10→11（10px 中文不可读，且凑齐 5 档）。
3. **③ 从"图左表右竖堆记录块"改为"三列卡同屏"**：图 240×150 配角→全宽 172px hero（大图主角归位，核销 v1 NOTES 自述的"图不再是绝对主角"取舍，对齐合同 §3.2"每卡大图为主角"）；六维评分从表格单元格改为右对齐星条行（悬浮 title 出注记），均分从来源行收敛为卡头一个关键数字（"评分收敛一行"）。
4. **徽章上 hero + 媒体分层四层化**：状态/专利徽章从卡头右移到 hero 图两上角，卡头只留主张+均分；媒体分层 segmented 从 3 段（渲染/五视图/概念图）扩为 4 段（+3D），对齐 design_goal"媒体四层"；segmented 仍是全站唯一切换控件（核销病灶 2 的纪律延续）。
5. **间距从散值系统化为 5 档 token**：v1 间距是手写散值（10/12/16/18/20/22/24/26/40…）；v2 全部映射到 8/16/20/24/48，章节间距强制 48（§3"≥48px"），组件内微值单独声明（见上表）。这使 Phase 2 tokens.css 可以直接由本表生成。

（另：信息架构按 design_goal §2 换新——六平级 Tab 名改为叙事六章：总览/市场证据/形态决策/工程实现/合规/决策档案，导航项带状态点；① 总览为 v1 没有的新页。这是内容结构变化，不计入上面 5 条视觉差异。侧栏导航状态点当前赋值：②绿 ③绿 ④红（S4 闸未过+用户动作阻塞）⑤黄 ⑥绿。）

## 3. 自查清单（对照 design_goal §3 逐条，截图实测打勾）

### 排印
- [x] 字阶种类 5 ≤ 6（CSS 全文核对，无其他字号）
- [x] H1 28/700 · 章节题 20/600 · 卡片题 15/600 · 正文 13/400 · meta 11/400；行高 1.6（正文）/1.45（标题）
- [x] 数字与英文 mono + tabular-nums（id/时间戳/均分/阶段号/校验计数）
- [x] 正文行长 ≤72 字符（max-width 880px；最长行实测 ≈63 字符）
- [x] 数字右对齐（星条、均分均右对齐）；发丝线仅用于分隔（全稿无装饰线）

### 留白
- [x] 章节间距 48px（① 三个 section 实测）
- [x] 卡片 padding 16/20/24 三档（决策行区 16 / 形态卡 20 / 阻塞卡 20→边框 24 档用于页首区）
- [x] 间距种类 5 档 + 已声明的组件内微值例外

### 色彩
- [x] 纸/底/墨/发丝线/语义色值与 §3 逐项一致（token 表第 1 节）
- [x] 语义色只出现在 badge/状态点/关键数值/3px 边条；无大面积铺色（banner 为单行浅 tint，阻塞卡白底红边）

### 组件与交互
- [x] segmented 是全站唯一切换控件（媒体分层四层）；导航为文档列表（丙方向固有）
- [x] banner 严格一行：结论 + 一个链接
- [x] 空态具名：W1 GLB 待补—S6 建模中 / W2 GLB 待补—未排期（summary 内可见）
- [x] 只读台：全稿无写操作；星级注记走原生 title 悬浮

### 首视口合同（合同 §3.2）
- [x] ① 一屏答"到哪一步/卡在谁"：阻塞卡置顶独立区（等你的动作 ×2），S0–S9 横条一眼读完，ph=900 实测
- [x] ③ A/B/D 三卡一屏看全 + 探索折叠条露出，ph=900 实测
- [x] 每章页首一句"本章回答什么"（quiet operations 语调，无感叹号/营销词）

### 数据纪律
- [x] 全部内容硬拷贝自真实数据（forms/decisions/pipeline_status/bom/IMPLEMENTATION_PLAN）；阻塞卡两条动作来自 IMPLEMENTATION_PLAN.md 行 34–35 与 bom.json contact 字段
- [x] 概念图相对路径 `../../../../concepts_v2/*.png`（A_1/B_cream/D_1/W1/W2 均存在）

### 遗留（Phase 3 实现时处理，静态稿无法表达）
- 键盘可达 / focus-visible 统一 / GLB 骨架屏 / 状态过渡 ≤150ms
- 媒体分层 segmented 的真实切换行为（稿内为静态 on=概念图）
