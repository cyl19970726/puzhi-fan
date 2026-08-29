// views/forms.js —— ③ 形态决策（冻结稿 丙_v2_形态对比.html 1:1：三卡 hero 四层媒体
// 概念图/AI皮肤/白模/3D + 六维星条 + 专利徽章 + W1W2 折叠 + Q1 结论行）。
// 数据：data/forms.json（+ concepts_v2 / renders / GLB / ai_shell，存在性走 meta.assets）。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { banner } from '../components/banner.js';
import { badge } from '../components/badge.js';
import { stars } from '../components/stars.js';
import { createSegmented } from '../components/segmented.js';
import { createGlbViewer } from '../components/glb-viewer.js';

const DIMS = [
  ['制冷可读性', '可读'], ['差异化', '差异'], ['专利风险', '专利'],
  ['工程代价', '代价'], ['价位匹配', '价位'], ['架构影响', '架构'],
];
const VIEW_LABELS = { three_quarter: '¾', front: '正', side: '侧', back: '背', top: '顶' };

function patentBadge(pr) {
  const lv = (pr || {}).level || '未评估';
  const level = lv.includes('高') ? 'risk' : lv.includes('中') ? 'warn' : lv.includes('低') ? 'ok' : 'todo';
  return badge(level, `专利 ${lv}`, (pr || {}).note || '');
}

function statusBadge(s) {
  const map = { 已选定: 'ok', 待验收: 'warn', 建模中: 'warn', 设计中: 'warn', 已否决: 'risk', 探索: 'todo' };
  return badge(map[s] || 'todo', s || '—');
}

// 白模子项标签：重名 stem（如 B 双 CMF）时带上一级目录前缀
function viewLabel(path) {
  const seg = path.split('/');
  const stem = seg.pop().replace(/\.\w+$/, '');
  const base = VIEW_LABELS[stem] || stem;
  return seg.length > 2 ? `${base}${seg.pop().slice(0, 1)}` : base;
}

function formCard(f, assets, decisionId) {
  const fid = f.id || '?';
  const layers = [];   // { key, label, nodes: [el], glb?: bool }
  const concepts = (f.concept_images || []).filter(p => assets[p]);
  const renders = (f.renders || []).filter(p => assets[p]);
  if (concepts.length) layers.push({ key: 'concept', label: '概念图', nodes: concepts.map(imgNode) });
  if (f.ai_shell && assets[f.ai_shell]) layers.push({ key: 'shell', label: 'AI皮肤', nodes: [glbNode(f.ai_shell)], glb: true });
  if (renders.length) layers.push({ key: 'render', label: '白模', nodes: renders.map(imgNode) });
  if (f.glb && assets[f.glb]) layers.push({ key: 'glb', label: '3D', nodes: [glbNode(f.glb)], glb: true });

  function imgNode(p) {
    const img = h('img', { class: 'layer', src: REL + p, alt: `形态${fid}`, loading: 'lazy', hidden: true });
    img.addEventListener('load', () => {
      if (img.naturalHeight > img.naturalWidth) img.classList.add('tall');   // 竖图 contain（冻结稿 D 卡）
    });
    return img;
  }
  function glbNode(p) {
    return h('div', { class: 'glb-view layer', dataset: { glb: REL + p }, hidden: true });
  }

  const hero = h('div', { class: 'hero' },
    layers.flatMap(l => l.nodes),
    h('span', { class: 'badge bl ' + statusBadge(f.status).className.split(' ')[1] }, f.status || '—'),
    (() => { const b = patentBadge(f.patent_risk); b.classList.add('br'); return b; })());

  // 媒体分层：segmented（media 形态 = 冻结稿 .media 四格条）
  const subsWrap = h('div', { class: 'media-subs', hidden: true });
  let subsSeg = null;
  function showLayer(key, idx = 0) {
    layers.forEach(l => l.nodes.forEach(n => { n.hidden = true; }));
    const l = layers.find(x => x.key === key);
    if (!l) return;
    const node = l.nodes[idx] || l.nodes[0];
    node.hidden = false;
    if (l.glb) createGlbViewer(node, { glbUrl: node.dataset.glb }).init();
    // 子项切换（同层多图：概念图 1/2、白模五视图）——仍是 segmented
    subsWrap.innerHTML = '';
    if (l.nodes.length > 1) {
      const labels = key === 'render' ? renders.map(viewLabel) : l.nodes.map((_, i) => String(i + 1));
      subsSeg = createSegmented({
        options: labels.map((lb, i) => ({ value: i, label: lb })),
        value: idx,
        onChange: i => showLayer(key, i),
      });
      subsWrap.appendChild(subsSeg.el);
      subsWrap.hidden = false;
    } else {
      subsWrap.hidden = true;
    }
  }
  const mediaSeg = createSegmented({
    variant: 'media',
    options: layers.map(l => ({ value: l.key, label: l.label })),
    value: layers[0] && layers[0].key,
    onChange: k => showLayer(k),
  });
  if (layers.length) showLayer(layers[0].key);

  // 六维均分（mono tabular-nums，右对齐）
  const scoreVals = DIMS.map(([d]) => (f.scores || {})[d]).filter(Boolean).map(s => s.stars);
  const avg = scoreVals.length ? (scoreVals.reduce((a, b) => a + b, 0) / scoreVals.length).toFixed(1) : '—';
  const rank = ((f.notes || '').match(/^(\S+)/) || [])[1] || '';
  const selected = f.status === '已选定';

  return h('section', { class: 'fcard' + (selected ? ' sel' : '') },
    hero,
    layers.length ? mediaSeg.el : null,
    subsWrap,
    h('div', { class: 'cbody' },
      h('div', { class: 'chead' },
        h('h2', {}, `${fid} · ${f.name || ''}`),
        h('span', { class: 'fid' }, rank),
        h('span', { class: 'avg' }, avg, h('small', {}, ' /5 均分'))),
      h('p', { class: 'claim' }, f.claim || ''),
      h('div', { class: 'spec' },
        specRow('尺寸', ((f.language || '').split(/[，,；;]/)[0] || '—')),
        specRow('特征', ((f.language || '').split(/[，,；;]/).slice(1).join('；') || '—')),
        specRow('架构', `${(f.engineering_cost || {}).level || '—'} · ${(f.engineering_cost || {}).note || ''}`)),
      h('div', { class: 'scores' },
        DIMS.map(([d, short]) => {
          const s = (f.scores || {})[d];
          if (!s) return null;
          return h('div', { class: 'srow', title: `${d}：${s.note}` },
            h('span', { class: 'slabel' }, short),
            h('span', { class: 'st' }, stars(s.stars)));
        })),
      h('div', { class: 'src' },
        `${f.glb || 'GLB 待产出'} · ${f.status || ''}${selected && decisionId ? ' · ' + decisionId : ''}`),
      f.notes ? h('details', { class: 'fnotes' },
        h('summary', {}, '备注 / 验收 / 专利规避落实'),
        h('div', {}, f.notes)) : null));
}

