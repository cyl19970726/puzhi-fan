// assembly-viewer.js —— 装配体查看器（爆炸滑块 / 透视 / CSS2D 标注 / 零件列表 / 点击高亮 / BOM 卡 / 形态切换懒加载）
// 迁自 templates/workbench.html 的 initAssembly() + 三形态切换逻辑，行为逐项保留（见文件尾核销注释）。
// 输入：{ forms: [{id, name, glbUrl, partsJson, keyLabels?, infographic?}], bomUrl }
//       单形态可简写 { glbUrl, partsJson, bomUrl, keyLabels?, name?, infographic? }
// 数据只读：partsJson / bomUrl 由组件 fetch，不接收伪造数据。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { h, esc } from '../lib/dom.js';
import { fetchJson } from '../state.js';

// 关键零件中文标注缺省清单（回退形态 A；单一事实源是 cad/infographic/labels.json，经 keyLabels 注入）
const FALLBACK_KEY_LABELS = ['Body', 'Base', 'M1_Bosses', 'M2_Cell_B', 'M3_PCB', 'M4_FanFrame',
  'M5_TEC', 'M5_ColdFins', 'M5_HotSink', 'M5_Separator', 'M5_EVA', 'M1_Stepper',
  'M1_Pinion', 'Louver_1', 'M6_TwistLock', 'M7_Module'];

// 模块色号走 CSS 变量（tokens.css 可覆盖），inline var() 带兜底
const modColorVar = m => `var(--lc-mod-${String(m || 'M8').toLowerCase()}, var(--lc-todo))`;

// 3D 场景色（Three.js 色值，非 DOM 样式，不属 tokens 管辖）
const SCENE_BG = 0xf3f3f1, HL_COLOR = 0x17a08c, HL_EMISSIVE = 0x0b6e63;

