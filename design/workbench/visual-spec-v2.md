# 工作台视觉规格 visual-spec-v2（Phase 2，2026-08-30）

> 测量来源：冻结稿 `mockups/html/丙_v2_{总览,形态对比}.html`（实现唯一参照，FROZEN.md changelog）。
> 标注：`[实测]`=从冻结稿 computed/CSS 采样；`[推导]`=稿未展示，按信条推（信条见 design_goal.md §3）。
> 本规格的唯一实现出口：`workbench/src/styles/tokens.css`；组件 CSS 只许引用令牌，禁止硬编码。

## 1. 信条（不可违反）

文档排印；衬线只留 H1/章节题；语义色只在徽章/状态点/关键数值/3px 边条；发丝线仅分隔；
一页一个视觉锚点；所有切换一种 segmented 控件；quiet operations 文案。

## 2. 令牌（[实测]，= tokens.css 终值）

**色**：bg `#F7F7F5` / paper `#FFFFFF` / side `#F1F1EF` / hairline `#E3E2DE` / ink `#37352F` · ink2 `#73716C` · ink3 `#A3A29C` / ok=accent `#2F6B4F` / warn `#9A7B2D` / risk `#B4544A` / badge tint 三组（ok `#EEF4F0` warn `#F7F1E3` risk `#F8EEEC`，配对应 line 色）/ 空星 `#D8D6D0` / 模块色号 M1–M8 沿用 tokens.css 既有 `--lc-mod-m*`

**字阶（5 档）**：H1 28/700 serif lh1.45 · 章节题 20/600 serif · 卡片题 15/600 sans · 正文 13/400 lh1.6 · meta 11/400；数字/英文 mono + tabular-nums。字体栈：serif=`"Songti SC","Noto Serif CJK SC",serif`；sans=`-apple-system,"PingFang SC",sans-serif`；mono=`ui-monospace,"SF Mono",monospace` [推导：冻结稿内联栈]

**间距（5 档）**：8 / 16 / 20 / 24 / 48（章节间距强制 48；卡 padding 16/20/24 三档）。圆角 6 / 4。组件内微值例外（badge 2px、seg 6px、边条 3px）[实测+NOTES_v2 声明]

**布局**：顶栏 48px / 侧栏 232px / 文本块 max-width 880px（≈67 字符）/ ③ 三列卡 gap 24、hero 172px（竖图 contain）

## 3. 组件形态（逐状态；[实测]于冻结稿，未展示态标[推导]）

| 组件 | 规格要点 |
|---|---|
| 侧栏导航 | 232px，side 底；六章 + 状态点（ok/warn/risk/todo 灰）；当前章 paper 底+3px 左边条 accent；底部数据源+只读说明 |
| segmented | 唯一切换控件：hairline 边框胶囊组，active=paper 底+ink，inactive=ink2；6px 圆角 |
| badge | 2px 圆角 tint 底+对应 line 色文字：已核验/待补/风险/已选定四态 |
| 数据卡（三密度） | paper+hairline，圆角 6；密度：hero（③形态）/ 标准（②竞品）/ 紧凑（①阶段） |
| 星级条 | ★accent/☆空星，均分右对齐，mono，悬浮 title 出注记 [推导 hover] |
| banner | 一行结论+右端链接：ok/warn/risk 三色 tint 底+3px 左边条 |
| 空态 | 具名+原因+动作，ink2，虚线 hairline 框 |
| 3D 查看器 | 工具条并入查看器顶边（形态 segmented + 滑块 + 透视/标注 toggle）；加载骨架屏 [推导]；BOM 卡右侧固定 320px |
| 表格 | 数字右对齐 tabular-nums；行底发丝线；表头 meta 字重 600 |
| 阻塞卡（①专用） | risk tint 底 + 编号圆点 + 状态徽章右端 |

## 4. 元素→数据映射表（出身标注）

全部元素三出身：**有出处**（data/*.json 字段 / research/ 文件）/ **静态文案**（章节题、说明行）/ **待补**（具名空态）。
详细映射沿用现 workbench/build.py 六视图的数据消费清单（Phase 3 逐视图核销，禁止丢数据元素）：
① pipeline_status.json + decisions.json + 各数据 mtime；② competitors.json(+competitor_images)；③ forms.json(+concepts_v2/renders/GLB/ai_shell)；④ assembly_{a_eng,b,d}_parts.json + bom.json + infographic；⑤ patent_avoidance.md(§4 活体解析)+forms patent_risk；⑥ requirements-brief + decisions.json。
**needs-backend**：无（纯只读静态台）。

## 5. 交互补充（[推导]，静态稿未表达）

键盘 Tab 可达/Enter·Space 激活/focus-visible 统一（2px accent outline offset 2）；
查看器 GLB 加载骨架屏+失败重试；状态过渡 ≤150ms ease-out；`<details>` 折叠默认收起（W1/W2、长备注）。

## 6. 验收机械项（Phase 3 必须跑）

1. `node --check` 全部 src js；2. ego-browser 六视图截图（1440×900）；3. computed style 像素采样：顶栏高 48/侧栏 232/H1 28px/章节间距 48/badge tint 三组值（证明 tokens 生效，不看 diff）；4. 查看器五功能 DOM 断言（加载/爆炸/透视/标注 16 标签/BOM 卡）；5. 数据元素零丢失对照（旧六视图清单）；6. console 无错。
