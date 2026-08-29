// stars.js —— 星级条（spec §3：★accent / ★空星色，悬浮 title 出注记）[形态实测自冻结稿]
import { h } from '../lib/dom.js';

export function stars(n, note) {
  const on = Math.max(0, Math.min(5, n | 0));
  return h('span', { class: 'stars', title: note || null },
    '★'.repeat(on),
    h('span', { class: 'off' }, '★'.repeat(5 - on)));
}
