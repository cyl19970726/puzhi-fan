// badge.js —— 状态徽章（spec §3：2px 圆角 tint 底+对应 line 色文字）
// 四态：ok=已核验 / warn=待补·候选 / risk=风险·阻塞 / todo=未开始；「已选定」走 ok。
import { h } from '../lib/dom.js';

export function badge(level, text, title) {
  return h('span', { class: `badge b-${level}`, title: title || null }, text);
}
