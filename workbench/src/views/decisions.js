// views/decisions.js —— ⑥ 决策档案（时间线最新在上 + 需求追溯表）。
// 数据：decisions.json + requirements.json（构建时从 requirements-brief.md 解析 §2/§3/§5/§7）。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { badge } from '../components/badge.js';

function verdictLevel(v) {
  const s = String(v || '');
  if (/否决|砍掉/.test(s)) return 'risk';
  if (/转向|推进|组合/.test(s)) return 'warn';
  return 'ok';
}

function verdictShort(v) {
  const s = String(v || '');
  if (s.startsWith('选定')) return '选定';
  return s.split(/[（(：:]/)[0];
}

// 物证条目 → 链接（"path §锚" 或 "path 备注" 形式，取路径段做 href）
function evidenceLinks(ev) {
  const list = Array.isArray(ev) ? ev : (ev ? [ev] : []);
  return list.map(e => {
    const path = String(e).split(' ')[0].split('§')[0].trim();
    return h('a', { href: REL + path, target: '_blank' }, String(e));
  });
}

export function mount(el, store) {
  const decisions = (store.get('decisions') || {}).decisions || [];
  const req = store.get('requirements') || { tables: [] };

  el.append(
    h('h1', {}, '决策档案'),
    h('p', { class: 'lede' },
      '本章回答：每个决策是谁拍的、原话是什么、物证在哪。时间线最新在上；需求追溯表在下。'),
  );

  // ── 决策时间线（最新在上；S7 物证：口头验收不算，每个「已验收」必须有记录）──
  const sorted = [...decisions].sort((a, b) =>
    String(b.date).localeCompare(String(a.date)) || String(b.id).localeCompare(String(a.id)));
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, '决策时间线'),
      h('span', { class: 'sec-meta' },
        `最新在上 · ${sorted.length} 条 · 源 data/decisions.json · S7：口头验收不算，每个「已验收」必须有记录`)),
    h('div', { class: 'timeline' },
      sorted.map(d => {
        const lv = verdictLevel(d.verdict);
        const ev = evidenceLinks(d.evidence);
        return h('div', { class: `tl-item ${lv}` },
          h('b', { class: 'mono' }, d.date || ''), ' ',
          badge(lv, verdictShort(d.verdict)), ' ',
          h('span', { class: 'mono', style: { color: 'var(--lc-ink3)', fontSize: 'var(--lc-fs-meta)' } }, d.id || ''),
          h('br'), h('b', {}, '对象：'), d.object || '',
          d.quote ? [h('br'), h('span', { class: 'q' }, `原话：${d.quote}`)] : null,
          d.rationale ? [h('br'), h('b', {}, '理由：'), d.rationale] : null,
          h('br'), h('b', {}, '后续动作：'), d.action || '',
          ev.length ? [h('br'), h('b', {}, '物证：'),
            ev.flatMap((l, i) => [i ? '、' : '', l])] : null);
      }))));

  // ── 需求追溯表（每条需求挂证据 [U-Lxxxx]/[R-文件]/[D]）──
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, '需求追溯表'),
      h('span', { class: 'sec-meta' },
        '源 requirements/requirements-brief.md · 每条需求挂证据 [U-Lxxxx]/[R-文件]/[D]')),
    (req.tables || []).map(t =>
      h('div', { class: 'req-sec' },
        h('h3', {}, t.heading),
        h('table', { class: 'tbl' },
          h('thead', {}, h('tr', {}, t.headers.map(c => h('th', {}, c)))),
          h('tbody', {}, t.rows.map(row =>
            h('tr', {}, row.map((c, i) =>
              i === 0 ? h('th', {}, c) : h('td', {}, c))))))))));

  el.appendChild(h('div', { class: 'foot' },
    'Q1–Q3 待拍板项的处置记录见上方时间线（D-2026-08-29-01/02/03）与 ① 总览阻塞登记；原始 §7 表见 ',
    h('a', { href: REL + 'requirements/requirements-brief.md', target: '_blank' }, 'requirements-brief.md'), '。'));
}
