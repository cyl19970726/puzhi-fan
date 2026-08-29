// main.js —— 启动 + hash 路由（六视图挂载）+ 顶栏/侧栏壳（冻结稿骨架）。
// 数据流：build.py 快照 dist/data/ → state.js loadSnapshot → store → views 只读渲染。
import { h } from './lib/dom.js';
import { store, loadSnapshot } from './state.js';
import { createSidebar, markSidebarCurrent } from './components/sidebar.js';
import * as pipeline from './views/pipeline.js';
import * as competitors from './views/competitors.js';
import * as forms from './views/forms.js';
import * as assembly from './views/assembly.js';
import * as patent from './views/patent.js';
import * as decisions from './views/decisions.js';

const CHAPTERS = [
  { id: 'pipeline', no: '①', label: '总览', mount: pipeline.mount, src: 'data/pipeline_status.json' },
  { id: 'competitors', no: '②', label: '市场证据', mount: competitors.mount, src: 'research/competitors.json' },
  { id: 'forms', no: '③', label: '形态决策', mount: forms.mount, src: 'data/forms.json' },
  { id: 'assembly', no: '④', label: '工程实现', mount: assembly.mount, src: 'cad/assembly_*_parts.json' },
  { id: 'patent', no: '⑤', label: '合规', mount: patent.mount, src: 'research/patent_avoidance.md' },
  { id: 'decisions', no: '⑥', label: '决策档案', mount: decisions.mount, src: 'data/decisions.json' },
];
const DEFAULT_VIEW = 'pipeline';

// dist/data/ 快照清单（build.py 写入；视图只读 store，不直接读文件）
const SNAPSHOT = {
  pipeline: 'pipeline_status.json',
  validation: 'validation_report.json',
  decisions: 'decisions.json',
  forms: 'forms.json',
  bom: 'bom.json',
  competitors: 'competitors.json',
  labels: 'labels.json',
  asm_a: 'assembly_a_parts.json',
  asm_b: 'assembly_b_parts.json',
  asm_d: 'assembly_d_parts.json',
  meta: 'meta.json',
  patent: 'patent_ratings.json',
  requirements: 'requirements.json',
};

// 侧栏状态点：导航本身 = 流水线状态一瞥（design_goal §2）
function chapterDots() {
  const st = store.get('pipeline') || { stages: [] };
  const bom = store.get('bom') || {};
  const gate = id => (st.stages.find(s => s.id === id) || {}).gate_result;
  const dot = g => g === 'pass' ? 'ok' : g === 'warn' ? 'warn' : g === 'fail' ? 'risk' : 'warn';
  return {
    pipeline: null,
    competitors: dot(gate('S1')),
    forms: dot(gate('S2')),
    assembly: /风险/.test(((bom.cost_summary || {}).gap) || '') ? 'risk' : dot(gate('S5')),
    patent: dot(gate('S3')),
    decisions: gate('S7') === 'pass' ? 'ok' : dot(gate('S7')),
  };
}

export async function startApp(rootEl) {
  rootEl.appendChild(h('div', { class: 'empty', style: { margin: '48px auto', maxWidth: '480px' } },
    h('b', {}, '数据加载中'), h('div', { class: 'act' }, '读取 dist/data/ 快照…')));
  try {
    await loadSnapshot(SNAPSHOT);
  } catch (e) {
    rootEl.innerHTML = '';
    rootEl.appendChild(h('div', { class: 'empty', style: { margin: '48px auto', maxWidth: '480px' } },
      h('b', {}, '数据加载失败'), h('div', { class: 'act' }, String(e.message || e)),
      h('div', { class: 'act' }, '先跑 python3 workbench/build.py 生成 dist/ 快照。')));
    throw e;
  }
  rootEl.innerHTML = '';

  // ── 顶栏（48px：品牌 + 数据时间戳 / 面包屑 / 语义图例）──
  const genAt = ((store.get('pipeline') || {}).generated_at || '').slice(0, 16);
  const crumb = h('div', { class: 'crumb' }, '工作台 / ', h('b', {}, ''));
  const topbar = h('header', { class: 'topbar' },
    h('div', { class: 'brand' }, 'LiteCool S1 Workbench',
      h('span', { class: 'ts' }, genAt ? `data ${genAt}` : '')),
    crumb,
    h('div', { class: 'legend' },
      h('span', {}, h('i', { class: 'dot-ok' }), '已核验'),
      h('span', {}, h('i', { class: 'dot-warn' }), '待补'),
      h('span', {}, h('i', { class: 'dot-risk' }), '风险')));

  // ── 侧栏（六章 + 状态点 + 当前章左边条）──
  const dots = chapterDots();
  const chapters = CHAPTERS.map(c => ({ ...c, dot: dots[c.id] }));
  const sidebar = createSidebar({ chapters, current: DEFAULT_VIEW, dataSource: 'data/*.json' });
  const pane = h('main', { class: 'doc' });
  rootEl.append(topbar, h('div', { class: 'shell' }, sidebar, pane));

  function route() {
    const id = location.hash.replace(/^#\/?/, '') || DEFAULT_VIEW;
    const view = CHAPTERS.find(c => c.id === id) || CHAPTERS[0];
    markSidebarCurrent(sidebar, view.id);
    crumb.querySelector('b').textContent = view.label;
    sidebar.querySelector('.side-meta').firstChild.textContent = `数据源 ${view.src}`;
    pane.innerHTML = '';
    view.mount(pane, store);
    scrollTo(0, 0);
  }
  addEventListener('hashchange', route);
  route();
  return { store, route };
}

// 入口壳（dist/index.html）内联 module 显式 import startApp 并调用
// （module script 中 document.currentScript 恒为 null，不能靠 data-autostart 自启）
