# 海洋水面 — Gerstner 波疗愈场景

> 数学基础源自 OceanThreejs 的 Gerstner 涌浪系统。适配到 healing-space：**不引入 FFT/WebGL2/GPU compute——用 6 条 Gerstner 波的解析公式在 vertex shader 中直接计算水面几何。移动端可用、单文件可嵌入。**
>
> 设计哲学继承 OceanThreejs 的核心原则：**一切视觉细节从底层位移场派生——泡沫从 Jacobian 行列式、法线从解析导数、颜色从 Fresnel + 水深。** 不是"叠加泡沫贴图"——泡沫是波浪折叠的几何产物。
>
> **加载时机**：STEP 5"应用四大维度"执行时必读。当决策树判定隐喻含"水面波浪/海浪/潮汐/涟漪/湖泊/海洋"时。
>
> **触发条件**：用户描述含 海/浪/潮汐/水面/湖泊/海洋/涟漪/波涛。

---

## 一、为什么不是 FFT

OceanThreejs 的 FFT 管线需要 `EXT_color_buffer_float`（移动端 Safari 不支持）+ 蝴蝶纹理预计算 + 6 GPU pass/帧。healing-space 的单文件 H5 约束下不可行。

**Gerstner 波是解析的**——不需要 FFT、不需要频谱、不需要 GPU compute。6 条波在 vertex shader 中直接计算位移 + 法线 + Jacobian。这是 Unity 标准海洋 shader 的数学基础。

---

## 二、Gerstner 波 vertex shader（最小实现）

### 2.1 平面网格

```javascript
// JS: 创建水面网格
const OCEAN_SIZE = 80;   // 世界空间尺寸
const OCEAN_SEGMENTS = 256; // 顶点密度——256² ≈ 65K 顶点，平滑足够
const oceanGeo = new THREE.PlaneGeometry(OCEAN_SIZE, OCEAN_SIZE, OCEAN_SEGMENTS, OCEAN_SEGMENTS);
oceanGeo.rotateX(-Math.PI / 2); // 平面→水平面（XZ 平面，Y 朝上）

// 顶点着色器需要 xz 世界坐标——用 position 的 xz 分量
// PlaneGeometry.rotateX(-PI/2) 后：position.x = 世界 X, position.z = -世界 Z(原始Y), position.y = 世界 Y(向上)
// 实际上：PlaneGeometry 默认在 XY 平面。rotateX(-PI/2) 后变为 XZ 平面，position.y 变为原来的 -z。
// 直接用 attribute 'position' 的 x 和 z 分量（或 y，取决于旋转方式）。
// 最简单做法：在 vertex shader 中把 localPos.xz 当作世界 XZ 坐标。
```

### 2.2 波参数（JS 端定义，通过 uniform 传入）

```javascript
// 6 条 Gerstner 波——每条波 4 个参数：(方向x, 方向z, 角频率, 振幅, 陡度)
// 存储为 4 个 vec4 uniform 数组
const waveParams = [
  // 大涌浪——方向约 45°，长波长
  { dir: [0.7, 0.7], omega: 0.8, amp: 1.5, steepness: 0.4 },
  // 中浪——方向约 30°
  { dir: [0.85, 0.5], omega: 1.2, amp: 0.9, steepness: 0.5 },
  // 中浪——方向约 60°
  { dir: [0.5, 0.85], omega: 1.1, amp: 0.8, steepness: 0.45 },
  // 小浪——方向约 -20°
  { dir: [0.95, -0.3], omega: 1.8, amp: 0.4, steepness: 0.6 },
  // 小浪——方向约 -50°
  { dir: [0.6, -0.8], omega: 2.0, amp: 0.35, steepness: 0.55 },
  // 细浪——方向约 10°
  { dir: [0.98, 0.2], omega: 2.5, amp: 0.2, steepness: 0.7 },
];

function packWaveUniforms(waves) {
  const dirAmp   = []; // (dirX, dirY, omega, amp)
  const steepness = []; // (steepness, 0, 0, 0)
  for (const w of waves) {
    dirAmp.push(w.dir[0], w.dir[1], w.omega, w.amp);
    steepness.push(w.steepness, 0, 0, 0);
  }
  return {
    uWavesDirAmp: new Float32Array(dirAmp),
    uWavesSteep: new Float32Array(steepness),
  };
}
```

