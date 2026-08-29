// banner.js —— 一行结论 + 右端链接（spec §3：ok/warn/risk 三色 tint 底 + 3px 左边条）
// banner('ok', '已选定', [内容节点...], { href, text }) —— 禁止文字墙（合同 §3.3）
import { h } from '../lib/dom.js';

export function banner(level, tag, content, link) {
  return h('div', { class: `banner ${level}` },
    tag ? h('span', { class: 'tag' }, tag) : null,
    h('span', {}, Array.isArray(content) ? content : [content]),
    link ? h('a', { href: link.href, target: link.external ? '_blank' : null }, link.text) : null);
}
