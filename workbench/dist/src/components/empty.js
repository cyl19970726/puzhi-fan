// empty.js —— 具名空态（spec §3：具名+原因+动作，ink2，虚线 hairline 框）
// empty({ name, reason, action, flat }) —— 「缺什么、为什么空、什么动作会填上」（合同 §2 待补纪律）
import { h } from '../lib/dom.js';

export function empty({ name, reason, action, flat = false }) {
  return h('div', { class: 'empty' + (flat ? ' flat' : '') },
    h('div', {}, h('b', {}, name), reason ? ` —— ${reason}` : ''),
    action ? h('div', { class: 'act' }, action) : null);
}