### 2.3 Vertex Shader

```glsl
// === ocean.vert — Gerstner 波位移 ===
// uniform
uniform float uTime;
uniform float uChoppiness;  // calm 映射：1.5(压抑) → 0(治愈)
uniform float uWaveAmplitude; // calm 映射：1.0(压抑) → 0.1(治愈)
uniform vec4  uWavesDirAmp[6];  // 每波: (dirX, dirZ, omega, amplitude)
uniform vec4  uWavesSteep[6];   // 每波: (steepness, 0, 0, 0)
uniform float uFoamThreshold;   // Jacobian 阈值——映射 foam 出现时机

// varying → fragment
varying vec3  vWorldPos;
varying vec3  vNormal;
varying float vFoam;
varying float vHeight;  // 波高——用于颜色混合

const float GRAVITY = 9.81;

void main() {
  vec3 pos = position;  // 平面网格顶点（Y=0, XZ 为世界坐标）
  vec3 displaced = vec3(pos.x, 0.0, pos.z);

  // 累积量——用于法线和 Jacobian
  float sumDxDx = 0.0, sumDyDx = 0.0, sumDzDx = 0.0;
  float sumDxDz = 0.0, sumDyDz = 0.0, sumDzDz = 0.0;

  for (int i = 0; i < 6; i++) {
    vec4  da = uWavesDirAmp[i];
    float st = uWavesSteep[i].x;

    float dirX   = da.x;
    float dirZ   = da.y;
    float omega  = da.z;
    float amp    = da.w * uWaveAmplitude;
    float steep  = st * uChoppiness;

    // 相位：θ = ω * dot(D, (x,z)) + φ * t
    float dotP = dirX * pos.x + dirZ * pos.z;
    float phi = sqrt(GRAVITY * omega);  // 深水色散：φ = √(g·ω)
    float theta = omega * dotP + phi * uTime;

    float cosT = cos(theta);
    float sinT = sin(theta);

    // 位移
    displaced.x -= steep * amp * cosT * dirX;
    displaced.y += amp * sinT;
    displaced.z -= steep * amp * cosT * dirZ;

    // 偏导数（用于法线 + Jacobian）
    float wx = omega * dirX;
    float wz = omega * dirZ;

    sumDxDx += steep * amp * wx * sinT * dirX * dirX;
    sumDyDx += amp * wx * cosT * dirX;
    sumDzDx += steep * amp * wx * sinT * dirZ * dirX;

    sumDxDz += steep * amp * wz * sinT * dirX * dirZ;
    sumDyDz += amp * wz * cosT * dirZ;
    sumDzDz += steep * amp * wz * sinT * dirZ * dirZ;
  }

  // Jacobian 行列式：J = (1+∂Dx/∂x)(1+∂Dz/∂z) - (∂Dx/∂z)²
  // J < 1 → 波面压缩。J < threshold → 泡沫。
  float j11 = 1.0 + sumDxDx;
  float j22 = 1.0 + sumDzDz;
  float j12 = sumDxDz;
  float J = j11 * j22 - j12 * j12;

  // 泡沫：J 低于阈值 → 折叠检测
  vFoam = smoothstep(uFoamThreshold + 0.15, uFoamThreshold - 0.05, J);

  // 解析法线
  vec3 tangentX = vec3(j11, sumDyDx, sumDzDx);
  vec3 tangentZ = vec3(sumDxDz, sumDyDz, j22);
  vec3 normal = normalize(cross(tangentZ, tangentX));

  vWorldPos = displaced;
  vNormal = normal;
  vHeight = displaced.y;

  gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
}
```

---

## 三、水面着色 fragment shader

### 3.1 Fresnel + 简化水面颜色

