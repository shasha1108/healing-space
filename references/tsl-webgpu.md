# TSL / WebGPU — Three.js 着色语言与 GPU Compute 武器库

本文件是 Three.js TSL（Three.js Shading Language）和 WebGPU Compute Shader 的可复用代码。
**TSL 让你用 JS 写着色器——自动编译为 WGSL（WebGPU）或 GLSL（WebGL 2）**，是 r168+ 的新主流写法。

核心价值：WebGPU Compute Shader 让 GPU 直接做物理计算，100 万粒子 @60fps 可行。

## 目录

- [一、WebGPURenderer 初始化 + WebGL2 降级](#一webgpurenderer-初始化--webgl2-降级)
- [二、TSL NodeMaterial 基础写法](#二tsl-nodematerial-基础写法)
- [三、TSL 自定义节点函数](#三tsl-自定义节点函数)
- [四、GPGPU Compute Shader 粒子模板](#四gpgpu-compute-shader-粒子模板)
- [五、Ping-Pong Buffer 双 Texture 架构](#五ping-pong-buffer-双-texture-架构)
- [六、instancedArray() 存储缓冲渲染](#六instancedarray-存储缓冲渲染)
- [七、降级检测 + 渐进增强](#七降级检测--渐进增强)
- [速查：TSL 常用节点](#速查tsl-常用节点)

---

## 一、WebGPURenderer 初始化 + WebGL2 降级

```javascript
import * as THREE from 'three';
import WebGPURenderer from 'three/addons/renderers/WebGPURenderer.js';

// 优先 WebGPU，失败自动降 WebGL 2
const renderer = new WebGPURenderer({ antialias: true });
await renderer.init();   // 必须 await！WebGPU 初始化是异步的
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

const isWebGPU = renderer.backend.isWebGPUBackend;
console.log(isWebGPU ? 'WebGPU active' : 'WebGL2 fallback');
```

**CDN 用法（无构建工具，单文件 HTML）**：

```html
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.168/build/three.webgpu.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.168/examples/jsm/",
    "three/tsl": "https://cdn.jsdelivr.net/npm/three@0.168/build/three.tsl.js"
  }
}
</script>
<script type="module">
import * as THREE from 'three';
import WebGPURenderer from 'three/addons/renderers/WebGPURenderer.js';
// ...
</script>
```

---

## 二、TSL NodeMaterial 基础写法

TSL 用函数调用替代 GLSL 字符串——写在 JS 里，无需 `<script type="x-shader">` 标签。

```javascript
import {
    MeshStandardNodeMaterial, color, vec3, float, sin, cos,
    positionLocal, normalLocal, timerLocal, mx_noise_float
} from 'three/tsl';

const mat = new MeshStandardNodeMaterial();

// colorNode 替代 fragment shader 颜色计算
const time = timerLocal();
const noiseVal = mx_noise_float(positionLocal.mul(0.5).add(time.mul(0.3)));
mat.colorNode = vec3(
    noiseVal.mul(0.5).add(0.3),   // R
    noiseVal.mul(0.3).add(0.2),   // G
    float(0.8)                    // B 固定
);

// positionNode 替代 vertex shader 位移
const wave = sin(positionLocal.x.mul(3.0).add(time.mul(2.0))).mul(0.1);
mat.positionNode = positionLocal.add(normalLocal.mul(wave));
```

---

## 三、TSL 自定义节点函数

`Fn()` 包裹任意逻辑，产生可复用的 TSL 节点：

```javascript
import { Fn, vec3, float, sin, cos, mx_noise_float, timerLocal } from 'three/tsl';

// Curl Noise（TSL 版）
const curlNoise = Fn(([p]) => {
    const e  = float(0.1);
    const n1 = mx_noise_float(p.add(vec3(e, 0, 0)));
    const n2 = mx_noise_float(p.sub(vec3(e, 0, 0)));
    const n3 = mx_noise_float(p.add(vec3(0, e, 0)));
    const n4 = mx_noise_float(p.sub(vec3(0, e, 0)));
    const n5 = mx_noise_float(p.add(vec3(0, 0, e)));
    const n6 = mx_noise_float(p.sub(vec3(0, 0, e)));
    return vec3(
        n3.sub(n4).sub(n5).add(n6),
        n5.sub(n6).sub(n1).add(n2),
        n1.sub(n2).sub(n3).add(n4)
    ).div(e.mul(2.0));
});

// 使用：mat.positionNode = positionLocal.add(curlNoise(positionLocal.mul(0.02)).mul(5.0))
```

---

## 四、GPGPU Compute Shader 粒子模板

```javascript
import { StorageBufferAttribute, WebGPURenderer, instanceIndex,
         Fn, vec3, float, cos, sin, timerLocal, mx_noise_float } from 'three/tsl';
import * as THREE from 'three';

const COUNT = 1_000_000;

// 在 GPU 显存中分配粒子状态 buffer（位置 + 速度）
const positionBuf = new StorageBufferAttribute(COUNT, 4);  // xyzw
const velocityBuf = new StorageBufferAttribute(COUNT, 4);

// 初始化随机位置（主线程，运行一次）
const posArr = positionBuf.array;
for (let i = 0; i < COUNT * 4; i += 4) {
    posArr[i]   = (Math.random() - 0.5) * 100;  // x
    posArr[i+1] = (Math.random() - 0.5) * 100;  // y
    posArr[i+2] = (Math.random() - 0.5) * 100;  // z
    posArr[i+3] = 1.0;
}

// Compute Shader：Curl Noise 驱动粒子（GPU 全并行）
const computeParticles = Fn(() => {
    const pos  = positionBuf.element(instanceIndex);
    const vel  = velocityBuf.element(instanceIndex);
    const t    = timerLocal();

    const noiseF = mx_noise_float(pos.xyz.mul(0.015).add(t.mul(0.04)));
    const angle  = noiseF.mul(Math.PI * 2.0);
    const force  = vec3(cos(angle), sin(angle), noiseF.mul(0.3)).mul(0.0015);

    vel.xyz = vel.xyz.mul(0.97).add(force);   // 阻尼 + 力
    pos.xyz = pos.xyz.add(vel.xyz);           // 积分
})().compute(COUNT);

// 渲染：InstancedMesh 从 buffer 读位置
const geo  = new THREE.SphereGeometry(0.08, 4, 4);
const mat  = new THREE.MeshBasicMaterial({ color: 0x6699ff });
const mesh = new THREE.InstancedMesh(geo, mat, COUNT);
scene.add(mesh);

// 主循环（WebGPU 专有）
async function animate() {
    requestAnimationFrame(animate);
    await renderer.computeAsync(computeParticles);
    renderer.render(scene, camera);
}
animate();
```

> **注意**：`renderer.computeAsync()` 是 WebGPU 专有 API。WebGL2 降级时不可用，需回退到 FBO 方案（gpu-fluid.md §一）。

---

## 五、Ping-Pong Buffer 双 Texture 架构

两张 StorageTexture 交替读/写，避免同帧读写竞态——适合反应扩散、流体模拟等双缓冲算法：

```javascript
import { StorageTexture, textureStore, textureLoad, vec4, vec2,
         instanceIndex, Fn, float } from 'three/tsl';

const W = 512, H = 512;

const texA = new StorageTexture(W, H);
const texB = new StorageTexture(W, H);
let readTex = texA, writeTex = texB;

// Compute：读 readTex，写 writeTex（Gray-Scott 简化示例）
const computeStep = Fn(() => {
    const x     = instanceIndex.mod(W);
    const y     = instanceIndex.div(W);
    const coord = vec2(x, y);

    const curr  = textureLoad(readTex, coord);
    const u = curr.r, v = curr.g;
    const F = float(0.035), k = float(0.065);

    const newU  = u.sub(u.mul(v).mul(v)).add(F.mul(float(1.0).sub(u)));
    const newV  = v.add(u.mul(v).mul(v)).sub(F.add(k).mul(v));

    textureStore(writeTex, coord, vec4(newU, newV, float(0), float(1)));
})().compute(W * H);

async function step() {
    await renderer.computeAsync(computeStep);
    [readTex, writeTex] = [writeTex, readTex];  // 每帧交换
}
```

> 完整的反应扩散 WebGL/WebGPU 实现见 `reaction-diffusion.md`。

---

## 六、instancedArray() 存储缓冲渲染

将 StorageBuffer 绑定到渲染管线，让每个实例读取 GPU 计算后的位置和颜色：

```javascript
import { instancedArray, instanceIndex, float, vec3 } from 'three/tsl';
import { MeshStandardNodeMaterial } from 'three/tsl';

const mat = new MeshStandardNodeMaterial();

// 每个实例读取自己的 positionBuf 行（xyz）
mat.positionNode = instancedArray(positionBuf, 3);

// 按粒子 ID 渐变颜色（无需 CPU 端写 color array）
const hue   = instanceIndex.toFloat().div(float(COUNT));
mat.colorNode = vec3(hue, float(0.6), hue.oneMinus());
```

---

## 七、降级检测 + 渐进增强

```javascript
async function initApp() {
    const renderer = new WebGPURenderer({ antialias: true });
    await renderer.init();

    const mode = renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2';
    const COUNT = mode === 'webgpu' ? 1_000_000 : 80_000;

    if (mode === 'webgpu') {
        initGPGPUParticles(renderer, COUNT);   // 本文件 §四
    } else {
        initFBOParticles(renderer, COUNT);     // gpu-fluid.md §一
    }

    return renderer;
}
```

> **疗愈类作品推荐策略**：默认走 FBO（WebGL2 全覆盖），WebGPU 作可选增强。FBO 流体已足够美——WebGPU 的核心优势是**量**（1M+ 粒子）和**算法复杂度**，不是必须的。

---

## 速查：TSL 常用节点

| TSL 节点 | 等价 GLSL | 用途 |
|---------|----------|------|
| `timerLocal()` | `uniform float uTime` | 自动递增时间 |
| `positionLocal` | `position`（顶点空间） | 顶点位置 |
| `normalLocal` | `normal` | 顶点法线 |
| `uv()` | `uv` | UV 坐标 |
| `mx_noise_float(p)` | `snoise(p)` | Perlin 噪声（标量） |
| `mx_noise_vec3(p)` | 3D 噪声向量 | Curl Noise 基础 |
| `instanceIndex` | `gl_InstanceID` | 实例 ID（Compute 用） |
| `smoothstep(a,b,x)` | `smoothstep` | 平滑阶跃 |
| `mix(a,b,t)` | `mix` | 插值 |
| `Fn(([args]) => {...})` | `float fn(...) {}` | 自定义节点函数 |
