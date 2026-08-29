# LiteCool S1 — codex 概念图 prompt 规格（v2，2026-08-28）

> 用法：每条 prompt 独立生成，产出后逐张看图筛选。
> 设计纪律：① 品类 = 桌面小空调（TEC 制冷），所有图必须读得出"空调"不是"风扇"；
> ② 签名元素 = 出风温度数显（青色 "22.0°"）；③ NOT 约束是硬约束，违反即重抽；
> ④ 美观锚点 = Muji / Braun(Dieter Rams) / Teenage Engineering 级的小家电质感。

## 共用风格后缀（拼在每条 prompt 末尾）

```
Premium industrial design concept render, photorealistic product photography, soft diffused studio lighting, light warm-gray seamless background, 3/4 perspective view, matte finish, crisp shadows, ultra-detailed CMF, 4k. This is a desktop PERSONAL AIR CONDITIONER (semiconductor Peltier cooling) — NOT a fan: no circular fan grille, no visible fan blades, no toy-like glossy plastic.
```

## 方向 A · 桌面挂机（2 张候选）

```
A compact horizontal desktop appliance (W220 × H140 × D110mm) designed like a miniature wall-mounted air conditioner: rounded-rectangle monolithic body, one wide horizontal air outlet with a single elegant adjustable louver blade angled slightly downward, a large minimalist digital temperature display "22.0°" in soft cyan on a flush black window at the front-left, a sculpted vertical heat-exhaust grille on the right side panel like the outdoor unit of a split AC, low wide weighted base plinth with a thin dark silicone ring, one precision-machined aluminum knob on the top surface. Matte mist-white body (#F2EFE9), one thin mint-green accent line, seamless parting lines.
```

## 方向 B · 复古收音机（2 张候选：奶油白胡桃木 / 墨绿黄铜）

```
A compact rounded-box desktop appliance (W200 × H150 × D120mm) in the language of a premium 1960s radio: the entire front face (over 80%) is one uniform fine woven metal grille with no circular speaker zone, no tuning dial, no frequency markings; a single large knurled walnut-wood knob centered on the top panel; a small round black display window showing "22.0°" in cyan at the top front edge; four short squat round feet; cream-white body with walnut wood accents, Braun Dieter Rams restraint, soft bevels (R16).
Variant: deep forest green body with brushed brass knob and brass base trim.
```

## 方向 D · 塔·认真版（2 张候选）

```
A premium desktop tower appliance (Ø90 × H230mm) with a superellipse squircle cross-section: seamless one-piece lofted body flowing into a wide Ø110 weighted base with a dark-gray silicone ring; the front face carries horizontal louver slats (NOT a radial fan grille); a large digital temperature display "22.0°" in cyan is set into a sculpted 35° sloped top face like a fifth surface; a vertical pill-shaped heat-exhaust column on the back; matte mist-white body with a thin mint-green waist line, Muji-like restraint, monolithic ceramic-like presence.
```

## 野卡 W1 · 氛围灯融合（1 张）

```
A desktop personal cooling device that reads as a premium ambient table lamp: a soft cylindrical frosted-glass upper body with a subtle cool-blue gradient light ring at the outlet height indicating active cooling, hidden slot air outlet, tiny monochrome temperature display "22.0°" on a ceramic-texture base, warm evening desk scene with soft bokeh, emotional but precise industrial design.
```

## 野卡 W2 · 精工铝unibody（1 张）

```
A horizontal cylindrical desktop cooling device machined from a single anodized aluminum unibody (titanium gray), precision-drilled micro-perforation air outlet band wrapping the front third, one flush monochrome display showing "22.0°", a single orange anodized accent ring and matching knob, Teenage Engineering meets aerospace precision, obsessive machining detail, cool studio lighting.
```

## 筛选清单（每张图生成后按此验收，任一不过 = 重抽）

- [ ] 第一眼读得出"小空调/降温设备"，不是风扇（无圆网罩塔扇既视感）
- [ ] 温度数显 "22.0°" 清晰可见
- [ ] 符合该方向形态语言（A 挂机/B 收音机/D 塔/W1 灯/W2 铝柱）
- [ ] 无 NOT 违禁元素（圆网罩/扇叶/玩具感亮塑料/收音机构图(B)/放射辐条(D)）
- [ ] CMF 有高级感（哑光、分色克制、细节可读）
- [ ] 美观一票否决：构图脏、比例怪、廉价感 → 直接重抽
