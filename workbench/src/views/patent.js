// views/patent.js —— ⑤ 合规（§4 评级表（构建时从 research/patent_avoidance.md 活体解析）
// + 逐方向规避要点 + FTO 闸状态）。
import { h } from '../lib/dom.js';
import { REL } from '../state.js';
import { banner } from '../components/banner.js';
import { badge } from '../components/badge.js';
import { empty } from '../components/empty.js';

// 逐方向规避要点（静态文案，源 research/patent_avoidance.md §3 逐方向小节）
const AVOID = [
  ['A 桌面挂机', '比例不仿挂机（矮方体+桌面脚架）· 单层手动百叶（避开双板对开结构）· 数显独立视窗 · 背部整面热排识别面'],
  ['B 复古收音机', '整面均匀细网 81%（无偏置喇叭区/无调频刻度）· 单旋钮非三联布局 · 热排出背部/顶部 · 与猫王/Divoom 构图拉开'],
  ['C 悬浮环/无叶', '放弃 —— 几素 CN217029352U 在权族 Active+诉讼记录，核心结构权利要求覆盖宽，规避空间极小'],
  ['D 塔形', 'squircle 截面非正圆 · 百叶/参数化开孔非放射公版纹样 · 数显置顶部斜面 · 塔身-底座一体轮廓 · 背部 pill 热排'],
];

function levelBadge(text) {
  const s = String(text || '');
  const lv = s.includes('高') ? 'risk' : s.includes('中') ? 'warn' : s.includes('低') ? 'ok' : 'todo';
  return badge(lv, s.replace(/\*\*/g, ''));
}

export function mount(el, store) {
  const pr = store.get('patent') || {};
  const rows = pr.ratings || [];
  const st = store.get('pipeline') || { stages: [] };
  const forms = (store.get('forms') || {}).forms || [];
  const s3 = st.stages.find(s => s.id === 'S3') || {};
  const s9 = st.stages.find(s => s.id === 'S9') || {};

  el.append(
    h('h1', {}, '合规'),
    h('p', { class: 'lede' },
      '本章回答：每个形态方向的专利风险多大、怎么规避、离开模前的正式 FTO 还差什么。'),
  );

  el.appendChild(banner('ok', 'S3 预检索', [
    '12 件专利逐条在 Google Patents 打开确认（含 URL 可复核），2 件种子专利号查无证伪 —— ',
    '研发级预检索不是法律意见，开模前正式 FTO 是不可跳过的闸（C2 / 架构 R1 / S9）。',
  ], { href: REL + 'research/patent_avoidance.md', text: 'patent_avoidance.md 全文 →', external: true }));

  // ── §4 方向风险评级（构建时从 md 活体解析）──
  if (rows.length) {    const [head, ...body] = rows;
    el.appendChild(h('section', {},
      h('div', { class: 'sec-head' },
        h('h2', {}, '§4 方向风险评级'),
        h('span', { class: 'sec-meta' }, '构建时从 research/patent_avoidance.md 活体解析')),
      h('table', { class: 'tbl' },
        h('thead', {}, h('tr', {}, head.map(c => h('th', {}, c.replace(/\*\*/g, ''))))),
        h('tbody', {}, body.map(cells =>
          h('tr', {},
            h('th', {}, (cells[0] || '').replace(/\*\*/g, '')),
            h('td', {}, levelBadge(cells[1])),
            h('td', {}, (cells[2] || '').replace(/\*\*/g, ''))))))));
  } else {
    el.appendChild(empty({
      name: '§4 方向风险评级 —— 待补',
      reason: 'research/patent_avoidance.md 尚未产出或 §4 表缺失（S3 未完成）',
      action: '完成 S3 预检索并重跑 build.py 后自动填入（构建时活体解析，不接受手抄）。',
    }));
  }

  // ── 逐方向规避要点 ──
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, '逐方向规避要点'),
      h('span', { class: 'sec-meta' }, '已注册元素 → 规避决策 → 替代元素 · 详见 §3')),
    h('div', { class: 'dlist' },
      AVOID.map(([dir, text]) => {
        const f = forms.find(x => dir.startsWith(x.id));
        return h('div', { class: 'drow' },
          h('span', { class: 'did' }, dir),
          f ? levelBadge(`专利 ${(f.patent_risk || {}).level || '—'}`) : badge('risk', '放弃'),
          h('div', { class: 'dbody' }, h('span', {}, text)));
      })),
    h('div', { class: 'foot' },
      '防御建议：squircle 截面+温度数显窗+独立热排组合尽早申请自有外观+实用新型（交叉筹码）。')));

  // ── FTO 闸状态 ──
  el.appendChild(h('section', {},
    h('div', { class: 'sec-head' },
      h('h2', {}, 'FTO 闸状态'),
      h('span', { class: 'sec-meta' }, '预检索 ≠ 正式 FTO')),
    h('div', { class: 'dlist' },
      h('div', { class: 'drow' },
        h('span', { class: 'did' }, 'S3 专利查询'),
        badge('warn', '进行 · 初判'),
        h('div', { class: 'dbody' }, h('span', {}, `闸：${s3.gate || '—'}。${s3.note || ''}`))),
      h('div', { class: 'drow' },
        h('span', { class: 'did' }, 'S9 正式 FTO+开模'),
        badge('todo', '未开始'),
        h('div', { class: 'dbody' }, h('span', {},
          `闸：${s9.gate || '—'}。待核验候选全部号码复核（重点 CN121782663B 发明授权、几素 CN2237248xx/9xx 系列）`,
          ` + 外观近似比对（佰腾或同级代理所出报告）后才可开模。`)))),
    h('div', { class: 'foot' },
      '相关档案：',
      h('a', { href: REL + 'research/patents_desktop_fans.md', target: '_blank' }, 'research/patents_desktop_fans.md'),
      ' ｜ ',
      h('a', { href: REL + 'design/form-directions.md', target: '_blank' }, 'design/form-directions.md §8 专利规避设计说明框架'))));
}