```glsl
// === ocean.frag — Fresnel + 水面着色 ===
uniform vec3  uViewPos;
uniform vec3  uSunDirection;
uniform vec3  uSunColor;
uniform float uSunIntensity;

uniform vec3  uShallowColor;   // 浅水色（治愈态：清澈蓝绿）
uniform vec3  uDeepColor;      // 深水色（压抑态：暗灰蓝）
uniform float uWaterClarity;   // calm 映射：0.3(浑浊) → 1.0(清澈)

uniform float uFoamIntensity;
uniform float uFoamScale;
uniform float uFoamSpeed;
uniform vec3  uFoamColor;
uniform float uTime;

// SSS 次表面散射（wrap lighting — 浪峰透光）
uniform vec3  uWaterSSS;        // SSS 颜色（翡翠绿/青绿，如 #43c3ab）
uniform float uSssScale;        // SSS 强度（0.3–0.7，治愈态偏高：水更清澈）
uniform float uSssDistortion;   // 光线折射偏移（0.15–0.25）
uniform float uSssPower;        // 角度响应锐度（3.0–6.0）
uniform float uSssMinHeight;    // SSS 触发最低波高（0.1–0.3）
uniform float uSssMaxHeight;    // SSS 饱和最高波高（0.8–1.5）

// 体积雾 + 太阳散射（大气透视）
uniform float uFogDensity;       // 雾密度（0.0002–0.002），calm 映射
uniform float uTurbidity;        // 大气浑浊度（2–12），calm 映射
uniform float uSunDiskSize;      // 太阳光盘锐度（0.9990–0.9998）
uniform float uSunGlowSize;      // 太阳光晕软度（0.97–0.99）
uniform float uSunDiskIntensity; // 光盘亮度（1.0–3.0）
uniform float uSunGlowIntensity; // 光晕亮度（0.3–1.2）
uniform float uFogSunScattering; // 总散射强度（0.3–0.8），calm 映射

// 深度透明度（海底可见度）
uniform float uSeafloorY;        // 海底世界空间 Y 坐标

// 环境反射（简化——无 HDR 贴图时用天空渐变近似）
uniform vec3  uSkyColor;       // 天空色（用于反射）
uniform vec3  uHorizonColor;   // 地平线色

varying vec3  vWorldPos;
varying vec3  vNormal;
varying float vFoam;
varying float vHeight;

// --- fBm 噪声（打散泡沫） ---
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i), hash(i + vec2(1,0)), f.x),
    mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x),
    f.y
  );
}
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p *= 2.07;
    a *= 0.5;
  }
  return v;
}

void main() {
  vec3 N = normalize(vNormal);
  vec3 V = normalize(uViewPos - vWorldPos);
  vec3 L = normalize(uSunDirection);

  // --- Fresnel (Schlick) ---
  float NoV = max(dot(N, V), 0.0);
  float F0 = 0.02; // 水的折射率 ≈ 1.33 → F0 ≈ 0.02
  float fresnel = F0 + (1.0 - F0) * pow(1.0 - NoV, 5.0);

  // --- 水面颜色：浅水 → 深水 ---
  // 波峰(高) → 浅水色。波谷(低) → 深水色。
  float heightFactor = smoothstep(-1.5, 2.0, vHeight);
  vec3 waterColor = mix(uDeepColor, uShallowColor, heightFactor * uWaterClarity);

  // --- 反射：Fresnel 加权天空色 ---
  // 简化版——无环境贴图时用天空渐变
  vec3 reflection = mix(uHorizonColor, uSkyColor, NoV) * uSunIntensity;

  // --- 镜面高光 (Blinn-Phong 简化版) ---
  vec3 H = normalize(L + V);
  float spec = pow(max(dot(N, H), 0.0), 256.0);  // 水的高光很锐
  vec3 specular = uSunColor * spec * 0.6 * uSunIntensity;

  // --- 组合 ---
  vec3 color = mix(waterColor, reflection, fresnel);
  color += specular;

  // --- 泡沫 ---
  float foamNoise = fbm(vWorldPos.xz * uFoamScale * 0.05 + uTime * uFoamSpeed * 0.3);
  float foamMask = vFoam * (0.6 + 0.4 * foamNoise);  // 噪声打散
  foamMask = clamp(foamMask, 0.0, 1.0);
  color = mix(color, uFoamColor, foamMask * uFoamIntensity);

  // --- 次表面散射 SSS（wrap lighting — 浪峰透光）---
  // 原理：光线进入水体后被波浪折射，弯曲后射向相机。
  // distortedLight 模拟折射后的光线方向。
  // dot(V, distortedLight) = 折射光与视线重合度 → 重合越多，透射光越多。
  vec3 distortedLight = normalize(-L + N * uSssDistortion);
  float sssAlignment = max(0.0, dot(V, distortedLight));
  float sss = pow(sssAlignment, uSssPower) * uSssScale;
  // 高度遮罩——严格限定在浪峰处（浪谷水厚，光无法穿透）
  float heightMask = smoothstep(uSssMinHeight, uSssMaxHeight, vHeight);
  sss *= heightMask;
  color += uWaterSSS * sss * uSunIntensity;

  // --- 体积雾 + 太阳散射（大气透视）---
  // 远处水面渐变为雾色——不是"水消失了"而是"光被大气散射取代"
  float dist = length(vWorldPos - uViewPos);
  float fogFactor = 1.0 - exp(-pow(dist * uFogDensity, 2.0));
  fogFactor = clamp(fogFactor, 0.0, 1.0);

  // 太阳散射：视线越接近太阳方向，雾光越亮
  float sunDot = dot(V, L);
  // turbidity 高 → 更多颗粒散射 → 光晕范围缩小（光被吸收）
  float dynamicGlowSize = uSunGlowSize - (uTurbidity * 0.002);
  float sunGlow = smoothstep(dynamicGlowSize, 1.0, sunDot);      // 软光晕
  float sunDisk = smoothstep(uSunDiskSize, 1.0, sunDot);         // 锐利光盘
  // turbidity 削弱直达光
  float dynamicDiskIntensity = uSunDiskIntensity / (1.0 + uTurbidity * 0.1);

  // 雾色 = 基础地平线色 + 太阳散射叠加
  vec3 fogColor = uHorizonColor;
  fogColor += uSunColor * sunGlow * uSunGlowIntensity;
  fogColor += uSunColor * sunDisk * dynamicDiskIntensity;

  color = mix(color, fogColor, fogFactor);

  // --- 深度透明度（Beer-Lambert，世界空间近似）---
  // 水面上方的垂直深度 = 海底 Y − 水面片元 Y
  // 走世界空间近似（不读 depth texture——移动端友好）
  float waterDepth = uSeafloorY - vWorldPos.y;

  // 片元在水面下方 → 始终不透明
  if (waterDepth <= 0.0) {
    gl_FragColor = vec4(color, 1.0);
    return;
  }

  // 视线穿过水体的路径长度 = 垂直深度 / cos(视角)
  // 俯视 → dot(N,V) ≈ 1 → pathLength ≈ waterDepth（薄水透明）
  // 水平看 → dot(N,V) ≈ 0 → pathLength → ∞（不透明）
  // max(abs(...), 0.01) 防止除零——极斜视角不崩
  float pathLength = waterDepth / max(abs(dot(N, V)), 0.01);

  // Beer-Lambert 吸收
  float alphaAbsorption = 1.0 - exp(-pathLength / uWaterClarity);
  float alpha = clamp(alphaAbsorption, 0.0, 1.0);

  // 能量守恒：浅水透明 → 看到海底颜色（在 waterColor 中被 mix 处理）。
  // alpha 确保从透明(alpha→0)到不透明(alpha→1)的平滑过渡。
  gl_FragColor = vec4(color, alpha);
}
```

