# Shader Patterns — 发光粒子渲染武器库

本文件是写发光粒子 Shader 的真实可复用代码。**照着改，不要从零发明。**

所有 Shader 用 `THREE.ShaderMaterial` 挂在 `THREE.BufferGeometry` 上。粒子的位置更新在 JS 侧（CPU）做，shader 只负责"把它画得发光、柔和、有层次"。

---

## 一、核心数据布局（BufferGeometry 必备的 attribute）

JS 侧这样准备 geometry（以 15 万粒子为例）：

```javascript
const COUNT = navigator.userAgent.match(/Mobile/) ? 60000 : 150000;
const positions = new Float32Array(COUNT * 3);   // xyz
const colFrom   = new Float32Array(COUNT * 3);   // 躁动态 rgb（GPU 端混合用，见第六节）
const colTo     = new Float32Array(COUNT * 3);   // 治愈态 rgb
const sizes     = new Float32Array(COUNT);       // 每粒子基础大小

// ... 在 init 时填充 positions/colFrom/colTo/sizes ...

const geo = new THREE.BufferGeometry();
geo.setAttribute('position',   new THREE.BufferAttribute(positions, 3));
geo.setAttribute('aColorFrom', new THREE.BufferAttribute(colFrom, 3));
geo.setAttribute('aColorTo',   new THREE.BufferAttribute(colTo, 3));
geo.setAttribute('aSize',      new THREE.BufferAttribute(sizes, 1));
```

> ⚠️ **关键坑**：不要用 `color` / `uv` / `normal` 当 attribute 名，THREE 会内置冲突。统一用 `aColorFrom` / `aColorTo` / `aSize` 这种 `a` 前缀。
>
> **颜色用双 attribute（From/To）而非单 aColor**：这样色彩过渡能交给 GPU 的 `mix`（见第六节），省掉每帧 14 万次 CPU 循环。这是 archetype《释·茧》验证过的关键性能优化。

---

## 二、Vertex Shader（决定大小 + 透视 + GPU 端色彩混合）

> ⚠️ attribute 名必须与 JS 侧 `geo.setAttribute('aColorFrom',...)` 一致。统一使用 `aColorFrom`/`aColorTo`（双重色），GPU 端 `mix` 做过渡——这是整个 skill 的核心性能优化。

```glsl
// id="vertexShader"
attribute vec3  aColorFrom;   // 躁动态颜色
attribute vec3  aColorTo;     // 治愈态颜色
attribute float aSize;

uniform float uTime;
uniform float uPixelRatio;
uniform float uGlobalSize;
uniform float uTransition;    // 0=躁动, 1=治愈（驱动 GPU 端颜色混合）
uniform float uBreathe;       // 0~1 呼吸相位

varying vec3  vColor;
varying float vAlpha;

void main() {
    // GPU 端颜色混合（替代每帧 CPU 循环 14 万次改色）
    vColor = mix(aColorFrom, aColorTo, uTransition);

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

    float breatheBoost = mix(1.0, 1.3 + uBreathe * 1.2, uTransition);
    gl_PointSize = aSize * uGlobalSize * uPixelRatio * breatheBoost * (300.0 / -mvPosition.z);

    gl_Position = projectionMatrix * mvPosition;
    vAlpha = mix(0.45, 0.5 + uBreathe * 0.4, uTransition);
}
```

**要点**：
- `gl_PointSize` 必须乘 `uPixelRatio`，否则 Retina 屏粒子会糊成一坨。
- `300.0 / -mvPosition.z` 这个常数越小，整体粒子越大；按场景调。
- 想让粒子随时间呼吸，可加 `* (0.8 + 0.2 * sin(uTime * 2.0 + position.x))`。

---

## 三、Fragment Shader（决定形状 + 柔和发光边缘）

这是**最关键**的一块。粒子的"高级感"全靠这里。

```glsl
// id="fragmentShader"
precision highp float;

varying vec3  vColor;
varying float vAlpha;

void main() {
    // gl_PointCoord 是当前像素在点 sprite 内的坐标，范围 [0,1]，左下角 (0,0)
    // 转成以中心为原点、范围 [-1,1]
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float dist = length(uv);   // 到中心的距离，0=中心 1=边缘

    // 圆形 mask：边缘外完全透明
    if (dist > 1.0) discard;

    // 核心：柔和发光。用 dist 的幂次做衰减，幂越高边缘越锐利、中心越亮。
    // 经验值：1.5~2.0 偏柔光球；3.0~5.0 偏锐利星点。
    float glow = pow(1.0 - dist, 2.0);

    // 中心更亮的内核（让粒子有"核 + 光晕"的层次）
    float core = pow(1.0 - dist, 6.0);
    vec3 finalColor = vColor + core * 0.5;   // 内核叠加白光感

    gl_FragColor = vec4(finalColor, glow * vAlpha);
}
```

**调参指南**：
| 想要的效果 | 改哪里 |
|-----------|--------|
| 更柔的雾状光球 | `pow(1.0 - dist, 1.5)`，core 的幂降到 `4.0` |
| 锐利的星点 | `pow(1.0 - dist, 4.0)`，去掉 core |
| 中心发白的钻石感 | core 系数加到 `1.0` 以上，core 幂 `8.0` |
| 整体偏暖/偏冷 | `finalColor` 末尾加 `+ vec3(0.05, 0.02, 0.0)`（暖）或 `+ vec3(0.0, 0.03, 0.06)`（冷） |

---

## 四、ShaderMaterial 配置（加法混合是灵魂）

