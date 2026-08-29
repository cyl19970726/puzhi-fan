// views/assembly.js —— ④ 工程实现（assembly-viewer 组件三形态切换 + 下方 BOM 表 + R8 banner + 图鉴缩略图）。
// 数据：assembly_{a,b,d}_parts.json + bom.json + labels.json 快照；GLB/图鉴走 repo 相对路径（只读）。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { banner } from '../components/banner.js';
import { badge } from '../components/badge.js';
import { empty } from '../components/empty.js';
import { createAssemblyViewer } from '../components/assembly-viewer.js';

const FORMS = [
  ['a', 'A 桌面挂机', 'asm_a', 'LiteCool_S1_解构图鉴.png'],
  ['b', 'B 复古收音机', 'asm_b', 'LiteCool_S1_解构图鉴_B.png'],
  ['d', 'D 塔·认真版', 'asm_d', 'LiteCool_S1_解构图鉴_D.png'],
];

export function mount(el, store) {
  const bom = store.get('bom') || { modules: [] };
  const labels = store.get('labels') || {};
  const meta = store.get('meta') || {};
  const assets = meta.assets || {};
  const cost = bom.cost_summary || {};

  el.append(
    h('h1', {}, '工程实现'),
    h('p', { class: 'lede' },
      '本章回答：选定形态怎么造、零件从哪来、成本卡在哪。3D 装配体是尺寸与结构唯一真源；',
      '拖爆炸滑块拆解，点零件看 BOM 卡。'),
  );

  // ── 三形态装配体（已验证组件，直接用）──
  const forms = FORMS.map(([fid, name, key, info]) => {
    const pj = store.get(key) || {};
    return {
      id: fid, name,
      glbUrl: REL + (pj.glb || ''),
      partsJson: `./data/${key.replace('asm_', 'assembly_')}_parts.json`,
      keyLabels: (labels[fid] || []).map(row => row[0]),
      count: (pj.parts || []).length,
      infographic: assets[`cad/infographic/${info}`] ? {
        src: REL + `cad/infographic/${info}`,
        caption: `产品解构图鉴 · ${name}（点击放大）`,
      } : null,
    };
  }).filter(f => f.count > 0);

  if (forms.length) {
    el.appendChild(banner('ok', '装配体', [
      `三形态装配体可切换：${forms.map(f => `${f.name}（${f.count} 件）`).join(' / ')} —— `,
      'DFM 级，Blender 无头 build_core_eng*.py 产出，爆炸向量存于 GLB node extras；',
      '切换自动重置爆炸滑块与选中态（GLB 懒加载）。',
    ]));
    const stage = h('div', {});
    el.appendChild(stage);
    const viewer = createAssemblyViewer(stage, { forms, bomUrl: './data/bom.json' });
    viewer.init();
    el.appendChild(h('div', { class: 'foot' },
      'GLB：', forms.map((f, i) => [i ? ' · ' : '', h('a', { href: f.glbUrl, target: '_blank' }, f.glbUrl.replace(REL, ''))]),
      ' ｜ 关键零件标注清单 cad/infographic/labels.json（单一事实源）'));
  } else {
    el.appendChild(empty({
      name: '3D 拆分热点标注 —— 空架子',
      reason: 'cad/assembly_{a,b,d}*.glb / *_parts.json 缺失',
      action: '先跑 blender --background --python cad/build_core_eng.py 产出装配体。',
    }));
  }

  // ── R8：BOM 超标风险（banner 一行 + 处置全文见下注）──
  el.appendChild(banner('risk', 'R8', [
    `BOM 合计 ≈¥${cost.bom_total ?? '—'}，出厂估算 ≈¥${cost.factory_estimate ?? '—'} vs 目标 ${cost.factory_target ?? '—'}`,
    ' —— 差 ≈¥20，处置已定（D-2026-08-29-03）：询价压实为先。',
  ], { href: '#/decisions', text: '决策记录 →' }));

  // ── 逐模块 BOM 表 ──
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, 'BOM 逐模块'),
      h('span', { class: 'sec-meta' }, `${bom.modules.length} 模块 · 候选厂核验/单价/MOQ/联系 · 三形态通用`)),
    h('table', { class: 'tbl' },
      h('thead', {}, h('tr', {},
        h('th', {}, '模块'), h('th', {}, '功能'), h('th', {}, '候选厂（核验/单价/MOQ/联系）'), h('th', { class: 'num' }, '成本预算'))),
      h('tbody', {},
        (bom.modules || []).map(m =>
          h('tr', {},
            h('th', {}, `${m.id} ${m.name}`),
            h('td', {}, m.function || ''),
            h('td', {},
              (m.candidates || []).map(c => {
                const vb = c.verification === '✅' ? badge('ok', '✅ 已核验')
                  : c.verification === '待补' ? badge('risk', '⬜ 待补采') : badge('warn', '⚠️ 候选未核验');
                const price = c.unit_price != null ? `¥${c.unit_price}` : '待询价';
                return h('div', { style: { marginBottom: '4px' } },
                  vb, ' ', h('b', {}, c.name || '?'), h('br'),
                  h('span', { class: 'mono', style: { color: 'var(--lc-ink2)', fontSize: 'var(--lc-fs-meta)' } },
                    `单价 ${price} · MOQ ${c.moq || '—'} · ${c.contact || '—'}`));
              })),
            h('td', { class: 'num' }, `¥${(m.cost_budget || {}).amount ?? '—'}`,
              h('br'), h('span', { style: { color: 'var(--lc-ink3)', fontSize: 'var(--lc-fs-meta)' } },
                (m.cost_budget || {}).basis || '')))))),
    h('div', { class: 'foot' },
      `数据源：${bom.source || '—'}（${bom.updated || '—'}）｜标准件 ¥${(bom.standard_parts || {}).amount ?? '—'}（${(bom.standard_parts || {}).basis || ''}）`,
      h('br'), `R8 处置全文：${cost.gap || '—'}`, h('br'), `注：${bom.note || '—'}`)));
}
