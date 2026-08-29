// blocked-card.js —— ① 专用阻塞卡（spec §3：risk tint 底 + 编号圆点 + 状态徽章右端）[实测自冻结稿]
// items: [{ title, who, sub, badgeLevel, badgeText }]
import { h } from '../lib/dom.js';
import { badge } from './badge.js';

export function blockedCard({ title = '当前阻塞 — 等你的动作', why, items }) {
  return h('section', { class: 'blocker' },
    h('div', { class: 'bk-head' },
      h('h2', {}, title),
      why ? h('span', { class: 'bk-why' }, why) : null),
    items.map((it, i) =>
      h('div', { class: 'bk-item' },
        h('span', { class: 'bk-no' }, String(i + 1)),
        h('div', { class: 'bk-body' },
          h('div', { class: 'bk-title' }, it.title,
            it.who ? h('span', { class: 'who' }, it.who) : null),
          it.sub ? h('div', { class: 'bk-sub' }, it.sub) : null),
        it.badgeText ? badge(it.badgeLevel || 'risk', it.badgeText) : null)));
}
