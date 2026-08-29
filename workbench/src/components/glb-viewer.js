// glb-viewer.js —— 纯 GLB 查看器封装（懒初始化单例 + dispose）
// 迁自 templates/workbench.html 的 initViewer()：首次可见时才建 scene（元素 hidden 时 clientWidth=0）。
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const instances = new WeakMap();

export function createGlbViewer(el, { glbUrl, correctYUp = false } = {}) {
  const existing = instances.get(el);
  if (existing) return existing;

  let renderer = null, raf = 0, disposed = false;
  const state = {
    el,
    get inited() { return !!renderer; },
    init,
    dispose,
  };
  instances.set(el, state);
  return state;

  function init() {
    if (renderer || disposed) return state;
    if (el.clientWidth === 0) return state; // 不可见，等入场后再调 init()
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf3f3f1);
    const camera = new THREE.PerspectiveCamera(40, el.clientWidth / el.clientHeight, 0.01, 50);
    camera.position.set(1.05, 0.85, 1.45);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xdfe3e8, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 1.8);
    key.position.set(2, 3, 2);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.7);
    fill.position.set(-1.5, 0.5, -1);
    scene.add(fill);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    new GLTFLoader().load(glbUrl || el.dataset.glb, gltf => {
      if (disposed) return;
      const model = gltf.scene;
      // 坐标矫正（可选）：Blender X=高/Z=宽/Y=前 → glTF 后先绕 Z 转 90° 让高朝上，再绕 Y 转 180° 让前脸朝相机
      if (correctYUp) model.rotation.set(0, Math.PI, Math.PI / 2);
      const box = new THREE.Box3().setFromObject(model);
      const size = box.getSize(new THREE.Vector3());
      const center = box.getCenter(new THREE.Vector3());
      const k = 1.0 / Math.max(size.x, size.y, size.z);
      model.scale.setScalar(k);
      model.position.sub(center.multiplyScalar(k));
      scene.add(model);
    }, undefined, err => {
      el.innerHTML = '<div class="ph">GLB 加载失败：' + err + '</div>';
    });
    (function animate() {
      if (disposed) return;
      raf = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    })();
    return state;
  }

  function dispose() {
    disposed = true;
    cancelAnimationFrame(raf);
    if (renderer) {
      renderer.dispose();
      renderer.domElement.remove();
      renderer = null;
    }
    instances.delete(el);
  }
}
