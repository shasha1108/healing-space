# GPU Fluid Simulation — FBO Ping-Pong 流体模拟武器库

本文件是 GPU 帧缓冲（FBO）流体模拟的真实可复用代码。**照着改，不要从零发明。**

核心思想：用两个 WebGLRenderTarget 交替作为"上一帧状态"和"当前帧输出"，在 fragment shader 中完成流体物理（漂移、画笔擦除、密度衰减）。

## 目录

- [一、FBO 基础架构](#一fbo-基础架构)
- [二、模拟 Shader（流体物理）](#二模拟-shader流体物理)
- [三、渲染 Shader（读取流体状态画到屏幕）](#三渲染-shader读取流体状态画到屏幕)
- [四、line 距离函数（平滑笔触）](#四line-距离函数平滑笔触)
- [五、FBO 预填充技巧](#五fbo-预填充技巧)
- [六、性能：HalfFloatType](#六性能halffloattype)
- [七、完整主循环集成](#七完整主循环集成)

---

## 一、FBO 基础架构

```javascript
const FBO_SIZE = 1024; // 1024×1024 分辨率，平衡质量与性能

const fboConfig = {
  format: THREE.RGBAFormat,
  type: THREE.HalfFloatType,        // 半精度浮点——省显存，精度足够
  minFilter: THREE.LinearFilter,
  magFilter: THREE.LinearFilter,
};

const rtA = new THREE.WebGLRenderTarget(FBO_SIZE, FBO_SIZE, fboConfig);
const rtB = new THREE.WebGLRenderTarget(FBO_SIZE, FBO_SIZE, fboConfig);

// 双场景：一个跑模拟（正交相机），一个跑最终渲染（可选——简单场景可直接一个）
const simScene = new THREE.Scene();
const simCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1);

// 全屏四边形——模拟 Shader 跑在它上面
const simGeo = new THREE.PlaneGeometry(2, 2);
const simMat = new THREE.ShaderMaterial({
  uniforms: {
    tDiffuse: { value: null },    // 上一帧的流体状态纹理
    uMouse: { value: new THREE.Vector2(-999, -999) },
    uPrevMouse: { value: new THREE.Vector2(-999, -999) },
    uAspect: { value: 1.0 },
    uIsDrawing: { value: 0 },
    uTime: { value: 0 },
  },
  vertexShader: document.getElementById('ortho-vs').textContent,
  fragmentShader: document.getElementById('sim-fs').textContent,
});
simScene.add(new THREE.Mesh(simGeo, simMat));

// 预填充：R 通道 = 1.0（全雾/全墨水状态）
renderer.setRenderTarget(rtA);
renderer.setClearColor(new THREE.Color(1.0, 0.0, 0.0), 1.0);
renderer.clear();
renderer.setRenderTarget(null);
renderer.setClearColor(new THREE.Color(0, 0, 0), 1.0);

// 每帧交换
function fluidStep() {
  simMat.uniforms.tDiffuse.value = rtA.texture;
  renderer.setRenderTarget(rtB);
  renderer.render(simScene, simCamera);
  // swap
  const tmp = rtA; rtA = rtB; rtB = tmp;
}
```

> `renderer.setClearColor(1.0, 0, 0, 1.0)` 把 R 通道预填为 1.0 是关键——代表初始状态（全雾/全墨水）。如果做"水迹擦除"类效果，R 通道代表雾浓度；做"墨水滴入"类效果，R 通道代表纸的空白度。

---

## 二、模拟 Shader（流体物理）

以下是最核心的流体模拟 fragment shader。它读取上一帧状态，施加漂移（noise swirl）、画笔擦除、缓慢恢复：

```glsl
// id="ortho-vs" — 全屏四边形顶点 shader
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position, 1.0); }

// id="sim-fs" — 流体物理 fragment shader
uniform sampler2D tDiffuse;
uniform vec2 uMouse;
uniform vec2 uPrevMouse;
uniform float uAspect;
uniform float uIsDrawing;
uniform float uTime;
varying vec2 vUv;

// -- 3D Simplex noise（约 40 行，见 shader-patterns.md §GLSL Simplex） --
// float snoise(vec3 v) { ... }

float line(vec2 p, vec2 a, vec2 b, float r) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return smoothstep(r, r * 0.5, length(pa - ba * h));
}

void main() {
    vec2 uv = vUv;
    vec2 p = uv; p.x *= uAspect;
    vec2 m = uMouse; m.x *= uAspect;
    vec2 pm = uPrevMouse; pm.x *= uAspect;

    // 读取上一帧状态
    vec4 state = texture2D(tDiffuse, uv);
    float density = state.r;  // R: 雾/墨浓度 (1=满, 0=被擦除/被水冲刷)
    float distX   = state.g;  // G: 扭曲向量 X
    float distY   = state.b;  // B: 扭曲向量 Y

    // 1. 漂移：用 snoise 生成 swirl 偏移，让流体自己动
    float noise = snoise(vec3(uv * 3.0, uTime * 0.15));
    vec2 swirl = vec2(noise * 0.003, snoise(vec3(uv * 3.0 + 1.0, uTime * 0.15)) * 0.003);
    float driftedDensity = texture2D(tDiffuse, uv - swirl).r;

    // 2. 画笔擦除（将手指划过处设为低密度）
    float brush = line(p, pm, m, 0.08) * uIsDrawing;

    // 3. 密度更新：极慢恢复（治愈感——不疾不徐）
    float newDensity = mix(driftedDensity, 1.0, 0.005); // 0.005 = 缓慢恢复
    newDensity -= brush * 0.8;
    newDensity = clamp(newDensity, 0.0, 1.0);

    // 4. 扭曲累积（手指推动流体的方向，存入 GB 通道供渲染 shader 使用）
    vec2 dir = normalize(p - m + 0.001);
    float newDistX = distX + dir.x * brush * 0.5;
    float newDistY = distY + dir.y * brush * 0.5;
    // 扭曲自身也缓慢衰减
    newDistX *= 0.98;
    newDistY *= 0.98;

    gl_FragColor = vec4(newDensity, newDistX, newDistY, 1.0);
}
```

> **关键调参**：`mix(drifted, 1.0, 0.005)` 的 0.005 是"恢复速度"——越小越慢、越治愈。`brush * 0.8` 的 0.8 是"擦除力度"。`swirl` 的 0.003 是"流体自发性"——太大像洗衣机、太小像死水。

---

## 三、渲染 Shader（读取流体状态画到屏幕）

FBO 跑完模拟后，需要一个渲染 shader 把 `rtA.texture` 画到 canvas。以下是一个构建"雾中深渊"的示例：

```glsl
uniform sampler2D tDiffuse;
uniform float uTime;
uniform vec2 uResolution;
varying vec2 vUv;

void main() {
    vec2 uv = vUv;
    vec4 state = texture2D(tDiffuse, uv);
    float density = state.r;   // 雾浓度
    float distX = state.g;
    float distY = state.b;

    // 构建色调：深渊暗蓝 → 冰壁青白 → 暖色微光
    vec3 darkAbyss = vec3(0.02, 0.04, 0.08);
    vec3 iceWall   = vec3(0.15, 0.35, 0.55);
    vec3 amberGlow = vec3(0.5, 0.75, 0.95);

    // 隧道透视：离中心越远越暗
    float tunnel = pow(abs(uv.x - 0.5), 1.5) * 4.0;

    // 密度越低 = 被擦除 = 光透进来
    float openness = 1.0 - density;
    vec3 color = mix(darkAbyss, iceWall, openness * 0.7 + tunnel);
    color += amberGlow * openness * 0.3;

    // 扭曲边缘：给擦除区域加一点光晕
    float edge = length(vec2(distX, distY)) * 2.0;
    color += amberGlow * edge * 0.15;

    // 微弱的噪声纹理（打破塑料感）
    float grain = fract(sin(dot(uv, vec2(12.9898, 78.233))) * 43758.5453);
    color += grain * 0.015;

    gl_FragColor = vec4(color, 1.0);
}
```

---

## 四、line 距离函数（平滑笔触）

这是让手指划过产生连贯线条而非离散圆点的关键：

```glsl
float line(vec2 p, vec2 a, vec2 b, float r) {
    vec2 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return smoothstep(r, r * 0.5, length(pa - ba * h));
}
```

它计算像素到线段 `a→b` 的最短距离。`r` 是笔触半径，`smoothstep(r, r*0.5, ...)` 产生柔和边缘。

---

## 五、FBO 预填充技巧

模拟的初始状态不是"空白"——而是"全满"。比如雾镜效果的初始状态是"全部被雾覆盖"(R=1.0)，用户手指擦除后才露出后面的景象。

```javascript
renderer.setRenderTarget(rtA);
renderer.setClearColor(new THREE.Color(1.0, 0.0, 0.0), 1.0); // R=1.0
renderer.clear();
renderer.setRenderTarget(null);
```

如果初始状态需要"全空"(R=0.0)，把 `1.0` 改成 `0.0`，适用于"墨水扩散"效果。

---

## 六、性能：HalfFloatType

```javascript
type: THREE.HalfFloatType  // 而非 THREE.FloatType
```

HalfFloatType 用 16 位浮点存储每个通道，精度足够（65536 级），但显存占用只有 FloatType（32位）的一半。1024×1024 RGBA 纹理：FloatType = 16MB，HalfFloat = 8MB。

> 移动端必须用 HalfFloatType，否则 FBO 可能创建失败。

---

## 七、完整主循环集成

```javascript
// 同时有 3D 粒子场景 + FBO 流体背景时
renderer.autoClear = false;

function loop() {
  requestAnimationFrame(loop);

  // 第一步：跑 FBO 流体模拟
  simMat.uniforms.tDiffuse.value = rtA.texture;
  simMat.uniforms.uTime.value = performance.now() / 1000;
  renderer.setRenderTarget(rtB);
  renderer.render(simScene, simCamera);
  const tmp = rtA; rtA = rtB; rtB = tmp;
  renderer.setRenderTarget(null);

  // 第二步：渲染 3D 粒子场景到屏幕
  renderer.clear();
  renderer.render(scene, camera);
  // 注：如果只有 FBO 没有粒子，直接 renderer.render(renderScene, renderCamera)
}
```

> **`autoClear = false`** 是关键——否则 renderer 会自动清空上一步的内容。

---

## 速查：效果 → 调参

| 效果 | density 初始 | 恢复速度 | 擦除力度 | swirl 强度 |
|------|------------|---------|---------|-----------|
| 雾镜（擦除露光） | 1.0（全雾） | 0.005（极慢） | 0.8 | 0.003 |
| 水墨（手指画墨） | 0.0（空白） | 0.02（快） | -0.5（画笔加墨） | 0.01 |
| 水迹（重力垂流） | 0.0 | 0.001 | 1.0 | 0.0（关闭） |
| 星云（搅动） | 0.5 | 0.01 | 0.3 | 0.02 |

---

## 八、WebGPU Compute Shader 路径（百万级粒子）

当场景需要 **20 万+粒子的实时物理**（如"百万个释放的光尘"、"消散的星云覆盖屏幕"），FBO 已不够用，需要 WebGPU Compute Shader。

> **选择标准**：< 20 万粒子 → FBO（本文件 §一~§七，WebGL2 全平台）；20 万~1M 粒子 → WebGPU Compute（本节）。

### WebGPU Compute 骨架（TSL 写法）

```javascript
import WebGPURenderer from 'three/addons/renderers/WebGPURenderer.js';
import { StorageBufferAttribute, Fn, instanceIndex, timerLocal,
         mx_noise_float, vec3, float, cos, sin } from 'three/tsl';

const COUNT = 1_000_000;

// GPU 显存中的粒子缓冲（无需 CPU 数组）
const positionBuf = new StorageBufferAttribute(COUNT, 4);
const velocityBuf = new StorageBufferAttribute(COUNT, 4);

// Compute Shader：Curl Noise 驱动（每帧 GPU 全并行）
const computeParticles = Fn(() => {
    const pos = positionBuf.element(instanceIndex);
    const vel = velocityBuf.element(instanceIndex);
    const t   = timerLocal();

    const n     = mx_noise_float(pos.xyz.mul(0.015).add(t.mul(0.04)));
    const angle = n.mul(Math.PI * 2.0);
    const force = vec3(cos(angle), sin(angle), n.mul(0.3)).mul(0.0015);

    vel.xyz = vel.xyz.mul(0.97).add(force);   // 阻尼 + 力
    pos.xyz = pos.xyz.add(vel.xyz);           // 积分位置
})().compute(COUNT);

// 主循环（WebGPU 专属 API）
async function loop() {
    requestAnimationFrame(loop);
    await renderer.computeAsync(computeParticles);  // GPU 端计算
    renderer.render(scene, camera);
}
```

### 降级策略

```javascript
const renderer = new WebGPURenderer({ antialias: true });
await renderer.init();

if (renderer.backend.isWebGPUBackend) {
    // WebGPU：百万粒子 Compute
    initComputeParticles(1_000_000);
} else {
    // WebGL2 降级：FBO 方案（本文件 §一）
    initFBOParticles(80_000);
}
```

### FBO vs Compute 对比速查

| 维度 | FBO（§一~§七） | WebGPU Compute（本节） |
|------|--------------|---------------------|
| 粒子上限 | ~200K | ~5M |
| 浏览器支持 | 所有现代浏览器 | Chrome/Edge（WebGPU） |
| 移动端 | ✅（HalfFloat 优化） | ❌（2025 年底前不稳定）|
| 适合隐喻 | 流体/墨水/雾 | 大气/星云/细沙/宇宙 |
| 实现复杂度 | 中等 | 较高（需 TSL 语法）|

> 完整实现（含 TSL NodeMaterial 自定义着色、Ping-Pong 双 buffer 反应扩散、instancedArray 渲染）见 **tsl-webgpu.md**。