```javascript
const material = new THREE.ShaderMaterial({
    uniforms: {
        uTime:       { value: 0 },
        uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
        uGlobalSize: { value: 1.0 },
    },
    vertexShader:   document.getElementById('vertexShader').textContent,
    fragmentShader: document.getElementById('fragmentShader').textContent,
    transparent: true,
    depthWrite: false,        // 关键！否则粒子会互相遮挡出黑边
    depthTest:  false,        // 纯加法场景通常关掉
    blending:   THREE.AdditiveBlending,   // 加法混合 → 重叠处更亮，形成光团
});

const points = new THREE.Points(geo, material);
scene.add(points);
```

> **为什么 AdditiveBlending**：黑色背景上，多个半透明粒子叠加会自然产生"越聚越亮"的光团效果，这就是星云/萤火/能量球的核心质感。代价是亮处会发白，所以颜色饱和度要拉高一点。

---

## 五、动态更新粒子（每帧改 attribute）

交互或物理每帧改变粒子位置/颜色后，必须 `needsUpdate = true`：

```javascript
function updateParticles(dt) {
    const posArr   = geo.attributes.position.array;
    const colArr   = geo.attributes.aColor.array;
    const alphaArr = geo.attributes.aAlpha.array;

    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        // ... 这里跑物理方程，更新 posArr[i3], posArr[i3+1], posArr[i3+2] ...
        // ... 状态机驱动下，colArr 和 alphaArr 也会渐变 ...
    }

    geo.attributes.position.needsUpdate = true;
    geo.attributes.aColor.needsUpdate   = true;
    geo.attributes.aAlpha.needsUpdate   = true;
    material.uniforms.uTime.value      += dt;
}
```

> **性能提示**：15 万粒子 × 每帧循环，在移动端会卡。两个办法：(1) 移动端 COUNT 砍半；(2) 物理更新降频（每 2 帧更新一次位置，shader 里插值）。黄金范例用的是办法 (1)。

---

## 六、颜色渐变（GPU 端混合 —— 必须这样做）

情感弧线的"色彩过渡"是最高频的操作。**千万不要**在 CPU 侧每帧循环 14 万粒子改 color array——那是性能杀手，移动端直接卡。

正确做法（archetype《释·茧》验证）：每粒子存**两套颜色 attribute**（`aColorFrom` 躁动态 + `aColorTo` 治愈态），把全局过渡进度作为 uniform 传进 vertex shader，在 GPU 端 `mix`。每帧只需更新**一个 uniform**：

```javascript
// geometry 准备（一次性，init 时）
const colFrom = new Float32Array(COUNT * 3);   // 躁动态色
const colTo   = new Float32Array(COUNT * 3);   // 治愈态色
for (let i = 0; i < COUNT; i++) {
    const i3 = i * 3;
    // 分层上色（见下方要点），不是单一颜色
    colFrom[i3]=0.85; colFrom[i3+1]=0.18; colFrom[i3+2]=0.12;
    colTo[i3]=0.45;   colTo[i3+1]=0.7;    colTo[i3+2]=1.0;
}
geo.setAttribute('aColorFrom', new THREE.BufferAttribute(colFrom, 3));
geo.setAttribute('aColorTo',   new THREE.BufferAttribute(colTo, 3));

// Vertex Shader 里（一次性写好）：
//   uniform float uTransition;       // 0=躁动, 1=治愈
//   attribute vec3 aColorFrom;
//   attribute vec3 aColorTo;
//   varying vec3 vColor;
//   void main() {
//       vColor = mix(aColorFrom, aColorTo, uTransition);   // GPU 端混合
//       ...
//   }

// 主循环里每帧（只需一行！）：
material.uniforms.uTransition.value = smoothstepProgress;   // 完事
```

> 对比：CPU 方案每帧 14 万次循环写 array + needsUpdate 上传显存；GPU 方案每帧一次 uniform 赋值。性能差几个数量级，移动端尤其明显。

**分层上色要点**（archetype 两份作品都用）：不要让所有粒子同色。按随机概率分配 2~3 种色调，叠加 AdditiveBlending 后色彩层次丰富得多：

```javascript
for (let i = 0; i < COUNT; i++) {
    const i3 = i * 3;
    // 躁动态：30% 玫红 + 70% 暗红
    if (Math.random() < 0.3) {
        colFrom[i3]=0.9; colFrom[i3+1]=0.1; colFrom[i3+2]=0.4;
    } else {
        colFrom[i3]=0.85; colFrom[i3+1]=0.18; colFrom[i3+2]=0.12;
    }
    // 治愈态：30% 暖金 + 40% 暖白蓝 + 30% 近白
    const r = Math.random();
    if (r < 0.3)      { colTo[i3]=1.0; colTo[i3+1]=0.75; colTo[i3+2]=0.35; }
    else if (r < 0.7) { colTo[i3]=0.45; colTo[i3+1]=0.7; colTo[i3+2]=1.0; }
    else              { colTo[i3]=0.7; colTo[i3+1]=0.85; colTo[i3+2]=1.0; }
}
```

> 上一节"动态更新粒子"里如果有改 `aColor`/`aAlpha` 的循环，**删掉**——改用本节的 GPU 方案。位置 `position` 仍需 CPU 更新（物理在 CPU 跑），但颜色不需要。

---

## 七、CSS 噪点遮罩（增加物理质感，避免塑料感）

放进 `<head>` 的 `<style>`，单独一层叠在 canvas 上：

```css
.noise-overlay {
    position: fixed; inset: 0;
    pointer-events: none;        /* 关键：不挡交互 */
    z-index: 10;
    opacity: 0.04;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>");
    mix-blend-mode: overlay;
}
```