---

## 四、calm 参数映射

水面场景的三幕剧：风暴海面（压抑态）→ 风停浪小（过渡）→ 平静如镜（治愈态）。

```javascript
// calm 总线——海洋水面参数映射
function applyOceanCalmState(calm, oceanMat) {
  const c  = calm;
  const ts = c * c * (3 - 2 * c);  // smoothstep

  const u = oceanMat.uniforms;

  // 波幅：3m(风暴) → 0.1m(如镜)
  u.uWaveAmplitude.value = 1.0 - 0.9 * ts;

  // choppiness：1.5(尖峰) → 0(正弦)
  u.uChoppiness.value = 1.5 - 1.5 * ts;

  // 泡沫阈值：-0.2(易触发泡沫) → 0.8(几乎不触发)
  u.uFoamThreshold.value = -0.2 + 1.0 * ts;
  u.uFoamIntensity.value = 1.0 - 0.9 * ts;

  // 水色：暗灰蓝(风暴) → 清澈蓝绿(治愈)
  u.uDeepColor.value.set(
    0.05 + 0.05 * ts,   // R: 0.05→0.10
    0.08 + 0.12 * ts,   // G: 0.08→0.20
    0.15 + 0.25 * ts    // B: 0.15→0.40
  );
  u.uShallowColor.value.set(
    0.10 + 0.10 * ts,   // R
    0.30 + 0.30 * ts,   // G
    0.50 + 0.30 * ts    // B
  );

  // 清澈度：0.3(浑浊) → 1.0(清澈见底)
  u.uWaterClarity.value = 0.3 + 0.7 * ts;

  // 环境光：风暴昏暗 → 治愈明亮
  u.uSunIntensity.value = 0.4 + 0.6 * ts;

  // 反射强度（治愈态水面如镜 → 反射更清晰）
  // Fresnel F0 不需要改——它是物理常数

  // SSS 次表面散射——浪峰透光
  // 平静时水更清澈 → SSS 更明显（光可以穿透更厚的浪峰）
  // 风暴时水浑浊 → SSS 几乎不可见
  u.uWaterSSS.value.set(0.26, 0.76, 0.67);             // 翡翠绿——水的透射色（固定）
  u.uSssScale.value       = 0.15 + 0.45 * ts;          // 0.15(风暴-几乎无) → 0.60(治愈-清晰透光)
  u.uSssDistortion.value  = 0.2;                        // 折射偏移——物理量，不随calm变化
  u.uSssPower.value       = 3.0 + 2.0 * ts;            // 3.0(风暴-宽角度模糊) → 5.0(治愈-锐利聚焦)
  u.uSssMinHeight.value   = 0.1 + 0.2 * ts;            // 0.1(风暴-低浪峰也触发) → 0.3(治愈-只在大浪峰)
  u.uSssMaxHeight.value   = 0.8 + 0.7 * ts;            // 0.8 → 1.5

  // 体积雾——大气透视
  // 风暴：浓雾 → 看不清远方（"不知道前面有什么"）
  // 治愈：清晰 → 远方一览无余（"一切都在视野之内"）
  u.uFogDensity.value        = 0.0015 - 0.0010 * ts;    // 0.0015(风暴) → 0.0005(治愈)
  u.uTurbidity.value         = 10.0 - 6.0 * ts;         // 10(风暴-浑浊) → 4(治愈-清澈)
  u.uFogSunScattering.value  = 0.3 + 0.5 * ts;          // 0.3(风暴-暗淡) → 0.8(治愈-明亮)
  u.uSunDiskSize.value       = 0.9995;                   // 物理常数——固定
  u.uSunGlowSize.value       = 0.985;                    // 物理常数——固定
  u.uSunDiskIntensity.value  = 1.0 + 1.5 * ts;          // 1.0 → 2.5
  u.uSunGlowIntensity.value  = 0.4 + 0.6 * ts;          // 0.4 → 1.0

  // 海底 Y——场景级固定值，不随 calm 变化
  // 由场景设计者设定（如 seafloorY = -5.0 表示海底在水面下 5m）
  // uSeafloorY 只在 JS 端设定一次，不在每帧映射中改变
}
```

