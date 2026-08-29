# ai_shell — 概念图 → 图生3D 外观皮肤(2026-08-29)

目的：Blender 程序化建模(form_a/b/d)做结构骨架，AI 图生3D 从 codex 概念图直接生成
高质感外观网格做**展示皮肤**。本文件记录三方向(A/B/D)的生成、评分、尺寸校验与积分消耗。

## 供应商选型(实测，非推断)

| 后端 | 状态(2026-08-29 实测) | 结论 |
|---|---|---|
| 腾讯混元 Pro / Rapid (`ai3d`) | `ResourceInsufficient` 资源包积分尽(Pro/Rapid 同账号同池，凭证文件与环境变量两套凭证均尽) | ❌ 不可用 |
| Tripo(3 把 key: kiln.tripo / kiln.tripo.2 / blender-harness.tripo,macOS Keychain) | `balance: 0` ×3(8-02 复测为 0,今日复测仍为 0) | ❌ 不可用 |
| Rodin / Hyper3D(codex-rodin-api 等 2 把) | `check_balance: 0` ×2 | ❌ 不可用 |
| **Meshy**(threejs-dreamfall / playable-ip-foundry,同账号) | **balance 905** | ✅ 唯一可用,选型 |

任务首选混元,但账号级积分尽属计费阻塞(需控制台充值/开通后付费，不在授权内),
故按"备选评估"条款落 Meshy。混元充值后可用 `ai_shell_gen.py --backend hunyuan` 重跑对比。

## 管线

1. `cad/ai_shell_gen.py --backend meshy --image <概念图> --dir cad/ai_shell_<x> --pbr`
   - 参数:`should_texture=true, enable_pbr=true, texture_resolution=2k, topology=triangle, origin_at=bottom`,**不 remesh**(保最高细节;展示用途不控面数)。
2. `blender --background --factory-startup --python cad/ai_shell_render.py -- <raw.glb> <dir> <最长边mm>`
   - 均匀缩放使最长边=spec(记录缩放比)→ 底面落地、Apply Transform → 导出 `shell_scaled.glb`
   - 三点 studio 光(key/fill/rim)+ 地面 + turntable 4 视角(az 30/120/210/300,el 15°)+ hero(el 25°),1024px Eevee,曝光 -1.0。
3. 逐张 ReadMediaFile 对照概念图人工评分(1–5)。

## 三方向结果

| 方向 | 概念图 | 还原度 | 最终尺寸 mm(最长边对齐) | 缩放比 | 三角面 | 积分 | GLB |
|---|---|---|---|---|---|---|---|
| A 桌面挂机 | concepts_v2/A_1.png | **4/5** | 220.0×140.7×107.6(spec 220×140×110 ✓) | 0.115571 | 1,990,768 | 30 | `ai_shell_a/shell_scaled.glb`(64MB,raw 79.5MB) |
| B 复古收音机·奶油 | concepts_v2/B_cream.png | **4/5** | 200.0×103.3×127.7(spec 机身 200 宽 ✓;总高含脚 103 偏低,见下) | 0.105069 | 1,981,944 | 30 | `ai_shell_b/shell_scaled.glb`(86MB,raw 113MB) |
| D 塔 | concepts_v2/D_1.png | **4/5** | 104.4×107.9×230.0(spec 底座 Ø110、总高 230 ✓) | 0.120825 | 1,996,762 | 30 | `ai_shell_d/shell_scaled.glb`(63MB,raw 79.8MB) |

渲染图:`cad/ai_shell_{a,b,d}/renders/{turntable_0..3,hero}.png`;
每方向另有 `input/concept.png`、`api/{submit,query}.json`、`raw/meshy_raw.glb`、`manifest.json`、`scale_report.json`。

**积分合计:90(905→815)。每次 30cr(贴图 2k+PBR)。** 无重抽(三方向均一次过 ≥3)。