> 这是**唯一允许的内联"资源"**——它是一段 SVG data-URI，不是外部文件，符合零依赖约束。它给整个画面蒙上一层极细的胶片颗粒，瞬间提升质感。

---

## 速查：常见视觉效果的对应改法

| 想要 | 改哪里 |
|------|--------|
| 粒子整体变大/变小 | `uGlobalSize` uniform |
| 粒子呼吸闪烁 | vertex 里 `aSize *= (0.8 + 0.2*sin(uTime + aSize*10.0))` |
| 远处模糊近处清晰 | 已自带（透视），调 `300.0` 常数 |
| 中心发白的热核 | fragment 的 `core` 项系数调大 |
| 整体偏某色调 | fragment `finalColor` 末尾加偏置 vec3 |
| 鼠标处粒子变亮 | 传 `uMouse` uniform，fragment 里 `+ smoothstep(0.3, 0.0, distance(uMouse, uv))` |

---

## 八、GLSL 端 3D Simplex Noise + Curl Noise（替代 CPU curl）

把噪声计算从 CPU 移到 GPU——每帧只需更新 `uTime` uniform，不占用 JS 物理循环的三角函数预算。适用于 10 万+ 粒子。

### 3D Simplex Noise（完整实现，~60 行）

```glsl
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
        i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m*m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
}
```

### Curl Noise（从 Simplex 推导旋度）

```glsl
vec3 snoiseVec3(vec3 x) {
    return vec3(
        snoise(x),
        snoise(vec3(x.y + 31.7, x.z - 11.3, x.x + 15.9)),
        snoise(vec3(x.z - 63.1, x.x + 27.5, x.y - 9.4))
    );
}

vec3 curlNoise(vec3 p) {
    const float e = 0.1;
    vec3 dx = vec3(e, 0.0, 0.0);
    vec3 dy = vec3(0.0, e, 0.0);
    vec3 dz = vec3(0.0, 0.0, e);
    vec3 p_x0 = snoiseVec3(p - dx);
    vec3 p_x1 = snoiseVec3(p + dx);
    vec3 p_y0 = snoiseVec3(p - dy);
    vec3 p_y1 = snoiseVec3(p + dy);
    vec3 p_z0 = snoiseVec3(p - dz);
    vec3 p_z1 = snoiseVec3(p + dz);
    float x = p_y1.z - p_y0.z - p_z1.y + p_z0.y;
    float y = p_z1.x - p_z0.x - p_x1.z + p_x0.z;
    float z = p_x1.y - p_x0.y - p_y1.x + p_y0.x;
    return vec3(x, y, z) / (2.0 * e);
}
```

### 在 Vertex Shader 中使用（微积分循环）

```glsl
// ... snoise + curlNoise 定义在上方 ...
void main() {
    vec3 fluidPos = position;
    // 微积分：3 步 ≈ 隐式欧拉，产生流畅的烟雾/水墨运动
    for (int i = 0; i < 3; i++) {
        fluidPos += curlNoise(fluidPos * 0.015 + uTime * 0.08) * 1.5;
    }
    vec4 mvPosition = modelViewMatrix * vec4(fluidPos, 1.0);
    gl_PointSize = aSize * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
}
```

> **对比 CPU curl**：CPU 版每粒子 3 次 sin，14 万粒子 = 42 万次/帧 ≈ 32ms。GPU 版在 shader 中并行执行，主线程零成本。

---

## 九、双场景渲染（全屏 GLSL 背景 + 3D 粒子前景）

当需要一个动态的 GLSL 背景（水墨、流体、渐变）托底，上面再叠加 3D 粒子：

```javascript
// 背景场景（全屏正交）
const bgScene = new THREE.Scene();
const bgCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1);
const bgGeo = new THREE.PlaneGeometry(2, 2);
const bgMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uMouse: { value: new THREE.Vector2() } },
    vertexShader: '...',  // 正交全屏 vs
    fragmentShader: '...' // FBM + 域扭曲背景
});
bgScene.add(new THREE.Mesh(bgGeo, bgMat));

// 渲染顺序：先背景，后粒子
renderer.autoClear = false;
function loop() {
    renderer.clear();
    renderer.render(bgScene, bgCamera);   // 1. 画 GLSL 背景
    renderer.render(scene, camera);        // 2. 画 3D 粒子
    requestAnimationFrame(loop);
}
```

> **`autoClear = false`** 防止第二步清掉第一步画的背景。FBO 流体 + 3D 粒子组合场景也用同样的双场景模式（FBO 场景替代 bgScene）。

---

## 十、粒子生命周期（Alpha 循环）

让粒子有"诞生→发光→消逝"的周期，而不是永远存在：

```glsl
// JS 侧：给每个粒子一个随机生命偏移
attribute float aLifeOffset; // 0~1，init 时 Math.random()

// Vertex Shader：
float age = fract(uTime * 0.1 + aLifeOffset);  // 0→1 循环
float lifeAlpha = sin(age * 3.14159);           // 0→1→0 平滑
vAlpha = mix(lifeAlpha * 0.6, 0.9, uTransition);
```

> `fract(uTime * 0.1 + aLifeOffset)` 保证每个粒子的"钟"是错开的，整体呈现波光粼粼。

---

## 十一、HalfFloatType 渲染目标

FBO 或离屏渲染时使用半精度浮点纹理：

```javascript
const rt = new THREE.WebGLRenderTarget(W, H, {
    format: THREE.RGBAFormat,
    type: THREE.HalfFloatType,   // 关键！
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
});
```