**映射设计原理**：每一行都是一个情绪决策——
- 波幅 3m→0.1m = 愤怒的浪头→平静的呼吸
- choppiness 1.5→0 = 尖峰怒涛→柔和正弦
- 泡沫消失 = 风暴的痕迹被抹去
- 水变清澈 = 你能看见自己了
- 雾散开 = 远方不再模糊——你能看见地平线了

---

## 五、移动端降级

```javascript
const isMobile = /Mobile|Android|iPhone/.test(navigator.userAgent);

if (isMobile) {
  // 1. 波数：6 → 3
  // 只保留最大的 3 条波（涌浪 + 2 条中浪）
  // 在打包 waveParams 时只取前 3 条

  // 2. 网格精度：256² → 128²
  // const SEGMENTS = 128;

  // 3. Jacobian 泡沫 → 简化
  // 移动端跳过 Jacobian 计算——用 heightFactor 替代
  // vFoam = smoothstep(-0.5, 1.5, vHeight); // 只在高波峰出现泡沫

  // 4. fBm 噪声 → 单层 noise
  // for (int i = 0; i < 4; i++) → for (int i = 0; i < 1; i++)

  // 5. SSS 保持——wrap lighting 无纹理采样，成本极低，移动端无需降级

  // 6. 体积雾降级——跳过太阳散射（smoothstep + pow 开销）
  // 移动端只保留指数雾：fogFactor = 1.0 - exp(-pow(dist * density, 2.0))
  // mix(color, uHorizonColor, fogFactor)  ← 纯雾色混合，无太阳光晕
  // sunDisk/sunGlow smoothstep 在任何距离下都不执行——省 ~10 ALU/px

  // 7. 深度透明度降级——移动端跳过 depth alpha
  // 移动端 alpha 固定为 1.0（水面始终不透明）
  // Beer-Lambert 的 world-space 近似虽然无纹理，但 mobile 的浅滩场景通常不设海底 geometry

  // 8. Fresnel + specular 保持（几乎零成本）
}
```

