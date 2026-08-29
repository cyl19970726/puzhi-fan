// views/competitors.js —— ② 市场证据（品类结论置顶 + 筛选行 + 卡片网格 + 待补灰卡）。
// 数据：research/competitors.json 快照 + validation_report（S1 闸/空壳率/诚实参数宣称清单）。
// 空壳款按 G-数据闸渲染灰色「待补」占位，不渲染成正式卡片。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { banner } from '../components/banner.js';
import { badge } from '../components/badge.js';
import { createSegmented } from '../components/segmented.js';

// pipeline/validate.py CLAIM_RE 的 JS 移植（G-诚实参数：竞品数值宣称无测量条件，引用前必须实测）
const CLAIM_RE = /\d+\s*(dB|分贝|小时|h\b|H\b|°C|℃|度|档|W\b|mAh|CFM|%)/;

export function mount(el, store) {
  const comp = store.get('competitors') || { items: [] };
  const val = store.get('validation') || {};
  const st = store.get('pipeline') || { stages: [] };
  const meta = store.get('meta') || {};
  const assets = meta.assets || {};
  const items = comp.items || [];
  const det = (val.details || {}).competitors || {};
  const claims = new Set((det.unconditioned_claims || []).map(c => `${c.item}||${c.claim}`));

  el.append(
    h('h1', {}, '市场证据'),
    h('p', { class: 'lede' },
      '本章回答：品类里已经有什么、我们的差异化空白在哪。每款竞品 ≥1 条评价原文是 S1 闸；',
      '宣称参数均未附测量条件，引用前必须自行实测。'),
  );

  // ── 品类结论置顶（design_goal ②：「温度数显无人做」）──
  const byCat = {};
  items.forEach(it => { const c = it.category || '—'; byCat[c] = (byCat[c] || 0) + 1; });
  const cool = items.filter(it => it.category === '制冷');
  const coolPrices = cool.map(it => it.price).filter(p => typeof p === 'number');
  el.appendChild(banner('ok', '品类结论', [
    `${items.length} 款竞品：制冷带 ${cool.length} 款`,
    coolPrices.length ? `（¥${Math.min(...coolPrices)}–${Math.max(...coolPrices)}）` : '',
    '，竞品数显只显示档位/电量——出风温度数显无人做（F1 差异化空白，「降温看得见」依据）。',
  ], { href: REL + 'research/competitors.json', text: 'competitors.json →', external: true }));

  // ── S1 数据完整度闸 ──
  const s1 = st.stages.find(s => s.id === 'S1') || {};
  const rate = (det.shell_rate || 0) * 100;
  el.appendChild(banner(s1.gate_result === 'pass' ? 'ok' : 'warn', 'S1 闸', [
    `数据完整度：${det.complete ?? '—'}/${det.total ?? items.length} 款有评价原文，空壳率 ${rate.toFixed(0)}%（闸要求 <20%）`,
    s1.gate_result === 'pass' ? ' —— 闸过。' : ' —— 闸未过，空壳款渲染为「待补」占位。',
    ` 数据更新：${String(comp.updated || '—').split('（')[0]}`,
  ]));

  // ── 筛选行（segmented 唯一切换控件）──
  const cats = ['全部', ...Object.keys(byCat)];
  const grid = h('div', { class: 'comp-grid' });
  const cnt = h('span', { class: 'cnt' });
  const seg = createSegmented({
    options: cats.map(c => ({ value: c, label: c === '全部' ? '全部' : `${c} ${byCat[c]}` })),
    value: '全部',
    onChange: () => renderGrid(),
  });
  el.appendChild(h('div', { class: 'filter-row' }, seg.el, cnt));
  el.appendChild(grid);

  function renderGrid() {
    const cat = seg.value;
    const shown = cat === '全部' ? items : items.filter(it => (it.category || '—') === cat);
    cnt.textContent = `${shown.length}/${items.length} 款`;
    grid.innerHTML = '';
    shown.forEach(it => grid.appendChild(renderCard(it)));
  }

  function renderCard(it) {
    const name = it.name || '?';
    const nRev = (it.reviews_good || []).length + (it.reviews_bad || []).length;
    const complete = Boolean((it.link || '').trim()) && nRev > 0;
    if (!complete) {
      const missing = [];
      if (!(it.link || '').trim()) missing.push('商品链接');
      if (nRev === 0) missing.push('评价原文（好评/差评）');
      if (!it.image) missing.push('竞品主图');
      return h('div', { class: 'card comp placeholder' },
        h('h3', {}, name),
        h('div', {}, `${it.brand || '—'} · ${it.shop || '—'} · `, h('b', {}, `¥${it.price ?? '—'}`), ` · 销量 ${it.sales || '—'}`),
        h('div', { class: 'missing' }, '⬜ ', h('b', {}, '待补'), `（S1 补抓中）：${missing.join('、')}`,
          h('br'), '空数据按纪律不渲染正式卡片。'));
    }
    const imgOk = it.image && assets[it.image];
    const chips = (it.features || []).map(f => {
      const isClaim = claims.has(`${name}||${f}`) || CLAIM_RE.test(f);
      return h('span', {
        class: 'chip' + (isClaim ? ' claim' : ''),
        title: isClaim ? '竞品宣称，未附测量条件（G-诚实参数）：引用到设计决策/详情页前必须自行实测' : null,
      }, (isClaim ? '⚠️ ' : '') + f);
    });
    const revs = h('div', { class: 'revs' },
      (it.reviews_good || []).length ? h('details', {},
        h('summary', { class: 'good' }, `好评原文 ${it.reviews_good.length} 条`),
        h('ul', { class: 'good' }, it.reviews_good.map(r => h('li', {}, r)))) : null,
      (it.reviews_bad || []).length ? h('details', {},
        h('summary', { class: 'bad' }, `差评/质疑原文 ${it.reviews_bad.length} 条`),
        h('ul', { class: 'bad' }, it.reviews_bad.map(r => h('li', {}, r)))) : null);
    return h('div', { class: 'card comp' },
      h('h3', {}, name, ' ', badge('ok', '数据完整')),
      imgOk ? h('img', { src: REL + it.image, alt: name, loading: 'lazy' }) : null,
      h('div', {}, h('span', { class: 'price' }, `¥${it.price ?? '—'}`),
        ` · 销量 ${it.sales || '—'} · ${it.shop || '—'} · ${it.category || '—'}`),
      h('div', {},
        it.form ? badge('todo', `形态原型: ${it.form}`) : null,
        it.category === '制冷' ? [' ', badge('warn', '制冷')] : null),
      chips.length ? h('div', { class: 'chips' }, chips) : null,
      it.functional ? h('div', { class: 'fn' }, it.functional) : null,
      revs,
      h('div', {}, h('a', { href: it.link, target: '_blank' }, '商品链接 →')));
  }

  renderGrid();
}