> HalfFloatType = 16 位浮点，精度足够（65536 级），显存占用是 FloatType 的一半。移动端必须用，否则可能创建失败。

---

## 十二、体积氛围渲染（Volumetric Atmosphere）

空气不是透明的——它有厚度、温度和重量。以下技法让场景从"3D 渲染"变成"有空气感的空间"。

### FogExp2（指数雾）——最轻量的体积感

```javascript
// 暗色深渊场景
scene.fog = new THREE.FogExp2(0x000508, 0.002);
// 宣纸/山岚场景
scene.fog = new THREE.FogExp2(0xF2F1E6, 0.0015);
```

> `FogExp2` 比 `Fog` 更自然——远处物体以指数速率隐入雾中，符合真实大气衰减。`density` 0.001~0.003 是治愈系作品的舒适区间。**深色场景用 0.0008~0.002，浅色场景用 0.001~0.003。**

### 丁达尔光路（Tyndall Rays）——Fragment Shader 端

在屏幕空间的 fragment shader 中模拟体积光散射。核心思路：从光源位置向每个像素步进采样，累积"被照亮"的雾密度。

```glsl
// 伪丁达尔光路（后处理 pass）
uniform vec2 uLightPos;    // 光源在屏幕空间的位置 (0~1)
uniform float uIntensity;  // 光路强度
uniform sampler2D tDiffuse;

void main() {
    vec2 uv = vUv;
    vec2 delta = uv - uLightPos;
    float dist = length(delta);
    vec2 dir = delta / max(dist, 0.001);

    float rays = 0.0;
    float stepSize = dist / 16.0;  // 16 步采样

    for (int i = 0; i < 16; i++) {
        vec2 sampleUV = uv - dir * float(i) * stepSize;
        float sampleFog = texture2D(tDiffuse, sampleUV).r; // 读雾密度
        rays += sampleFog * 0.06;
    }
    rays *= uIntensity * (1.0 - smoothstep(0.0, 1.5, dist));

    vec3 lightColor = vec3(0.9, 0.8, 0.5); // 暖金色光
    vec3 sceneColor = texture2D(tDiffuse, uv).rgb;
    gl_FragColor = vec4(sceneColor + lightColor * rays, 1.0);
}
```

> 适用场景：暗色深渊中一束光从上方射入、雾镜中手指擦出一道光路、银河中心的光晕向外辐射。

### 多层粒子叠加 = 天然体积光

AdditiveBlending 下，半透明粒子在重叠处自动变亮。让粒子从中心向边缘密度递减（`pow(dist, 2.0)` 衰减），多层层叠后自然产生光晕——不需要额外 shader。

### 相机 FogExp2 + 景深暗示

```javascript
// 粒子大小随深度变化（Vertex Shader 中已有透视除法）
gl_PointSize = aSize * (300.0 / -mvPosition.z);
// FogExp2 会让远处粒子自然融入背景色，产生"厚空气"感
```

调 `300.0` 常数：越大粒子越大；配合 FogExp2 的 density，远处的粒子同时缩小+变暗+偏色——三重深度暗示。

---

## 十三、SDF 形状库 + smin() + Domain Warping

> 本节技法用于**全屏 Fragment Shader**（`bgScene` + 正交相机模式，见 §九）；不用于粒子 vertex shader。核心：无需任何 mesh 即可在 shader 内构建完整 3D 形状。完整 Raymarching 场景模板见 **raymarching.md**。

### SDF 基础形状

```glsl
float sdSphere(vec3 p, float r) { return length(p) - r; }

float sdBox(vec3 p, vec3 b) {
    vec3 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

// 胶囊体（丝带/水草/流动形态）
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}

float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

float opU(float a, float b) { return min(a, b); }   // 并集
float opI(float a, float b) { return max(a, b); }   // 交集
float opS(float a, float b) { return max(a, -b); }  // 差集
```

### smin()：有机融合（水滴合并、气泡融合）

```glsl
// 多项式 smooth minimum。k 控制融合半径：0.3~0.5=水滴感，0.8+=气泡融合
float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}

// 使用示例：两个浮动球体有机融合
float scene(vec3 p) {
    float s1 = sdSphere(p - vec3(sin(uTime*0.7)*0.6, cos(uTime*0.5)*0.4, 0.0), 0.5);
    float s2 = sdSphere(p - vec3(cos(uTime*0.5)*0.6, sin(uTime*0.4)*0.5, 0.2), 0.4);
    return smin(s1, s2, 0.4);  // k=0.4：明显有机感
}
```

### Domain Warping：极光 / 岩浆 / 云雾质感

```glsl
// fBM 分形布朗运动（snoise 见 §八）
float fbm(vec3 p) {
    float v = 0.0, amp = 0.5;
    for (int i = 0; i < 5; i++) {
        v += amp * snoise(p);
        p  = p * 2.0 + vec3(1.7, 9.2, 5.3);  // 相位偏移，避免对齐伪影
        amp *= 0.5;
    }
    return v;
}

// 双层域扭曲（关键：两次 fBM 叠加产生极光/岩浆层次感）
float domainWarp(vec3 p, float t) {
    vec3 q = vec3(
        fbm(p + t * 0.2),
        fbm(p + vec3(5.2, 1.3, 0.0) + t * 0.15),
        fbm(p + vec3(1.3, 8.7, 0.0) + t * 0.18)
    );
    vec3 r = vec3(
        fbm(p + 4.0*q + vec3(1.7, 9.2, 3.3)),
        fbm(p + 4.0*q + vec3(8.3, 2.8, 5.1)),
        fbm(p + 4.0*q + vec3(5.4, 6.8, 1.2))
    );
    return fbm(p + 4.0 * r);
}

// 用法：全屏背景 fragment shader
void main() {
    vec2 uv   = vUv * 2.0 - 1.0;
    float w   = domainWarp(vec3(uv * 0.5, uTime * 0.05), uTime);
    vec3 colA = vec3(0.05, 0.10, 0.30);  // 深海蓝
    vec3 colB = vec3(0.50, 0.80, 1.00);  // 极光冰青
    gl_FragColor = vec4(mix(colA, colB, w * 0.5 + 0.5), 1.0);
}
```