**降级原则**：波数减半（6→3）+ 网格减至 1/4（256²→128² = 16K 顶点）+ 跳过 Jacobian（用高度替代）。移动端仍能看到水面、Fresnel 反射、简化泡沫——视觉弧线完整。

---

## 六、三幕剧适配

```
第一幕（intro, calm=0）：风暴海面
  - 波高 3m，choppiness 1.5，泡沫密布
  - 天色灰暗，太阳被云遮
  - 文案："这就是你现在的感受。"（看见愤怒的海）

第二幕（active, calm: 0→0.95）：风在变小
  - 用户长按 → calm 上升 → 波高降低/泡沫减少/水色变清
  - 交互：长按 = 安抚海浪。松手 = 浪又起来一点（可逆——平静需要持续投入）
  - 文案："它在变。你也在变。"（陪伴）

第三幕（complete, calm>0.95）：平静如镜
  - 波高 0.1m，choppiness 0，无泡沫
  - 水面反射天空——"你能看见自己了"
  - 文案："它过去了。你在这里。"（见证）
```

---

## 七、反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | 粒子做海 | 致命 | 150K 蓝粒子上下浮动——米粒汤 | 用 Gerstner 波 vertex displacement——**连续曲面** |
| 2 | 正弦波无 choppiness | 警告 | 完美对称正弦波 = 塑料水/果冻 | choppiness > 0——波峰尖锐、波谷平缓 |
| 3 | 无泡沫 | 警告 | 浪头无白沫 = 油/果冻 | Jacobian 折叠检测 → 波峰自动白 |
| 4 | 无 Fresnel | 警告 | 从正上方看和从水平看完全一样 | Fresnel: 水平=反射强(银色)，俯视=看透(水色) |
| 5 | 所有波同方向 | 警告 | 一排排平行浪——像水渠 | 6 条波方向散布在 120° 范围内 |
| 6 | choppiness > 1.0 | 致命 | 波峰形成闭环——水面自交 | steepness 永远 ≤ 1.0，通常 ≤ 0.7 |
| 7 | 移动端 256² 网格 | 警告 | 移动端 GPU 顶点处理 65K 顶点帧率低 | 移动端降为 128² = 16K 顶点 |
| 8 | turbidity > 12 + fogDensity > 0.002 | **致命** | 整帧白雾——水面完全不可见 | turbidity ≤ 12，fogDensity ≤ 0.002。即使用户在最压抑态 (calm=0)，雾也不能掩盖水面本身 |
| 9 | uSeafloorY 未设但 transparant: true | 警告 | 水面半透明但无海底 depth 可采样 → alpha 全为 1.0 → 透明设置无效 | 设 uSeafloorY 或在无海底场景中按 opaque 渲染 |

---

## 八、自检清单

- [ ] 水面用的是 Gerstner 波 vertex displacement（不是粒子）？
- [ ] 6 条波的方向散布在 ≥ 90° 范围内？
- [ ] choppiness ∈ [0, 1.0)，没有 > 1.0？
- [ ] 泡沫来自 Jacobian 折叠检测（不是单独噪声）？
- [ ] Fresnel 反射存在——水平看和俯视看不同？
- [ ] calm 映射了波幅/choppiness/泡沫/水色/清澈度/SSS？
- [ ] 三幕剧的情绪弧线清晰（风暴→风停→如镜）？
- [ ] 移动端降级了波数（6→3）和网格（256²→128²）？
- [ ] fogDensity ≤ 0.002 且 turbidity ≤ 12（雾不淹没水面）？
- [ ] 如需水下视角 → 已加载 **underwater-post.md**（EffectComposer + Beer-Lambert）？
- [ ] 如需浅滩透明 → uSeafloorY 已设且 scene 有海底 geometry？

