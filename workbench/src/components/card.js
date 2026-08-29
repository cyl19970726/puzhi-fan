// card.js —— 数据卡（spec §3：paper+hairline 圆角 6；三密度由视图类组合实现：
// hero=③ 形态卡 .fcard / 标准=② 竞品卡 .comp / 紧凑=① 阶段条 .stage）
import { h } from '../lib/dom.js';

export function card(className, ...children) {
  return h('div', { class: ['card', className].filter(Boolean).join(' ') }, children);
}
