// main.js —— 启动 + hash 路由（六视图，phase0_contract §9）
// 视图为占位函数：Phase 3 实现。视图注册表与 §4 组件 registry 对应，禁止同一需求两个实现。
import { h } from './lib/dom.js';
import { store } from './state.js';

const VIEWS = {
  overview:    { title: '① 流水线总览',  mount: placeholder('pipeline') },
  competitors: { title: '② 竞品分析',    mount: placeholder('competitors') },
  forms:       { title: '③ 形态对比',    mount: placeholder('forms') },
  assembly:    { title: '④ 3D拆分+供应链', mount: placeholder('assembly') },
  patent:      { title: '⑤ 专利规避',    mount: placeholder('patent') },
  decisions:   { title: '⑥ 需求与决策',  mount: placeholder('decisions') },
};
const DEFAULT_VIEW = 'overview';

function placeholder(name) {
  return el => el.appendChild(h('div', { class: 'ph' },
    `视图 ${name} —— Phase 3 实现（占位，数据源走 store，不直接读文件）`));
}

export function startApp(rootEl) {
  const nav = h('nav', { class: 'seg-nav' },
    Object.entries(VIEWS).map(([id, v]) =>
      h('button', { dataset: { view: id }, onclick: () => { location.hash = id; } }, v.title)));
  const pane = h('main', { class: 'view-pane' });
  rootEl.append(nav, pane);

  function route() {
    const id = location.hash.replace(/^#\/?/, '') || DEFAULT_VIEW;
    const view = VIEWS[id] || VIEWS[DEFAULT_VIEW];
    nav.querySelectorAll('button').forEach(b =>
      b.classList.toggle('active', b.dataset.view === (VIEWS[id] ? id : DEFAULT_VIEW)));
    pane.innerHTML = '';
    view.mount(pane, store);
  }
  addEventListener('hashchange', route);
  route();
  return { store, route };
}

// 直接以本文件为入口打开时自动启动（dev 壳以外的主壳 index.html 由后续 build.py 生成）
if (typeof document !== 'undefined' && document.currentScript?.dataset.autostart !== undefined) {
  startApp(document.getElementById('app'));
}