---

## 九、交叉引用

- **水下后处理**：场景需要从水面上方下潜到水下 → `underwater-post.md`（EffectComposer depth pass + Beer-Lambert 体积吸收）。水面颜色（uDeepColor）必须与水下雾色（uFogColor）同源取值——否则下潜瞬间颜色突变。

### 9.1 水面↔水下自动切换（滞后检测）

当场景同时使用本文件（Gerstner 水面）和 `underwater-post.md`（水下后处理）时，需要统一的切换逻辑决定当前相机在水上还是水下。

**设计哲学**：继承自 threejs-environment-water-and-sky 的 `camera.position.y < water.position.y` 自动检测模式——但适配 Gerstner 波场景。波浪顶点位移导致瞬时水面 Y 不断变化——必须用平均水面 Y + 滞后阈值防止边界闪烁。

```javascript
// === 水面↔水下自动切换（放在 animate() 顶部，在更新水面/水下之前） ===

// 平均水面 Y — 不含 Gerstner 位移（即 oceanMesh.position.y）
const AVG_WATER_Y = 0.0;  // 与 ocean mesh 的 position.y 一致
const HYSTERESIS = 0.5;   // 滞后阈值（米）— 消除浪峰浪谷引起的闪烁

// 水下状态（闭包变量，初始化时根据相机位置设定）
let isUnderwater = camera.position.y < AVG_WATER_Y;

function updateSubmersionState(camera) {
  const camY = camera.position.y;
  
  // 滞后逻辑：下潜需要更深，上浮需要更高
  // → 相机在浪谷时不会误触发水下模式
  if (!isUnderwater && camY < AVG_WATER_Y - HYSTERESIS) {
    isUnderwater = true;
    // 可选：触发下潜音效（见 audio-engine.md §十一 瞬态触发）
  } else if (isUnderwater && camY > AVG_WATER_Y + HYSTERESIS) {
    isUnderwater = false;
    // 可选：触发浮出水面音效
  }
  
  return isUnderwater;
}

// 在 animate() 中：
// const underwater = updateSubmersionState(camera);
// underwaterPass.enabled = underwater;
// 
// 水下时同步更新：
// - underwaterPost uniforms（fogColor ← ocean.uDeepColor 同源）
// - ocean material uniforms（underwater flag → 调整 Fresnel/透明度）
// - 太阳/天空可见性（水下 → 隐藏或减弱）
```

**⚠️ 关键约束**：
1. `AVG_WATER_Y` 必须与 `oceanMesh.position.y` 一致——Gerstner 位移后的瞬时 Y 不可用于检测
2. `HYSTERESIS` 推荐值：平静水面 = 0.3，中等浪 = 0.5，风暴浪 = 1.0（浪越大，滞后越大——防止闪烁）
3. 水面颜色（`uDeepColor`）和水下雾色（`uFogColor`）必须是**同一个 `THREE.Color` 对象或同一组源值**——否则下潜瞬间颜色突变（外部 water-sky 的反模式 2）
4. 过渡区（AVG_WATER_Y ± HYSTERESIS 范围内）的状态保持不变——这是滞后的核心价值

**滞后原理**：想象相机在浪谷（-2.5m）。瞬时水面 Y 在 -0.8（浪谷）和 +1.2（浪峰）之间振荡。如果没有滞后，相机在每次浪峰经过时短暂"浮出水面"→ 画面闪烁。有了 0.5m 滞后：相机需要上升到 -0.5 + 0.5 = 0.0 以上才触发"浮出"，或下降到 -0.5 - 0.5 = -1.0 以下才触发"下潜"——浪谷的 -2.5m 持续触发"水下"，不受浪峰影响。

### 9.2 自检（追加到 §八）

- [ ] 如果同时加载了 underwater-post.md → `AVG_WATER_Y` 与 `oceanMesh.position.y` 一致？
- [ ] 滞后阈值是否匹配波浪振幅（HYSTERESIS ≥ 最大浪高 × 0.3）？
- [ ] `uDeepColor` 和 `uFogColor` 是否同源（同一个 Color 对象或同一组 RGB 值）？
- [ ] 相机在过渡区（±HYSTERESIS）是否不闪烁？