function specRow(k, v) {
  return h('div', { class: 'row' }, h('span', { class: 'k' }, k), h('span', { class: 'v' }, v));
}

export function mount(el, store) {
  const formsData = store.get('forms') || { forms: [] };
  const meta = store.get('meta') || {};
  const assets = meta.assets || {};
  const decisions = (store.get('decisions') || {}).decisions || [];
  const forms = formsData.forms || [];
  const main = forms.filter(f => f.status !== '探索');
  const explore = forms.filter(f => f.status === '探索');
  const sel = decisions.find(d => /^选定/.test(d.verdict || ''));

  el.append(
    h('h1', {}, '形态决策'),
    h('p', { class: 'lede' }, '本章回答：三个候选形态选哪个、为什么。A / B / D 同屏对比，W1 / W2 收在探索折叠区。'),
  );

  // ── Q1 结论行（一行结论 + 右端链接）──
  el.appendChild(banner('ok', '已选定', [
    'Q1 形态方向已定 ', h('b', {}, 'A 桌面挂机'),
    sel ? ` — ${sel.id}` : '', ' · B / D 装配体保留为备份基线',
  ], { href: '#/decisions', text: '决策记录 →' }));

  // ── A/B/D 三卡一屏 ──
  el.appendChild(h('div', { class: 'cards' },
    main.map(f => formCard(f, assets, sel && sel.id))));

  // ── 探索折叠（W1/W2）──
  if (explore.length) {
    el.appendChild(h('details', { class: 'fold' },
      h('summary', {},
        `探索 — 形态 ${explore.map(f => f.id).join(' / ')}`,
        h('span', { class: 'ph-note' },
          explore.map(f => `${f.id} GLB 待补${f.id === 'W1' ? ' — S6 建模中' : ' — 未排期'}`).join(' · ')),
        h('span', { class: 'arrow' }, '展开 ▸')),
      h('div', { class: 'explore-body' },
        explore.map(f => {
          const img = (f.concept_images || []).find(p => assets[p]);
          return h('div', { class: 'wcard' },
            img ? h('img', { src: REL + img, alt: `形态 ${f.id} ${f.name} 概念图` }) : null,
            h('div', { class: 'wbody' },
              h('div', { class: 'whead' }, h('b', {}, `${f.id} · ${f.name}`), badge('warn', '待补')),
              h('p', {}, f.notes || f.claim || '')));
        }))));
  }

  el.appendChild(h('div', { class: 'foot' },
    `数据源 data/forms.json（${formsData.updated || '—'}）｜AI 皮肤=图生3D 外观网格，仅展示；尺寸/结构以工程装配体为准。`,
    h('br'),
    formsData.pending_decision ? `待拍板处置：${formsData.pending_decision}` : '',
    formsData.pending_decision ? h('br') : '',
    '专利风险为预检索确认；开模前仍须正式 FTO（见 ⑤ 合规）。'));
}