export function createAssemblyViewer(container, opts) {
  const forms = (opts.forms || [{
    id: 'main', name: opts.name || '', glbUrl: opts.glbUrl, partsJson: opts.partsJson,
    keyLabels: opts.keyLabels, infographic: opts.infographic,
  }]).map(f => ({ ...f }));
  const multi = forms.length > 1;
  const viewers = new Map(); // form.id → per-form viewer state

  const bar = multi ? h('div', { class: 'asm-form-bar' },
    forms.map((f, i) => h('button', {
      type: 'button', class: 'asm-form-btn' + (i ? '' : ' active'), dataset: { form: f.id },
      onclick: () => selectForm(f.id),
    }, f.name || f.id, ' ', h('span', { class: 'cnt' }, f.count != null ? `${f.count} 件` : '')))) : null;

  const formEls = forms.map((f, i) =>
    h('div', { class: 'asm-form', dataset: { form: f.id }, hidden: i > 0 }));

  const root = h('div', { class: 'asm-multi' }, bar, formEls);
  container.appendChild(root);

  forms.forEach((f, i) => viewers.set(f.id, buildFormShell(formEls[i], f)));

  function selectForm(id) {
    // 离场块重置滑块/选中态（透视/标注开关保持）；入场块懒加载 GLB
    root.querySelectorAll('.asm-form-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.form === id));
    for (const [fid, v] of viewers) {
      const show = fid === id;
      if (!show && v.inited) v.reset();
      v.formEl.hidden = !show;
    }
    viewers.get(id).init();
  }

  const api = {
    el: root,
    selectForm,
    init: () => viewers.get(forms[0].id).init(),
    reset: () => { for (const v of viewers.values()) if (v.inited) v.reset(); },
    dispose: () => { for (const v of viewers.values()) v.dispose(); root.remove(); },
    viewer: id => viewers.get(id),
  };
  return api;

  // ------------------------------------------------------------ 单形态
  function buildFormShell(formEl, form) {
    // DOM 骨架（class 钩子与旧版一致，样式全走 components.css + tokens 变量）
    const view = h('div', { class: 'asm-view' });
    const slider = h('input', { type: 'range', class: 'asm-explode', min: '0', max: '100', value: '0', step: '1' });
    const xrayBtn = h('button', { type: 'button', class: 'asm-mode', dataset: { mode: 'xray' }, title: '外壳类零件半透明，看内部结构（对标透视图）' }, '透视');
    const labelsBtn = h('button', { type: 'button', class: 'asm-mode active', dataset: { mode: 'labels' }, title: '爆炸滑块 >30% 时显示关键零件中文标注' }, '标注');
    const stage = h('div', { class: 'asm-stage card' }, view,
      h('div', { class: 'asm-bar' },
        h('span', { class: 'asm-bar-label' }, '装配'), slider, h('span', { class: 'asm-bar-label' }, '爆炸'),
        xrayBtn, labelsBtn,
        h('span', { class: 'asm-hint' }, '拖拽旋转 · 滚轮缩放 · 点零件高亮')));
    const partsCard = h('div', { class: 'asm-parts card' }, h('h3', {}, '零件清单'));
    const bomCard = h('div', { class: 'asm-bom card' });
    const side = h('div', { class: 'asm-side' }, partsCard, bomCard);
    const asm = h('div', { class: 'asm' }, stage, side);
    formEl.appendChild(asm);
    if (form.infographic && form.infographic.src) {
      formEl.appendChild(h('div', { class: 'asm-info' },
        h('a', { href: form.infographic.href || form.infographic.src, target: '_blank', title: '点击新窗口打开原图' },
          h('img', { src: form.infographic.src, alt: form.infographic.alt || '产品解构图鉴', loading: 'lazy' }),
          h('span', {}, form.infographic.caption || '产品解构图鉴（点击放大）'))));
    }

    // ── 运行时状态（init 后填充）──
    let inited = false, disposed = false, raf = 0;
    let scene, camera, renderer, labelRenderer, controls;
    let partsMeta = {}, bomModules = {};
    const parts = [];   // {name, obj, base, explode, labelObj?}
    const byName = {};
    let xrayOn = false, labelsOn = true, explodeT = 0, selected = null;

    // 透视模式的外壳类零件：M6 模块（壳体/前壳/腰线/旋扣/导风板）+ Base（对标参考-3 透壳）
    const isGhost = name => (partsMeta[name] || {}).module === 'M6' || name === 'Base';

    const state = { formEl: null, get inited() { return inited; }, init, reset, dispose };
    state.formEl = formEl;

    async function init() {
      if (inited || disposed) return;
      if (view.clientWidth === 0) return; // 不可见（hidden）：等入场后再 init（懒加载）
      inited = true;

      // 数据：parts json + BOM（只读 fetch；parts 列表拿到数据后再渲染分组）
      let partsJson, bom;
      try {
        [partsJson, bom] = await Promise.all([fetchJson(form.partsJson), fetchJson(opts.bomUrl)]);
      } catch (e) {
        view.innerHTML = '<div class="ph">数据加载失败：' + esc(e.message) + '</div>';
        return;
      }
      if (disposed) return;
      partsJson.parts.forEach(p => { partsMeta[p.name] = p; });
      (bom.modules || []).forEach(m => { bomModules[m.id] = m; });
      const KEY_LABELS = form.keyLabels || partsJson.key_labels || FALLBACK_KEY_LABELS;
      renderPartsList(partsJson, bom);
      renderCard(null);

      // ── Three.js 场景 ──
      scene = new THREE.Scene();
      scene.background = new THREE.Color(SCENE_BG);
      camera = new THREE.PerspectiveCamera(40, view.clientWidth / view.clientHeight, 0.01, 50);
      camera.position.set(1.15, 0.95, 1.60);
      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(view.clientWidth, view.clientHeight);
      renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
      view.appendChild(renderer.domElement);
      scene.add(new THREE.HemisphereLight(0xffffff, 0xdfe3e8, 1.6));
      const key = new THREE.DirectionalLight(0xffffff, 1.8); key.position.set(2, 3, 2); scene.add(key);
      const fill = new THREE.DirectionalLight(0xffffff, 0.7); fill.position.set(-1.5, 0.5, -1); scene.add(fill);
      controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;

      // ── 爆炸标注层（CSS2D）：关键零件中文标签，随爆炸滑块显隐 ──
      labelRenderer = new CSS2DRenderer();
      labelRenderer.setSize(view.clientWidth, view.clientHeight);
      labelRenderer.domElement.className = 'asm-labels';
      view.appendChild(labelRenderer.domElement);

      new GLTFLoader().load(form.glbUrl, gltf => {
        if (disposed) return;
        const model = gltf.scene;
        // 坐标矫正：Blender X=高/Z=宽/Y=前 → glTF 后为 (高→X, 宽→Y, 前→-Z)，
        // 先绕 Z 转 90° 让高朝上，再绕 Y 转 180° 让前脸朝相机
        model.rotation.set(0, Math.PI, Math.PI / 2);
        const box = new THREE.Box3().setFromObject(model);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        const k = 1.0 / Math.max(size.x, size.y, size.z);
        model.scale.setScalar(k);
        model.position.sub(center.multiplyScalar(k));
        scene.add(model);
        model.traverse(o => {
          if (!o.userData || !o.userData.explode) return;
          o.traverse(m => {   // 材质按件克隆：高亮/半透明互不串扰（外壳共享 BodyIvory）
            if (m.isMesh) m.material = Array.isArray(m.material)
              ? m.material.map(mt => mt.clone()) : m.material.clone();
          });
          const rec = { name: o.name, obj: o, base: o.position.clone(),
                        explode: new THREE.Vector3().fromArray(o.userData.explode) };
          parts.push(rec);
          byName[o.name] = rec;
        });
        // 关键零件中文标注（文字取 parts.json 的 label，色号按 module）
        scene.updateMatrixWorld(true);
        parts.forEach(p => {
          if (!KEY_LABELS.includes(p.name)) return;
          const meta = partsMeta[p.name] || {};
          const div = h('div', { class: 'asm-label' },
            h('span', { class: 'dot', style: { background: modColorVar(meta.module) } }),
            String(meta.label || p.name).split('(')[0]);
          const lo = new CSS2DObject(div);
          const c = new THREE.Box3().setFromObject(p.obj).getCenter(new THREE.Vector3());
          lo.position.copy(p.obj.worldToLocal(c));   // 挂到零件上，随爆炸一起移动
          lo.visible = false;
          p.obj.add(lo);
          p.labelObj = lo;
        });
        updateLabels();
        paint();   // 加载前若已开透视/已选中，此处补应用
      }, undefined, err => {
        view.innerHTML = '<div class="ph">GLB 加载失败：' + esc(String(err)) + '</div>';
      });

      // ── 交互（事件只绑一次，此时 slider/按钮已存在）──
      // 爆炸滑块 0–1：node.position = base + explode·t（爆炸向量在 GLB node extras，模型局部坐标，随父级缩放）
      slider.addEventListener('input', () => {
        explodeT = slider.value / 100;
        parts.forEach(p => p.obj.position.copy(p.base).addScaledVector(p.explode, explodeT));
        updateLabels();
      });
      // 透视 / 标注 开关
      xrayBtn.addEventListener('click', () => { xrayOn = !xrayOn; xrayBtn.classList.toggle('active', xrayOn); paint(); });
      labelsBtn.addEventListener('click', () => { labelsOn = !labelsOn; labelsBtn.classList.toggle('active', labelsOn); updateLabels(); });
      // 零件列表点击（事件委托，列表是拿到 partsJson 后渲染的）
      partsCard.addEventListener('click', e => {
        const b = e.target.closest('.asm-part');
        if (b) select(b.dataset.part === selected ? null : b.dataset.part);
      });
      // 3D 里直接点零件（raycast 到带 explode extras 的节点；拖拽旋转不触发）
      const ray = new THREE.Raycaster();
      let downAt = null;
      renderer.domElement.addEventListener('pointerdown', e => { downAt = [e.clientX, e.clientY]; });
      renderer.domElement.addEventListener('pointerup', e => {
        if (!downAt || Math.hypot(e.clientX - downAt[0], e.clientY - downAt[1]) > 5) return;
        const r = renderer.domElement.getBoundingClientRect();
        ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1,
                                            -((e.clientY - r.top) / r.height) * 2 + 1), camera);
        const hit = ray.intersectObjects(parts.map(p => p.obj), true)[0];
        if (!hit) { select(null); return; }
        let o = hit.object;
        while (o && !(o.userData && o.userData.explode)) o = o.parent;
        select(o && byName[o.name] && o.name !== selected ? o.name : null);
      });

      (function animate() {
        if (disposed) return;
        raf = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
        labelRenderer.render(scene, camera);
      })();
    }

    // 零件清单：按 BOM 模块顺序分组（M1–M8）
    function renderPartsList(partsJson, bom) {
      const plist = partsJson.parts || [];
      const byMod = {};
      for (const p of plist) (byMod[p.module || '?'] = byMod[p.module || '?'] || []).push(p);
      partsCard.innerHTML = '';
      partsCard.appendChild(h('h3', {}, `零件清单（${plist.length} 件，按 M1–M8 分组）`));
      for (const m of (bom.modules || [])) {
        const mid = m.id || '?';
        if (!byMod[mid]) continue;
        partsCard.appendChild(h('div', { class: 'asm-mod' }, `${mid} ${m.name || ''}（${byMod[mid].length}）`));
        for (const p of byMod[mid]) {
          partsCard.appendChild(h('button', { class: 'asm-part', dataset: { part: p.name } },
            p.label || p.name, h('span', { class: 'pn' }, p.name)));
        }
      }
    }

    function updateLabels() {
      const show = labelsOn && explodeT > 0.3;
      parts.forEach(p => { if (p.labelObj) p.labelObj.visible = show; });
    }

    // 零件选择：目标高亮，其余半透明；透视模式：外壳类零件半透（选中态优先）
    function paint() {
      parts.forEach(p => {
        const dimmed = selected && p.name !== selected;
        const ghost = !dimmed && xrayOn && isGhost(p.name);
        const on = !dimmed && !ghost;
        const opacity = dimmed ? 0.07 : (ghost ? 0.15 : 1);
        p.obj.traverse(m => {
          if (!m.isMesh) return;
          (Array.isArray(m.material) ? m.material : [m.material]).forEach(mt => {
            mt.transparent = !on;
            mt.opacity = opacity;
            mt.depthWrite = on;
            if (mt.color) {
              if (mt.userData.__col === undefined) mt.userData.__col = mt.color.getHex();
              mt.color.setHex(selected && p.name === selected ? HL_COLOR : mt.userData.__col);
            }
            if (mt.emissive) {
              if (selected && p.name === selected) {
                if (!mt.userData.__em) mt.userData.__em = mt.emissive.getHex();
                mt.emissive.setHex(HL_EMISSIVE);
                mt.emissiveIntensity = 1.5;
              } else if (mt.userData.__em !== undefined) {
                mt.emissive.setHex(mt.userData.__em);
                mt.emissiveIntensity = 1;
              }
            }
          });
        });
      });
      partsCard.querySelectorAll('.asm-part').forEach(b =>
        b.classList.toggle('active', b.dataset.part === selected));
    }

    function renderCard(name) {
      if (!name) {
        bomCard.innerHTML = '<h3>BOM 卡</h3><div class="fn">点击右侧零件（或直接点 3D 模型）查看该零件所属模块的候选厂 / 核验 / 单价 / MOQ。</div>';
        return;
      }
      const meta = partsMeta[name] || {};
      const mod = bomModules[meta.module] || {};
      const cands = (mod.candidates || []).map(c => {
        const v = c.verification === '✅' ? '<span class="badge b-ok">✅ 已核验</span>'
          : c.verification === '待补' ? '<span class="badge b-risk">⬜ 待补采</span>'
          : '<span class="badge b-warn">⚠️ 候选未核验</span>';
        const price = c.unit_price != null ? '¥' + c.unit_price : '待询价';
        return '<div class="cand">' + v + ' <b>' + esc(c.name) + '</b><br>'
          + '<span class="meta">单价 ' + esc(price) + ' · MOQ ' + esc(c.moq || '—')
          + ' · ' + esc(c.contact || '—') + '</span></div>';
      }).join('');
      const cb = mod.cost_budget || {};
      bomCard.innerHTML = '<h3>' + esc(meta.label || name)
        + ' <span class="pn">' + esc(name) + '</span></h3>'
        + '<div class="fn">' + esc(meta.module || '') + ' ' + esc(mod.name || '') + ' —— ' + esc(mod.function || '') + '</div>'
        + cands
        + '<div class="budget">模块成本预算 ¥' + esc(cb.amount != null ? cb.amount : '—') + '（' + esc(cb.basis || '') + '）</div>';
    }

    function select(name) { selected = name; paint(); renderCard(name); }

    // 形态切换时外部调用：重置爆炸滑块与选中态（透视/标注开关保持）
    function reset() {
      slider.value = 0;
      explodeT = 0;
      parts.forEach(p => p.obj.position.copy(p.base));
      updateLabels();
      select(null);
    }

    function dispose() {
      disposed = true;
      cancelAnimationFrame(raf);
      if (renderer) { renderer.dispose(); renderer.domElement.remove(); }
      if (labelRenderer) labelRenderer.domElement.remove();
      renderer = labelRenderer = null;
      inited = false;
    }

    return state;
  }
}

// 行为核销（对照 templates/workbench.html initAssembly）：懒加载 clientWidth 闸 / Y-up 矫正 rotation.set(0,π,π/2)
// / 归一化缩放居中 / 材质按件克隆 / explode extras 爆炸 / CSS2D 标注（>30% 显隐、module 色号、label 截 '(' 前）
// / 透视 isGhost=M6+Base / 选中高亮 0x17a08c+emissive 0x0b6e63·1.5 / dimmed 0.07 ghost 0.15 depthWrite
// / 零件列表模块分组 / BOM 卡三态 badge / raycast 5px 拖拽阈 / __asmReset → reset() / 形态切换懒加载+离场重置。
