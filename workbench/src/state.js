// state.js —— 数据加载（fetch data 快照）+ 极简 store（phase0_contract §9 数据流）
// 数据流：build.py 快照 → state.js fetch → store → views 订阅渲染。视图只读 store，不直接读文件。

export function createStore(initial = {}) {
  const data = { ...initial };
  const subs = new Map(); // key → Set<fn>；'*' 订阅所有变更
  return {
    get(key) { return key === undefined ? data : data[key]; },
    set(key, value) {
      data[key] = value;
      for (const fn of subs.get(key) || []) fn(value, key);
      for (const fn of subs.get('*') || []) fn(value, key);
    },
    subscribe(key, fn) {
      if (!subs.has(key)) subs.set(key, new Set());
      subs.get(key).add(fn);
      return () => subs.get(key).delete(fn);
    },
  };
}

export async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`fetch ${url} → HTTP ${r.status}`);
  return r.json();
}

// 全局 store 单例。DATA_BASE 由入口（dev.html / index.html 壳）注入，指向 dist/data/ 快照目录。
export const store = createStore();

export async function loadSnapshot(files, base = document.documentElement.dataset.dataBase || './data/') {
  const entries = await Promise.all(
    Object.entries(files).map(async ([key, rel]) => [key, await fetchJson(base + rel)]));
  for (const [key, val] of entries) store.set(key, val);
  store.set('ready', true);
  return store;
}
