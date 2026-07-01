# 水下后处理 — 深度缓冲 + Beer-Lambert 体积吸收

> 核心技术源自 FFTOCEAN 的水下 EffectComposer pass。适配到 healing-space：**不依赖 FFT、不依赖 WebGL2、不依赖 GPU compute——只用 Three.js 的 EffectComposer + depthBuffer + 一个自定义 ShaderPass。**
>
> 设计哲学：**水下不是一个"滤镜"——是水体对光的物理吸收（Beer-Lambert 定律）。** 水越深/越浑浊 → 光衰减越快。从水面下潜的过渡不是切换场景——是同一个 scene 的 depth 驱动的连续的渐变。
>
> **加载时机**：STEP 5 执行时必读。当决策树判定隐喻含"水下/潜水/海底/深海/沉入水中/珊瑚礁"时。
>
> **触发条件**：用户描述含 水下/潜水/海底/深海/珊瑚礁/浮潜/沉入水中/海洋深处/水底。

---

## 一、边界规则

| 条件 | 行为 |
|------|------|
| 场景含实体 geometry（海床/礁石/地形） | ✅ 正常使用 depth 模式 |
| 场景全是 Points（粒子海底） | ⚠️ 降级：用 camera Y 高度代替 depth |
| 场景无水面（纯水下视角） | ✅ 正常使用——waterLevel 设为高于相机即可 |
| 移动端 | ⚠️ 降级：跳过 depth read，用 camera Y + 简化混合 |
| 用户无水下描述 | ❌ 不加载此 reference |

**核心约束**：depth 模式依赖场景中存在写深度缓冲的 geometry。`THREE.Points` 不写深度——如果海底是粒子场，`readDepth(uv)` 返回 1.0（无穷远），Beer-Lambert 会把整帧染成 fogColor。必须在加载前检查场景组成。

---

## 二、EffectComposer + depthBuffer 管线

### 2.1 依赖

```javascript
// Three.js 标准模块（无需额外安装）
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }    from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass }    from 'three/addons/postprocessing/ShaderPass.js';
```

WebGL1 兼容。不需要 `EXT_color_buffer_float` 或 `WEBGL_multi_draw`。

### 2.2 管线组装

```javascript
// 创建 EffectComposer — 关键：depthBuffer: true
const composer = new EffectComposer(renderer);
composer.renderToScreen = false; // 用户手动控制

// RenderPass — 先渲场景（带上 depth）
const renderPass = new RenderPass(scene, camera);
composer.addPass(renderPass);

// UnderwaterPass — 后处理：读 depth → Beer-Lambert
const underwaterPass = new ShaderPass(UnderwaterShader);
underwaterPass.renderToScreen = true;
composer.addPass(underwaterPass);

// 每帧
function animate() {
  // 更新 uniform
  underwaterPass.uniforms['uCameraPos'].value.copy(camera.position);
  underwaterPass.uniforms['uTime'].value = performance.now() * 0.001;

  composer.render();
}
```

### 2.3 水面高度判断

```javascript
// 简化判断：不读 FFT 纹理——用场景预设的 waterLevel
// ocean-waves.md 提供的 sea level（世界空间 Y 坐标）
const WATER_LEVEL = 0.0; // 或从 ocean material 读取

function isUnderwater(camera) {
  return camera.position.y < WATER_LEVEL;
}
```

**为什么不用 FFTOCEAN 的 displacementY 纹理检测**：FFTOCEAN 的 `waveHeightAtCamera` 依赖 FFT displacement 纹理——Gerstner 场景没有这张纹理。用固定 waterLevel 更简单、更可靠。如果需要波浪高度影响水面判断（如相机在波谷处），可以用 Gerstner 波的 JS 端计算——但不必要，因为水下的 fog 过渡本身有平滑区间。

---

## 三、Underwater Fragment Shader

### 3.1 核心公式

```
Beer-Lambert 吸收定律：
  I(d) = I₀ · e^(-d / σ)

其中：
  d  = 光线在水下经过的距离（米）→ 由 depth buffer 重建
  σ  = waterClarity（衰减系数）——值越大水越清，衰减越慢
  
fogFactor = 1 - e^(-d / waterClarity)
最终颜色 = mix(sceneColor, fogColor, fogFactor)
```

### 3.2 完整 Fragment Shader

