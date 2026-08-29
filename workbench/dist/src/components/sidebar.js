// sidebar.js —— 六章导航（spec §3：232px side 底；状态点 ok/warn/risk/todo 灰；
// 当前章 paper 底 + 3px 左边条 accent；底部数据源 + 只读说明）[形态实测自冻结稿]
// chapters: [{ id, no, label, dot }] —— dot: 'ok'|'warn'|'risk'|'off'|null
import { h } from '../lib/dom.js';

export function createSidebar({ chapters, current, dataSource }) {
  return h('aside', { class: 'sidebar' },
    h('div', { class: 'side-label' }, '章节'),
    h('nav', { class: 'snav' },
      chapters.map(c =>
        h('a', { href: `#/${c.id}`, class: c.id === current ? 'on' : null, dataset: { view: c.id } },
          h('span', { class: 'no' }, c.no),
          h('span', { class: 'lbl' }, c.label),
          c.dot ? h('span', { class: `dot ${c.dot}` }) : null))),
    h('div', { class: 'side-meta' }, `数据源 ${dataSource || 'data/*.json'}`, h('br'), '只读工作台 · 桌面 1440px+'));
}

// 路由切换时只更新当前章高亮（不重渲染整栏）
export function markSidebarCurrent(sidebarEl, current) {
  sidebarEl.querySelectorAll('.snav a').forEach(a =>
    a.classList.toggle('on', a.dataset.view === current));
}