> **调参**：空间频率 `uv * 0.5`（越小越宏观）；流速 `uTime * 0.05`（治愈取 0.02~0.08）；双层 fBM 让花纹不像简单噪声，而是有"湍流层次"——这是极光/岩浆质感的来源。

### Glow（距离场发光）

```glsl
// 在 rayMarch 循环中累积接近度，无需额外 pass
float glow = 0.0;
float t = 0.0;
for (int i = 0; i < 64; i++) {
    float d = scene(ro + rd * t);
    glow += exp(-d * 12.0) * 0.04;  // 越近 glow 越强，指数衰减
    if (d < 0.001) break;
    t += d; if (t > 30.0) break;
}
vec3 glowColor = mix(vec3(0.2, 0.4, 1.0), vec3(0.9, 0.8, 0.6), uCalm);
vec3 finalColor = surfaceColor + glowColor * glow * 1.5;
```

---

## 十四、振动增强（Vibrance Boost）— 线性工作流去饱和补偿

> 设计哲学源自 threejs-environment-water-and-sky 的 BT.709-luma 振动增强。Three.js r152+ 的 `outputColorSpace = SRGBColorSpace` 管线在 linear→sRGB 往返中会比 r93 时代的原始通道写入产生感知去饱和。振动增强以微量推向色度来补偿——不做全局饱和度乘法（那会过饱和亮部和暗部）。

### 14.1 原理

**振动 ≠ 饱和度**。饱和度是统一乘法——亮部和暗部以相同比例被推离灰色。振动是针对**中调**的——亮部和暗部变化小、中调变化大。这保留了高光和阴影的细节，只让"不太鲜艳也不太灰"的中间色更生动。

```
饱和度（不要用）：color.rgb = mix(gray, color.rgb, saturation)  // 全范围
振动（用这个）：  color.rgb = mix(vec3(luma), color.rgb, vibrance)  // BT.709 加权
```

### 14.2 GLSL 最小片段

```glsl
// === 振动增强 — 放在 colorspace_fragment 之前 ===
// vibrance: 1.0 = 无操作，>1.0 = 推向色度
// 推荐范围：莫兰迪/低饱和色板 = 1.03-1.08，自然色板 = 1.08-1.15
uniform float uVibrance;

// 在 main() 的末尾，tonemapping/colorspace 之前：
vec3 vC = gl_FragColor.rgb;
float vL = dot(vC, vec3(0.2126, 0.7152, 0.0722));  // BT.709 luma
gl_FragColor.rgb = clamp(mix(vec3(vL), vC, uVibrance), 0.0, 1.0);
```

### 14.3 Three.js ShaderMaterial 用法

```javascript
// JS 端：在 ShaderMaterial 的 uniforms 中定义
const waterMaterial = new THREE.ShaderMaterial({
  uniforms: {
    // ... 其他 uniforms ...
    uVibrance: { value: 1.08 },  // 默认：莫兰迪场景用 1.05-1.08
  },
  fragmentShader: `
    uniform float uVibrance;
    // ... 在 gl_FragColor 赋值后、最终输出前 ...
    vec3 vC = gl_FragColor.rgb;
    float vL = dot(vC, vec3(0.2126, 0.7152, 0.0722));
    gl_FragColor.rgb = clamp(mix(vec3(vL), vC, uVibrance), 0.0, 1.0);
  `,
});

// calm 映射：治愈态略提高振动（世界更"鲜活"），压抑态保持中性
// uVibrance = 1.0 + 0.08 * ts   (ts = smoothstep(calm), 范围 1.0-1.08)
```

### 14.4 按场景色板的校准指南

| 场景色板类型 | 推荐 vibrance | 理由 |
|------------|-------------|------|
| 莫兰迪 / 低饱和（Healing Space 默认） | 1.03–1.08 | 低饱和色板对振动敏感——>1.10 会将"高级灰"推成"廉价彩" |
| 自然色板（草地/海洋/森林） | 1.08–1.15 | 自然色板耐受更高振动——蓝天绿水在感知上预期更鲜艳 |
| 极简单色 / 黑白为主 | 1.00 | 无操作——单色场景不需要振动 |
| Frutiger Aero（Pixel Bloom 参考） | 1.03–1.06 | Frutiger Aero 的柔和粉彩与莫兰迪类似——轻触即可 |

### 14.5 ⚠️ 关键反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | vibrance 硬编码为 1.15 | **致命** | 莫兰迪场景过度饱和——灰蓝→艳蓝(ΔE>15)、灰紫→亮紫 | vibrance 必须可调，默认从 1.05 起步 |
| 2 | 用饱和度替代振动 | 警告 | `color = mix(gray, color, sat)` 在高光和阴影上产生色偏 | 用 BT.709 luma 加权——不是平均 gray |
| 3 | 振动在 colorspace 之后 | 警告 | 在 sRGB 编码后推色 → 色度偏移非均匀 | 振动放在 tonemapping 之前、colorspace 之前 |
| 4 | 对所有场景用同一 vibrance | 警告 | "治愈"和"压抑"用同一振动 → 情绪线索缺失 | calm 映射：治愈态略高（世界"鲜活"），压抑态中性 |