```glsl
// === underwater.frag — Beer-Lambert 水下吸收 ===
uniform sampler2D tDiffuse;     // 场景渲染结果
uniform sampler2D tDepth;       // 深度缓冲（EffectComposer 自动提供）
uniform float     uCameraNear;
uniform float     uCameraFar;
uniform vec3      uCameraPos;
uniform vec3      uFogColor;     // 水体颜色——从 ocean material 的 uDeepColor 继承
uniform float     uWaterClarity; // 衰减系数（30–100），calm 映射
uniform float     uWaterLevel;   // 水面世界空间 Y 坐标
uniform float     uTime;

varying vec2 vUv;

// 标准 depth → viewZ 重建（Three.js perspectiveDepthToViewZ 等价）
float readDepth(sampler2D depthSampler, vec2 coord) {
  float depth = texture2D(depthSampler, coord).r;
  // perspectiveDepthToViewZ
  float viewZ = perspectiveDepthToViewZ(depth, uCameraNear, uCameraFar);
  return viewZ;
}

float perspectiveDepthToViewZ(float depth, float near, float far) {
  // 标准公式：viewZ = (near * far) / (far - depth * (far - near))
  return (near * far) / (far - depth * (far - near));
}

void main() {
  vec4 sceneColor = texture2D(tDiffuse, vUv);

  // 1. 判断相机是否在水下
  // cameraY < waterLevel → 水下
  float isUnderwater = step(uCameraPos.y, uWaterLevel);

  // 2. 过渡平滑——相机接近水面时，fog 逐渐加强
  // transitionZone: 相机在 waterLevel ± 5m 范围内 → 过渡
  float proximityToSurface = 1.0 - smoothstep(uWaterLevel - 5.0, uWaterLevel + 5.0, uCameraPos.y);
  // proximityToSurface = 0（远高于水面）→ 1（远低于水面）

  // 3. 读深度并重建 viewZ
  float rawDepth = texture2D(tDepth, vUv).r;

  float viewZ;
  // 天空/无穷远 → 给一个巨大的值 → fog 完全覆盖
  if (rawDepth >= 0.9999) {
    viewZ = 10000.0;
  } else {
    viewZ = perspectiveDepthToViewZ(rawDepth, uCameraNear, uCameraFar);
  }

  // 4. Beer-Lambert 吸收
  // fogFactor: 0 = 无 fog（浅水/近距离）→ 1 = 完全 fog（深水/远距离）
  float fogFactor = 1.0 - exp(-viewZ / uWaterClarity);
  fogFactor = clamp(fogFactor, 0.0, 1.0);

  // 5. 组合：只在相机在水下或接近水面时应用
  float finalFog = fogFactor * proximityToSurface;

  // 6. 颜色输出
  vec3 color = mix(sceneColor.rgb, uFogColor, finalFog);
  gl_FragColor = vec4(color, sceneColor.a);
}
```

### 3.3 JS 端 Shader 定义

```javascript
const UnderwaterShader = {
  uniforms: {
    tDiffuse:       { value: null },       // EffectComposer 自动注入
    tDepth:         { value: null },       // EffectComposer 自动注入
    uCameraNear:    { value: 0.1 },
    uCameraFar:     { value: 4000.0 },
    uCameraPos:     { value: new THREE.Vector3(0, 40, 200) },
    uFogColor:      { value: new THREE.Color('#002b4f') }, // 深蓝——从 uDeepColor 继承
    uWaterClarity:  { value: 60.0 },
    uWaterLevel:    { value: 0.0 },
    uTime:          { value: 0.0 },
  },

  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,

  fragmentShader: `/* 上述 fragment shader 代码 */`,
};
```

---

## 四、calm 参数映射

```javascript
// calm 总线——水下参数映射
function applyUnderwaterCalmState(calm, underwaterPass) {
  const c  = calm;
  const ts = c * c * (3 - 2 * c);  // smoothstep

  const u = underwaterPass.uniforms;

  // waterClarity：浑浊(风暴) → 清澈(治愈)
  // 30 = 能见度极低（浓雾般）→ 120 = 清澈如无物
  u.uWaterClarity.value = 30.0 + 90.0 * ts;

  // fogColor：暗灰蓝(压抑) → 更浅更暖的蓝(治愈)
  // 压抑态 = 深海恐惧感（深蓝几乎黑）
  // 治愈态 = 阳光透入浅滩的温暖感（浅蓝绿）
  u.uFogColor.value.setRGB(
    0.01 + 0.08 * ts,   // R: 0.01→0.09
    0.02 + 0.25 * ts,   // G: 0.02→0.27
    0.10 + 0.40 * ts    // B: 0.10→0.50
  );
}
```

**映射设计原理**：
- 焦虑时水下浑浊如浓雾——看不见远方 → "我不知道前面有什么"（深海恐惧）
- 平静时水下清澈通透——光线穿透水层照亮海底 → "我能看清一切了"（安全感的视觉等价）
- 颜色的回暖：压抑态是冷得接近黑的蓝（#001a33 左右），治愈态是温暖清透的蓝绿

---

## 五、与 ocean-waves.md 的协作

