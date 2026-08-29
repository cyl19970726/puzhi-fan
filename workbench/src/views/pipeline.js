// views/pipeline.js —— ① 总览（冻结稿 丙_v2_总览.html 1:1：阻塞卡置顶 / S0–S9 进度条含闸结果 /
// 最近三决策 / 数据新鲜度行）。数据：pipeline_status.json + decisions.json + bom.json + meta.json。
// 旧视图数据元素保全：阶段产物/闸规则/备注 + Q1–Q3 待拍板登记 → 收入折叠区（合同 §3.3 长内容折叠）。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { blockedCard } from '../components/blocked-card.js';
import { badge } from '../components/badge.js';

const STATUS_SHORT = { done: '完成', doing: '进行', blocked: '阻塞', todo: '未开始' };
const GATE_SHORT = { pass: '闸过', warn: '警告', fail: '闸未过' };

// 闸结果缺省时从 note 提取短态（冻结稿 S3「初判」/ S6「待验收」同口径）
function stageShort(stg) {
  const s = STATUS_SHORT[stg.status] || stg.status;
  if (stg.gate_result && GATE_SHORT[stg.gate_result]) return `${s} · ${GATE_SHORT[stg.gate_result]}`;
  const m = (stg.note || '').match(/初判|待验收|待人类验收/);
  return m ? `${s} · ${m[0].replace('待人类验收', '待验收')}` : s;
}

// 阻塞卡条目：从 bom.json M1 仍活跃（✅ 且 moq 待询/待复）的 ODM 候选派生，禁伪造
function supplierBlockers(bom) {
  const m1 = (bom.modules || []).find(m => m.id === 'M1') || {};
  const active = (m1.candidates || []).filter(c =>
    c.verification === '✅' && /待询|待复/.test(c.moq || '') && !/出局/.test(c.name || ''));
  return active.slice(0, 2).map(c => {   // 冻结稿口径：前两条活跃 ODM 阻塞
    const detail = ((c.contact || '').match(/（(.+)）/) || [])[1] || c.contact || '';
    const person = (detail.match(/对接人\s*([^，；]+)/) || [])[1]
      || (detail.match(/旺旺\s*(\S+?)[\s，；]/) || [])[1] || '';
    const short = (c.name || '').replace(/^整机 ODM 内配（/, '').replace(/）.*$/, '');
    const blocked = /待签\s*NDA/.test(detail);
    const mode = /甲供/.test(detail) ? ' · 甲供模式已确认' : '';
    return {
      title: blocked ? `${short}：签 NDA 后发 GLB/STEP 预评估报价`
                     : `${short}：开模费/组装测试费/首单 MOQ 量级回复`,
      who: person + mode,
      sub: `${c.moq}；${detail}`,
      badgeLevel: blocked ? 'risk' : 'warn',
      badgeText: blocked ? '阻塞' : '待回复',
    };
  });
}