### 14.6 自检

- [ ] vibrance 是否可调（uniform 或变量，非硬编码）？
- [ ] 默认值是否匹配场景色板（莫兰迪 ≈ 1.05，自然 ≈ 1.10）？
- [ ] 振动代码是否放在 `colorspace_fragment` **之前**？
- [ ] 是否使用 BT.709 luma 系数（`0.2126, 0.7152, 0.0722`）而非简单平均？
- [ ] calm 是否映射 vibrance（治愈 > 压抑）？

---

## 十五、空间相位图扭曲（Spatial Phase-Map Warping）

> 设计哲学源自 threejs-environment-water-and-sky 的焦散 UV 扭曲：`warp = sin(uv.y*10+t*2) + cos(uv.x*10+t*2.5)`——不同空间位置有不同的扭曲方向和速度，让滑动纹理看起来像"在传播的波纹"而非"平移的贴纸"。通用化后适用于任何需要有机传播感的着色器。

### 15.1 原理

**问题**：纹理在 UV 上做刚性平移（`uv += vec2(t * speedX, t * speedY)`）→ 整个纹理以相同速度向同一方向滑动 → 感知为"贴纸在移动"。

**解法**：在 UV 采样前叠加空间相位图——一个随空间位置和时间变化的小幅位移场。不同（x,y）位置的位移不同 → 纹理局部扭曲 → 感知为"波纹在传播"。

```
刚性平移（不要）： uv_shifted = uv + vec2(t * 0.1, t * 0.05);
空间扭曲（要）：   uv_warped = uv + vec2(
    sin(uv.y * freq + t * phase1),
    cos(uv.x * freq + t * phase2)
) * amplitude;
```

### 15.2 GLSL 最小片段

```glsl
// === 空间相位图扭曲 — 放在纹理采样之前 ===
// amplitude: 0.01-0.05 UV 单位。0.01 = 微妙涟漪，0.05 = 明显焦散
// frequency: 5-20。低频 = 大波纹，高频 = 细碎波纹
// phase1/phase2: 不同的时间速度 — 一般互为质数（如 2.0 和 2.5）避免对称

uniform float uTime;
uniform float uWarpAmplitude;  // 推荐 0.015-0.03
uniform float uWarpFrequency;  // 推荐 8.0-12.0

// 在采样纹理之前：
vec2 warpedUV = vUv + vec2(
    sin(vUv.y * uWarpFrequency + uTime * 2.0),
    cos(vUv.x * uWarpFrequency + uTime * 2.5)
) * uWarpAmplitude;

// 然后用 warpedUV 采样纹理：
vec4 texColor = texture2D(uTexture, warpedUV);
```

### 15.3 参数调优指南

| 参数 | 范围 | 效果 | 增大后的视觉变化 |
|------|------|------|----------------|
| `amplitude` | 0.01–0.05 | 扭曲强度 | 过大 → 纹理撕裂/跳跃。0.05 = 焦散级，0.015 = 涟漪级 |
| `frequency` | 5–20 | 空间变化密度 | 高 → 细碎波纹。低 → 缓慢大波纹 |
| `phase1 : phase2` 比值 | 1 : 1.2–1.5 | 方向不对称性 | 1:1 = 对称漩涡（不好）。1:1.25 = 自然不对称 |
| 时间速度 | 1.5–3.0 | 传播速度 | 过快 → 像"快进"。过慢 → 几乎不动的静态扭曲 |

**关键安全约束**：`amplitude * frequency / (2π)` 不能超过 ~0.3。超过此值 → 相邻像素的 UV 偏移差值 > 纹理周期 → 出现视觉撕裂。例如 `amp=0.03, freq=10` → `0.03*10/6.28 ≈ 0.048` ✅；`amp=0.1, freq=20` → `0.1*20/6.28 ≈ 0.32` ⚠️ 临界。

### 15.4 应用场景矩阵

| 场景 | amplitude | frequency | 纹理 | 效果 |
|------|-----------|-----------|------|------|
| **水面焦散**（3D） | 0.015 | 10 | caustics 贴图 | 水下光斑有机传播——每个区域方向不同 |
| **水面涟漪**（2D Pixel Bloom） | 0.02 | 8 | 水面渐变纹理 | 涟漪不规则扩散——不同区域不同步 |
| **FBO 流体表面细节** | 0.01 | 12 | 细节噪声纹理 | 在流体平流之上叠加微观扰动 |
| **Ganzfeld 光场色相漂移** | 0.03 | 5 | 色相渐变 | 缓慢、大尺度的色温变化——像极光 |
| **能量场波动** | 0.025 | 15 | 发光渐变 | 快速细碎波动——"活跃的能量" |
| **Reaction-Diffusion 有机运动** | 0.008 | 6 | RD 输出纹理 | 极微妙扰动——让 Turing 图案"活"起来 |

### 15.5 p5.js 2D 适配