### A — 4/5
保留：数显窗(teal "22.0°" 数码管)✓、薄荷腰线 ✓、横置出风口+下压导风板 ✓、右侧竖条热排格栅(带凹框)✓、顶部旋钮 ✓、底座滑板 ✓。
偏差:① "PERSONAL AIR CONDITIONER" 小字丢失;② 数显窗黑玻璃贴图有灰斑(糊);③ 出风口凹腔偏浅,导风板不如概念图挺拔;④ 棱线普遍偏"充气感"(AI 网格通病,可接受)。网格无破洞/悬浮。

### B — 4/5
保留：整面编织网罩(编织纹理可读)✓、胡桃/金属边框 ✓、顶部大旋钮 ✓、圆数显 "22.0°" ✓、4 木脚 ✓、奶油壳体 ✓。正面 hero 与概念图非常接近。
偏差:① 旋钮滚花丢失、颜色由深胡桃偏香槟金;② 侧/背面被发明了竖条格栅,且背面格栅上有**乱码浮雕文字**(AI 幻觉,正面不可见);③ 概念侧面为净面。网格无破洞。
高度说明:缩放按最长边=宽 200mm 对齐;AI 网格自身高宽比(0.52)低于工程 spec(机身 150 高+脚 10),故总高 103mm——AI 网格比例漂移,仅作展示皮肤不影响。

### D — 4/5
保留：35° 斜顶数显(teal "22.0°" 黑窗)✓、正面水平百叶(细密可读)✓、右侧 pill 排热柱 ✓、底座圆盘+深灰硅胶圈 ✓、塔身 squircle 轮廓 ✓。
偏差:① 薄荷腰线极淡(近不可读);② 左侧多了一条竖槽格栅(概念仅右侧 pill,疑 AI 对称化);③ 顶部旋钮/制冷键未生成(概念图 D_1 顶面本就只画数显,不算丢)。网格三面干净,无破洞。

## 用途划分:皮肤 = 展示,骨架 = 工程

- **AI 皮肤(`ai_shell_*`)**:单 mesh、约 200 万三角、全三角无拓扑/owner/UV 分层、2k PBR 贴图。
  只用于营销渲染、turntable、详情页 hero。**不可**用于开模/结构评审/3D 打印。
- **工程装配体(`assembly_*.glb` / `form_*.blend`)**:保留为结构骨架——分件、命名、尺寸链、
  堆叠(电池/PCB/风机/TEC)全部以它为准。
- 集成建议:以工程装配体 bbox 为唯一尺寸真源;皮肤按 `scale_report.json` 的 `scale_factor`
  对齐(已做到最长边一致)。注意 AI 网格**比例会漂**(如 B 高宽比 0.52 vs spec 0.75)——
  皮肤只做"看起来像",任何配合面/间隙都以骨架为准;若需皮肤贴骨架,只允许非均匀微拉
  (≤5%)且不得影响正视轮廓。workbench 集成另做,不在本次范围。

## 看图修掉的问题(过程记录)

1. **相机 40 米外空渲**:`cam_data.angle` 已是弧度,脚本误再 `radians()` 一次 → turntable 全空。修为直接用弧度,并用旧 GLB 试渲验证。
2. **过曝**:白壳+白背景高光全炸 → 灯能量 900/450/1100→400/150/600、world 0.6→0.35、曝光 -1.0,A 重渲后腰线/数显可读。
3. **B 下载中断**:assets.meshy.ai 直连 ~110KB/s 且 89MB 处 `curl (18)` 断流、续传被 `Connection reset` → 改 `curl -C -` 断点续传 + 走本机 Clash 代理(127.0.0.1:7890)完成;`ai_shell_gen.py` 已固化 `curl_download()` 续传重试。D 全程代理下载正常。GLB 均已校验头/长度。

## 复跑

```bash
# 任一方向重抽(换参数/换图):
python3 cad/ai_shell_gen.py --backend meshy --image concepts_v2/B_green.png --dir cad/ai_shell_b_green --pbr
blender --background --factory-startup --python cad/ai_shell_render.py -- \
    cad/ai_shell_b_green/raw/meshy_raw.glb cad/ai_shell_b_green 200
# 混元恢复积分后对比:
python3 cad/ai_shell_gen.py --backend hunyuan --image concepts_v2/A_1.png --dir cad/ai_shell_a_hy --model 3.1 --faces 80000 --pbr
```