当场景同时含水面和水下时，两个 reference 必须协调：

### 5.1 颜色一致

```
水面 uDeepColor ←──→ 水下 uFogColor
      必须用同一组 RGB
```

```javascript
// 协调代码
const deepColor = new THREE.Color('#002b4f');
oceanMat.uniforms.uDeepColor.value.copy(deepColor);
underwaterPass.uniforms.uFogColor.value.copy(deepColor);
```

### 5.2 水面高度一致

```javascript
// 从 ocean material 读取或从场景配置传入
const waterLevel = 0.0;
underwaterPass.uniforms.uWaterLevel.value = waterLevel;
// 水面的 mesh.position.y 也应 = waterLevel
```

### 5.3 绘制顺序

```
1. Sky / Atmosphere（最底层）
2. SeaFloor geometry（海底地形——写 depth buffer）
3. Ocean surface mesh（Gerstner 波——水面）
4. EffectComposer:
   a. RenderPass → 全场景到 tDiffuse + tDepth
   b. UnderwaterPass → 读 tDepth → Beer-Lambert → 输出
```

SeaFloor 必须在 RenderPass 中——否则没有 depth 数据来重建 viewZ。

---

## 六、移动端降级

移动端读 depth texture 可能慢（取决于 GPU——A14+ 可以，低端 Android 不行）。

```javascript
const isMobile = /Mobile|Android|iPhone/.test(navigator.userAgent);
const canReadDepth = !isMobile || renderer.capabilities.isWebGL2;
// 保守策略：移动端一律降级

if (!canReadDepth) {
  // 降级模式：用 camera Y 高度代替 depth
  // fogFactor 不再基于逐像素 depth——而是基于整帧的单值
  // 效果差但 frame rate 更重要

  // 简化 fragment: 去掉 depth read，用固定 viewZ
  // fogFactor = 1.0 - exp(-CAMERA_HEIGHT_BELOW_SURFACE / uWaterClarity);

  // JS 端每帧计算
  const depthBelowSurface = Math.max(0, WATER_LEVEL - camera.position.y);
  const fogFactor = 1.0 - Math.exp(-depthBelowSurface / clarity);
  // 作为 uniform 传入 → 全屏统一 fog
  underwaterPass.uniforms.uFixedFog.value = fogFactor;
}
```

降级后效果：全屏均匀雾化（没有"远处比近处更雾"的深度感），但 frame rate 有保障。

---

## 七、反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | 粒子海底 | **致命** | 场景全是 Points → depth 全是 1.0 → 全屏 fogColor | 加入至少一个海底 PlaneGeometry 或 BoxGeometry——哪怕只有一个低面数平面也足够提供 depth |
| 2 | 忘记继承 fogColor | **致命** | 水面深蓝 + 水下雾绿 = 下潜瞬间颜色突变 | `uFogColor ← ocean.uDeepColor` 同源取值 |
| 3 | waterClarity 过低(< 15) | 警告 | 水下能见度 < 3 米——什么都看不见 | clarity 不低于 30。情绪最压抑时用 30（模糊但至少可见），治愈时用 100+ |
| 4 | 移动端硬跑 depth read | 警告 | 低端 Android 帧率掉到 < 20 | 移动端检测 → 降级到全屏统一 fog |
| 5 | waterLevel 和 ocean mesh Y 不一致 | 警告 | 水面视觉高度 ≠ 水下判断高度 → 下潜时 fog 在错误高度激活 | 用一个常量 `WATER_LEVEL`，ocean mesh 和 underwater pass 共用 |
| 6 | 未用滞后检测（与 Gerstner 波同场景时） | 警告 | Gerstner 顶点位移导致瞬时水面 Y 振荡 → 浪峰过境时误切水上/水下 → 画面闪烁 | 使用平均水面 Y + 滞后阈值（见 `ocean-waves.md §9.1`） |

---

## 八、自检清单

- [ ] 场景中存在写 depth 的实体 geometry（不是纯 Points）？
- [ ] `uFogColor` 和 ocean `uDeepColor` 来自同一个 `THREE.Color` 对象？
- [ ] `waterLevel` 与 ocean mesh.position.y 一致？
- [ ] 移动端已降级（跳过 depth read → 全屏统一 fog）？
- [ ] waterClarity ≥ 30（即使在最压抑状态）？
- [ ] EffectComposer 的 `depthBuffer: true` 已设置？
- [ ] calm 映射了 waterClarity 和 fogColor？
- [ ] 过渡区（waterLevel ± 5m）的 smoothstep 无跳变？
- [ ] 如果同场景有 Gerstner 水面 → 检测使用了平均水面 Y + 滞后阈值（非瞬时水面 Y），无闪烁？