```javascript
// === 空间相位图扭曲 — p5.js 版 ===
// 用于 Canvas2D 纹理坐标或采样网格的扭曲

/**
 * @param {number} x, y — 画布坐标（或标准化 UV 坐标）
 * @param {number} time — 全局时间（秒）
 * @param {number} freq — 空间频率（推荐 0.02-0.08，对应画布坐标尺度）
 * @param {number} amp — 扭曲幅度（推荐 2-6 像素）
 * @returns {{x: number, y: number}} 扭曲后的坐标
 */
function warpCoord(x, y, time, freq = 0.04, amp = 3) {
  return {
    x: x + Math.sin(y * freq + time * 2.0) * amp,
    y: y + Math.cos(x * freq + time * 2.5) * amp,
  };
}

// 用法 1：扭曲纹理坐标（配合 p5.js texture()）
// 在 beginShape()/vertex() 中对每个顶点的 UV 做 warp
// const w = warpCoord(u * CW, v * CH, millis() * 0.001, 0.03, 3);
// vertex(w.x, w.y, w.x / CW, w.y / CH);

// 用法 2：扭曲采样网格（用于噪声场采样）
// 原本：const n = noise(x * 0.03, y * 0.03);
// 改为：const w = warpCoord(x, y, millis() * 0.001, 0.04, 4);
//       const n = noise(w.x * 0.03, w.y * 0.03);
// → 噪声场本身在"流动"，产生有机的图案运动

// ⚠️ 性能：warp 在每个采样点计算一次——如果采样点 > 10K/帧，预计算 warping LUT
```

### 15.6 反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | 振幅过大 | **致命** | `amp > 0.1` → UV 撕裂、纹理跳变 | amp ∈ [0.01, 0.05]，验证 `amp * freq / 6.28 < 0.3` |
| 2 | 对称相位 | 警告 | phase1 = phase2 → 漩涡状扭曲（不自然） | phase1 : phase2 比值 ≈ 1 : 1.25（互质） |
| 3 | p5.js 逐像素 warp | 警告 | 614K 像素逐帧计算 → 帧率崩溃 | p5.js 中用 warp 作用于采样网格（≤ 1000 点），非逐像素 |
| 4 | warp 在 rigid 平移之后叠加 | 警告 | `uv += rigidSlide + warp` → 双倍位移 → 纹理"飞出" | 选择一种：要么 rigid 平移，要么 warp——不同时用 |

### 15.7 自检

- [ ] `amplitude * frequency / 6.28 < 0.3`（无撕裂）？
- [ ] phase1 : phase2 ≠ 1:1（不对称，避免对称漩涡）？
- [ ] p5.js 版本作用于采样网格（≤ 1000 点），非逐像素？
- [ ] 是否没有同时使用 rigid 平移和 warp（选一个）？

---

## 十六、植被透光 + Fresnel 边缘光

> 设计哲学源自 stylized-scene 的草地透光（Half-Life 2 GPU Gems 背部透光技术）和 Fresnel 边缘发光。透光让薄的部分看起来被光穿透——适合"内在光芒"、"外壳剥落露核"、"光从内部透出"等疗愈隐喻。Fresnel 让边缘发光——适合"被包裹的光从边缘溢出来"的视觉同构。
>
> **前置条件**：场景必须有方向光（`DirectionalLight`）用于透光计算。无方向光 → 跳过透光，仅用 Fresnel。

### 16.1 透光（Back-Translucency）— Half-Life 2 技术

物理原理：光线从背面穿透薄材质（叶片、薄膜、半透明外壳）→ 在正面可见。GPU Gems 的方案：用表面法线扭曲入射光方向，让光"绕过"边缘到达正面。

```glsl
// === 透光 — 放在 fragment shader 的 emissive 计算中 ===
// 前置条件：场景有 DirectionalLight → sunDir 有效

uniform vec3 uSunDirection;     // 方向光的世界空间方向（normalize）
uniform float uTranslucency;    // 0.0 = 关闭, 1.0 = 全强度。calm 可映射
uniform float uHeightT;         // 归一化高度 0-1（0=根部/厚处, 1=尖端/薄处）

// 视方向
vec3 viewDir = normalize(cameraPosition - vWorldPosition);

// 法线扭曲：让光"绕过"表面边缘到达正面
// distortion 控制绕过的程度——0.5 = 标准，1.0 = 极度（光几乎从正面可见）
float distortion = 0.5;
vec3 transLightDir = normalize(uSunDirection + vWorldNormal * distortion);

// 背面光强度：视方向与扭曲后的逆光方向越对齐，透光越强
float backLight = pow(max(dot(viewDir, -transLightDir), 0.0), 3.0);

// 厚度遮罩：薄处（heightT 高）= 更透光
float thicknessMask = pow(uHeightT, 1.5);

// 透光颜色 — 温暖的黄绿色（模拟叶绿素透光）或按隐喻选择
vec3 translucencyColor = vec3(0.81, 0.88, 0.42); // #cfe06a 的线性空间等价

// 最终透光 emissive
vec3 translucency = translucencyColor * backLight * thicknessMask * 1.2 * uTranslucency;
```

**参数校准（按隐喻选择透光颜色）**：

| 隐喻 | 透光颜色（线性空间） | 物理含义 |
|------|--------------------|---------|
| 半透明薄膜/外壳剥落 | `(0.95, 0.85, 0.65)` 暖白琥珀 | "内核发出温暖的光" |
| 植物/叶片/草地 | `(0.81, 0.88, 0.42)` 黄绿 | "阳光穿过绿叶"——叶绿素透光 |
| 水母/深海生物 | `(0.45, 0.70, 0.85)` 蓝绿 | "生物荧光穿透胶质" |
| 薄膜/肥皂泡 | `(0.85, 0.80, 0.90)` 淡紫白 | "光在薄膜中干涉" |

### 16.2 Fresnel 边缘光