function verdictBadge(v) {
  const s = String(v || '');
  if (/否决|砍掉/.test(s)) return ['risk', s.split(/[（(]/)[0]];
  if (/选定/.test(s)) return ['ok', '选定'];
  if (/转向|推进|组合/.test(s)) return ['warn', s.split(/[（(：:]/)[0]];
  return ['ok', s.split(/[（(]/)[0]];
}

export function mount(el, store) {
  const st = store.get('pipeline') || { stages: [], blockers: [] };
  const dec = (store.get('decisions') || {}).decisions || [];
  const bom = store.get('bom') || {};
  const meta = store.get('meta') || {};
  const vs = st.validation_summary || { pass: 0, warn: 0, fail: 0 };

  el.append(
    h('h1', {}, '总览'),
    h('p', { class: 'lede' },
      '本章回答：项目现在走到哪一步、卡在谁身上、接下来发生什么。进度与阻塞来自 ',
      h('span', { class: 'mono' }, 'pipeline_status.json'), '，决策来自 ',
      h('span', { class: 'mono' }, 'decisions.json'), '。'),
  );

  // ── 当前阻塞：本页视觉锚点 ──
  const failed = st.stages.filter(s => s.gate_result === 'fail').map(s => `${s.id} ${s.name}`);
  const items = supplierBlockers(bom);
  el.appendChild(blockedCard({
    why: failed.length ? `卡住 ${failed.join('、')}（闸未过）→ 报价回填后才能复核 R8 / Q3` : '',
    items,
  }));

  // ── 项目进度 S0–S9 ──
  const counts = { done: 0, doing: 0, blocked: 0, todo: 0 };
  st.stages.forEach(s => { counts[s.status] = (counts[s.status] || 0) + 1; });
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, '项目进度'),
      h('span', { class: 'sec-meta' },
        `S0–S9 · 完成 ${counts.done} · 进行 ${counts.doing} · 阻塞 ${counts.blocked} · 未开始 ${counts.todo} ｜ 校验 `,
        h('span', { class: 'mono' }, `pass ${vs.pass} / warn ${vs.warn} / fail ${vs.fail}`))),
    h('div', { class: 'stages' },
      st.stages.map(stg =>
        h('div', { class: `stage ${stg.status}`, title: stg.note || stg.gate || '' },
          h('span', { class: 'sid' }, stg.id),
          h('span', { class: 'sname' }, stg.name),
          h('span', { class: 'sst' }, stageShort(stg))))),
  ));

  // 旧视图数据元素保全（G-数据闸规则 + 阶段产物/闸/备注 + Q1–Q3 登记），折叠不丢
  const gateBadge = g => g === 'pass' ? badge('ok', '闸 ✓')
    : g === 'warn' ? badge('warn', '闸 ⚠') : g === 'fail' ? badge('risk', '闸 ✗') : badge('todo', '闸未接');
  el.appendChild(h('section', {},
    h('details', { class: 'fold' },
      h('summary', {}, '阶段产物与闸明细',
        h('span', { class: 'ph-note' },
          vs.fail ? `G-数据闸：${vs.fail} fail —— 闸未过的数据对象一律渲染为「待补」占位` : '全部闸状态与产物清单'),
        h('span', { class: 'arrow' }, '展开 ▸')),
      st.stages.map(stg =>
        h('div', { class: 'stage-detail' },
          h('h4', {}, `${stg.id} ${stg.name} `, gateBadge(stg.gate_result)),
          h('div', { class: 'gate' }, `闸：${stg.gate}`),
          stg.artifacts.map(a =>
            h('div', { class: 'art' },
              a.exists ? '✅ ' : '⬜ ',
              a.exists ? h('a', { href: REL + a.path, target: '_blank' }, a.path) : a.path,
              a.mtime ? ` · ${a.mtime}` : (a.exists ? '' : '（不存在）'))),
          stg.note ? h('div', { class: 'note' }, stg.note) : null)),
      st.blockers && st.blockers.length ? h('div', { class: 'stage-detail' },
        h('h4', {}, `待拍板决策登记（源：${st.blockers_source || 'requirements §7'}）`),
        st.blockers.map(b =>
          h('div', { class: 'gate' },
            h('b', {}, `${b.id} ${b.decision}`), ` —— 选项：${b.options}｜阻塞：${b.blocks}`)),
        h('div', { class: 'note' }, 'Q1–Q3 处置记录见 ⑥ 决策档案时间线（D-2026-08-29-01/02/03）。')) : null,
    )));

  // ── 最近决策（最新在上，三条）──
  const latest = [...dec].sort((a, b) => String(b.date).localeCompare(String(a.date)) || String(b.id).localeCompare(String(a.id))).slice(0, 3);
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, '最近决策'),
      h('span', { class: 'sec-meta' }, '最新在上 · 完整时间线见 ⑥ 决策档案')),
    h('div', { class: 'dlist' },
      latest.map(d => {
        const [lv, vt] = verdictBadge(d.verdict);
        const sel = String(d.verdict || '').match(/^选定\s*(.+?)[（(]/);
        return h('div', { class: 'drow' },
          h('span', { class: 'did' }, d.id),
          badge(lv, vt),
          h('div', { class: 'dbody' },
            h('b', {}, sel ? `${d.object} → ${sel[1]}` : d.object),
            h('span', {}, d.rationale || d.action || '')));
      }))));

  // ── 数据新鲜度 ──
  const mt = meta.mtimes || {};
  const fmt = (k, full) => {
    const v = mt[k];
    if (!v) return null;
    return `${k} ${full ? v : v.slice(5)}`;
  };
  const parts = [fmt('pipeline_status', true), fmt('forms'), fmt('bom'), fmt('decisions'), fmt('competitors')]
    .filter(Boolean);
  el.appendChild(h('footer', { class: 'fresh' },
    h('span', { class: 'k' }, '数据新鲜度'),
    h('span', { class: 'mono' }, parts.join(' · ') || '—')));
}
