// segmented.js —— 全站唯一切换控件（spec §3：hairline 边框胶囊组，active=paper 底+ink）
// 用法：const seg = createSegmented({ options, value, onChange, variant });
//   options: [{ value, label, disabled?, title? }]
//   variant: 'pill'（默认胶囊组）| 'media'（③ 媒体分层条，冻结稿 .media 形态）
import { h } from '../lib/dom.js';

export function createSegmented({ options, value, onChange, variant = 'pill' }) {
  let current = value ?? options.find(o => !o.disabled)?.value;
  const btns = new Map();
  const el = h('div', { class: 'seg' + (variant === 'media' ? ' media' : ''), role: 'tablist' },
    options.map(o => {
      const b = h('button', {
        type: 'button', role: 'tab', disabled: o.disabled || null, title: o.title || null,
        onclick: () => { if (!o.disabled) set(o.value, true); },
      }, o.label);
      btns.set(o.value, b);
      return b;
    }));
  function set(v, fire) {
    current = v;
    for (const [key, b] of btns) b.classList.toggle('on', key === v);
    if (fire && onChange) onChange(v);
  }
  if (current !== undefined) btns.get(current)?.classList.add('on');
  return { el, get value() { return current; }, set: v => set(v, false) };
}