物理原理：掠射角（视线几乎平行于表面）反射率最高。边缘发光 = (1 - N·V)^power → 只有边缘可见。

```glsl
// === Fresnel 边缘光 — 放在 emissive 计算中 ===
uniform float uFresnelEnabled;  // 0.0 = 关闭, 1.0 = 开启

// 掠射角因子：视线与法线的夹角越大 → 值越高
float fresnel = pow(1.0 - max(dot(vWorldNormal, viewDir), 0.0), 4.0);

// 边缘光颜色 — 按隐喻选择
vec3 fresnelColor = vec3(0.92, 0.95, 0.75); // #eaf2c0 的线性等价——淡暖白边缘

// 最终边缘光 emissive
vec3 fresnelEmissive = fresnelColor * fresnel * 0.25 * uFresnelEnabled;
```

**power 参数的效果**：
- `pow(..., 2.0)` → 宽边缘光——物体大部分边缘都发光（"雾气包裹"感）
- `pow(..., 4.0)`（推荐）→ 中等边缘——清晰的边缘线条
- `pow(..., 6.0)` → 窄边缘——只有最掠射的角度才发光（"锋利的光边"）

**Fresnel 颜色校准（按隐喻）**：

| 隐喻 | Fresnel 颜色 | 视觉感受 |
|------|-------------|---------|
| 外壳剥落露核 | 暖琥珀 `(0.95, 0.7, 0.4)` | "内核的光从裂缝溢出" |
| 内在光芒 | 淡暖白 `(0.92, 0.95, 0.75)` | "柔软的光晕包裹物体" |
| 薄膜/茧 | 珍珠白 `(0.9, 0.88, 0.95)` | "薄如蝉翼的表面" |
| 冰/水晶 | 淡蓝白 `(0.75, 0.85, 0.95)` | "冰冷但透光的晶体" |

### 16.3 完整集成骨架（fragment shader）

```glsl
// === emissive = 透光 + Fresnel — 放在 main() 中 PBR 光照之后 ===

// 透光（需要方向光）
#ifdef HAS_DIRECTIONAL_LIGHT
vec3 viewDir = normalize(cameraPosition - vWorldPosition);
vec3 transLightDir = normalize(uSunDirection + vWorldNormal * 0.5);
float backLight = pow(max(dot(viewDir, -transLightDir), 0.0), 3.0);
float thicknessMask = pow(uHeightT, 1.5);
vec3 translucency = uTranslucencyColor * backLight * thicknessMask * 1.2 * uTranslucency;
#else
vec3 translucency = vec3(0.0);
#endif

// Fresnel 边缘光（始终可用——不依赖方向光）
float fresnel = pow(1.0 - max(dot(vWorldNormal, viewDir), 0.0), 4.0);
vec3 fresnelEmissive = uFresnelColor * fresnel * 0.25 * uFresnelEnabled;

// 合并 emissive
vec3 totalEmissive = materialEmissive + translucency + fresnelEmissive;
```

### 16.4 与其他发光效果的协调

**⚠️ 如果场景已有 AdditiveBlending 粒子**：
- 透光强度降低 50%（`* 0.6` 替代 `* 1.2`）
- Fresnel 强度降低 40%（`* 0.15` 替代 `* 0.25`）
- 原因：多层发光叠加 → 画面过曝 → 失去"包裹感"变成"刺眼"

**⚠️ 如果场景有 FogExp2**：
- 透光和 Fresnel 的 emissive 在雾中会被衰减（emissive 不参与雾计算 → 不会自然衰减）
- 需要手动：`translucency *= exp(-fogDensity * distance)` 或直接降低 calm=0 时的 emissive 强度

**calm 映射**：
- `uTranslucency = calm`（压抑态 >> 内核被包裹不发光；治愈态 >> 内核光芒完全释放）
- `uFresnelEnabled = calm * calm`（治愈态边缘光更亮——"完整的光"）

### 16.5 反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | 无方向光时硬跑透光 | **致命** | sunDir = (0,0,0) → 透光计算结果 = NaN 或 0 → 无效果或画面异常 | 用 `#ifdef HAS_DIRECTIONAL_LIGHT` 守卫，无方向光时跳过透光 |
| 2 | 在不透明粗几何体上用 Fresnel | 警告 | 石头/金属边缘发光 → "塑料模型"感 | Fresnel 仅用于半透明隐喻元素（薄膜/外壳/晶体/植物）——不用于刚体 |
| 3 | 透光颜色与场景光源颜色冲突 | 警告 | 暖光透光 + 冷光场景光源 → 画面色彩不协调 | 透光颜色应与场景主光源色温一致（或故意相反——隐喻"内核和外部不同"） |
| 4 | AdditiveBlending 粒子 + 全强度透光 | 警告 | 双重发光叠加 → 过曝 | 检测粒子系统 → 透光强度减半（见 §16.4） |
| 5 | 忽略 emitter 在雾中的行为 | 警告 | emissive 不参与 fog 计算 → 远处仍然发光 → 雾失去深度暗示 | 手动衰减或降低 calm=0 时的发射强度 |

### 16.6 自检

- [ ] 场景有方向光？（无 → 跳过透光）
- [ ] 透光颜色是否与隐喻一致（不是随机选择）？
- [ ] Fresnel 是否仅用于半透明/有机元素（不是石头/金属）？
- [ ] 是否有 AdditiveBlending 粒子 → 透光/Fresnel 强度已减半？
- [ ] calm 是否映射了 `uTranslucency` 和 `uFresnelEnabled`？
