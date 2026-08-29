# concepts_v2 — 生成与筛选记录（2026-08-28）

## 生成方式

全部图片由本机 codex（gpt-5.6-sol，`codex exec`）内置图像生成工具真实生成，流程：
`codex exec --skip-git-repo-check -s workspace-write "用内置图像生成工具按以下 prompt 出一张图，并把 PNG 从 generated_images 拷到 concepts_v2/<名>.png"`
封装脚本：`concepts_v2/gen.sh`（每条的完整 prompt 见同目录 `*.log`）。
原始图保留在 `~/.codex/generated_images/<session-id>/exec-*.png`。

prompt 来源：`design/concept_prompts_v2.md`，每条均拼上共用风格后缀。

## 逐张筛选结果（对照 concept_prompts_v2.md 筛选清单）

| 文件 | 方向 | 轮次 | 结果 | 一句话 |
|---|---|---|---|---|
| A_1.png | A 桌面挂机 | 1 | ✅ 过 | 一次过：横置出风口+下压导风板+右侧排热格栅，空调读感强，薄荷绿腰线+顶旋钮，无任何违禁元素 |
| A_2.png | A 桌面挂机（变体） | 1 | ✅ 过 | 一次过：同语言低机位变体，出风口带冷气流光效；与 A_1 相似度偏高，供二选一 |
| B_cream.png | B 复古收音机·奶油白胡桃木 | 3 | ✅ 过 | 第 3 轮过：格栅均匀无圆形单元、无品牌字、胡桃木旋钮/边框/脚，Braun 式克制 |
| B_green.png | B 复古收音机·墨绿黄铜 | 2 | ✅ 过 | 第 2 轮过：格栅均匀，黄铜旋钮+底座饰条，墨绿哑光高级，数显清晰 |
| D_1.png | D 塔·认真版 | 1 | ✅ 过 | 一次过：squircle 塔身+水平百叶（非放射网罩）+35° 斜顶数显+背部 pill 排热柱+硅胶圈底座，陶瓷感 |
| D_2.png | D 塔·认真版（变体） | 1 | ✅ 过 | 一次过：石墨腰线变体、俯角展示斜顶数显；右侧排热柱略读作"把手"，可接受 |
| W1.png | 野卡·氛围灯 | 1 | ✅ 过 | 一次过：磨砂玻璃灯体+冷蓝光环+陶瓷底座数显，暖夜桌面散景，情绪与精度兼具 |
| W2.png | 野卡·精工铝 unibody | 1 | ✅ 过 | 一次过：钛灰铝柱+微孔出风带+橙色阳极环/旋钮，TE 式精工；机身多了行 "BY PEI" 小字，瑕不掩瑜 |

## 被毙掉的图（保留在同目录备查）

| 文件 | 方向 | 轮次 | 毙因 |
|---|---|---|---|
| B_cream_r1_rejected.png | B 奶油白 | 1 | 格栅后透出两个圆形"喇叭单元"鬼影 → 收音机构图违禁，第一眼读作蓝牙音箱而非空调 |
| B_green_r1_rejected.png | B 墨绿 | 1 | 同上：格栅后圆形驱动单元鬼影，读作音箱 |
| B_cream_r2_rejected.png | B 奶油白 | 2 | 格栅已均匀，但前脸印了 "BRAUN" 品牌 logo → 山寨感，美观一票否决 |

重抽时 prompt 微调：r2 起加"格栅绝对均匀、禁任何圆形/同心圆/喇叭单元"+ "NOT a speaker"；
B_cream r3 再加"禁任何品牌 logo/文字（除 PERSONAL AIR CONDITIONER 小字）"。

## 产物

- 8 张成品：`A_1.png A_2.png B_cream.png B_green.png D_1.png D_2.png W1.png W2.png`
- 对比拼图：`contact_sheet.png`（`make_sheet_v2.py` 生成）
- 生成日志：`<名>.log` / `<名>_r<N>.log`（含完整 prompt 与 codex 输出）
