# 风系统数学模型 — 四组分风场 + 圆形弧线弯曲

> 设计哲学源自 stylized-scene (dedekpo) 的 GPU 风系统：阵风(gust) + 碎浪(chop) + 微风(breeze) + 尖端颤振(flutter) 的四层频率叠加，配合圆形弧线弯曲模型，产生"风吹过田野"的空间传播感而非"所有东西同时 sin 摆动"。
>
> 适配到 healing-space：**风不是装饰效果——风是疗愈隐喻的载体。** 狂风 = 焦虑峰值（Act 2 自动触发），微风 = 平静（Act 3 用户抚平），空间传播 = "这片情绪不是只在你身上，它在空间里真实存在"。
>
> **加载时机**：STEP 3.1 决策树选中"风/草地/户外自然"隐喻时按需加载。不是默认加载。
>
> **触发条件**：用户描述含"风吹过"、"草地在动"、"麦浪"、"暴风雨后平静"、"风吹散阴霾"、"风铃"、"wind"——或三幕剧隐喻涉及"外部力量扫过空间"（如他人的负面情绪像冷风吹过）。

---

## 目录

- [一、第一性原理：为什么简单 sin 摆动是错的](#一第一性原理为什么简单-sin-摆动是错的)
- [二、四组分风模型（技术无关）](#二四组分风模型技术无关)
- [三、圆形弧线弯曲模型](#三圆形弧线弯曲模型)
- [四、空间传播：相位 = 世界坐标的函数](#四空间传播相位--世界坐标的函数)
- [五、calm 总线 → 风参数映射](#五calm-总线--风参数映射)
- [六、三幕剧适配](#六三幕剧适配)
- [七、GLSL 实现骨架（Three.js / WebGL）](#七glsl-实现骨架threejs--webgl)
- [八、p5.js 实现骨架（2D 像素/有机线条）](#八p5js-实现骨架2d-像素有机线条)
- [九、TSL 实现骨架（WebGPU）](#九tsl-实现骨架webgpu)
- [十、与其他技术路线的兼容性](#十与其他技术路线的兼容性)
- [十一、反模式](#十一反模式)
- [十二、自检清单](#十二自检清单)

---

## 一、第一性原理：为什么简单 sin 摆动是错的

```
当前反模式（大多数风实现）：
  offset = sin(time * frequency) * amplitude
  → 所有东西同时、同方向、同幅度摆动
  → 这是"节拍器"，不是"风"

正确的风：
  offset(t, worldPosition, elementIndex) = 
    gust(t, worldX)        // 低频大振幅——阵风以波的形式扫过空间
  + chop(t, worldX)        // 中频中振幅——碎浪叠加在阵风上
  + breeze(t, elementIdx)  // 高频低振幅——每个元素的独立微颤
  + flutter(tip, t)        // 尖端局部高频——只影响末梢
```

**核心洞察**：风不是单一的周期性力——它是**不同空间尺度和时间尺度的叠加**。阵风(Gust)是"整个区域同时被一阵强风吹过"——低空间频率、高振幅、间歇性。碎浪(Chop)是"阵风中的细碎波动"——中空间频率、中振幅、连续。微风(Breeze)是"每个叶片/枝条自己的小幅随机摆动"——个别元素的高频微动。颤振(Flutter)是"尖端在风中快速抖动"——只影响末端、极高频率。

**如果只用一层 sin**：要么"看起来像所有东西在呼吸"（频率太低），要么"看起来像在发抖"（频率太高），要么"看起来像广播体操"（没有空间相位差）。

---

## 二、四组分风模型（技术无关）

以下公式用伪代码表示——独立于任何渲染 API。实现时适配到 GLSL / TSL / p5.js / CSS。

```javascript
/**
 * 四组分风模型 —— 每帧/每顶点/每元素计算
 * 
 * @param {number} t           — 全局时间（秒）
 * @param {number} worldX      — 元素的世界 X 坐标（决定空间相位）
 * @param {number} worldZ      — 元素的世界 Z 坐标（可选，3D 场景用）
 * @param {number} elementIdx  — 元素索引（决定逐元素相位偏移）
 * @param {number} heightT     — 归一化高度 0-1（0=根部，1=尖端；非细长元素传 0.5）
 * @param {object} params      — 风参数对象，见下方定义
 * @returns {number} offset    — 水平偏移量（世界单位或像素）
 */

// 风参数（默认值 — 对应 calm=0.5 的中等风）
const WIND_PARAMS = {
  strength:   0.25,  // 总风强 0-1 — 驱动所有振幅
  speed:      2.0,   // 风速 — 驱动所有频率
  angle:      45,    // 风向（度）— 决定偏移方向
  gustScale:  0.5,   // 阵风空间频率（越大=阵风越密）
  turbulence: 0.28,  // 逐元素摆动幅度（越大=每个元素越独立）
  flutter:    0.28,  // 尖端颤振幅度
};

function windOffset(t, worldX, worldZ, elementIdx, heightT, params) {
  const w = params;
  
  // === 风向分解 ===
  const angleRad = w.angle * Math.PI / 180;
  const windDirX = Math.cos(angleRad);
  const windDirZ = Math.sin(angleRad);  // 3D 场景用，2D 忽略
  
  // === 逐元素相位（确定性 hash） ===
  const bladePhase = hash(elementIdx) * Math.PI * 2;
  
  // === 逐元素振幅变化（每个元素刚度不同） ===
  const ampVar = 0.65 + hash(elementIdx + 7) * 0.7;  // 范围 0.65-1.35
  
  // === 组分 1：微风（Breeze）—— 逐元素独立高频微颤 ===
  // 频率高、振幅低、每个元素相位独立
  const breezeFreq = w.speed * 0.6;
  const breeze = Math.sin(t * breezeFreq + bladePhase) * w.turbulence * 0.4;
  
  // 风向在基础角度周围缓慢摆动
  const wobbleAngle = angleRad + breeze;
  const wobbleDirX = Math.cos(wobbleAngle);
  const wobbleDirZ = Math.sin(wobbleAngle);
  
  // === 沿风向的投影坐标（决定阵风和碎浪的相位） ===
  const along = worldX * wobbleDirX + worldZ * wobbleDirZ;
  
  // === 噪声抖动——让波前不规则 ===
  // 采样低频噪声在元素的世界位置——每个元素有微小相位偏移
  const noiseJitter = (sampleNoise(worldX * 0.03, worldZ * 0.03) - 0.5) * 2.0;
  
  // === 组分 2：阵风（Gust）—— 低频大振幅空间传播波 ===
  // 相位 = 空间位置 + 时间 + 噪声扰动
  const gustPhase = along * w.gustScale - t * w.speed * 0.6 + noiseJitter * 1.5;
  // 原始 sin → [0,1] → pow 1.6 锐化（间歇性：强风短，平静长）
  let gust = Math.sin(gustPhase) * 0.5 + 0.5;  // [0, 1]
  gust = Math.pow(gust, 1.6);                   // 锐化——峰值更尖
  
  // === 组分 3：碎浪（Chop）—— 中频中振幅快速连续波 ===
  // 空间频率是阵风的 2.7 倍，时间频率是 1.3 倍
  const chopPhase = along * w.gustScale * 2.7 - t * w.speed * 1.3 + bladePhase;
  const chop = Math.sin(chopPhase) * 0.5 + 0.5;  // [0, 1]
  
  // === 合成为总强度 ===
  // 0.25 是地板——永远有微风，不会完全静止
  const intensity = (0.25 + gust * 0.85 + chop * 0.18) * ampVar;
  
  // === 圆形弧线弯曲（见 §三） ===
  const phi = clamp(w.strength * intensity * 3.0, 0, 1.6);   // 弯曲角 ≤ ~90°
  const bendExponent = 1.5;                                    // 弯曲曲线形状
  const a = phi * Math.pow(heightT, bendExponent);             // 此高度的弯曲角
  const safePhi = Math.max(phi, 0.001);
  const R = 1.0 / safePhi;                                     // 归一化弧线半径
  const u = R * (1 - Math.cos(a));                             // 水平位移
  const dv = R * Math.sin(a) - heightT;                         // 垂直下垂
  
  // === 组分 4：尖端颤振（Flutter）—— 只影响上半部分 ===
  const flutterMask = heightT < 0.55 ? 0 : (heightT - 0.55) / 0.45;  // smoothstep 近似
  const flutterPhase = t * 10.0 + bladePhase * 3 + along * 0.8;
  const flutterAmt = Math.sin(flutterPhase) * w.flutter * 0.08 * flutterMask;
  
  // === 最终水平偏移 ===
  // 主偏移沿风向，颤振垂直于风向
  const mainOffset = u;                                          // 沿风向
  const flutterOffset = flutterAmt;                              // 垂直风向（简化用同方向）
  
  return {
    offsetX: wobbleDirX * mainOffset + wobbleDirZ * flutterOffset,
    offsetY: dv,                                                 // 垂直下垂（3D 用）
    offsetZ: wobbleDirZ * mainOffset - wobbleDirX * flutterOffset,
  };
}

function clamp(v, min, max) { return v < min ? min : v > max ? max : v; }
```

**四个组分的关键差异**：

| 组分 | 空间频率 | 时间频率 | 振幅占比 | 视觉感受 |
|------|---------|---------|---------|---------|
| 阵风 (Gust) | 低（整个区域） | 低 | ~85% | "一阵强风扫过"——间歇性、有方向 |
| 碎浪 (Chop) | 中（~3× 阵风） | 中（~2× 阵风） | ~18% | "强风中的细碎波动"——连续、快速 |
| 微风 (Breeze) | 逐元素独立 | 低 | 地板 25% | "永远有轻微的风"——稳定基线 |
| 颤振 (Flutter) | 尖端局部 | 极高（~10Hz） | ~8% | "叶片边缘在抖"——只影响末梢 |

**为什么是这四个组分而不是三个或五个？**

从第一性原理：自然风有三个可感知的时空尺度。(1) 宏观尺度——你看到一片麦田被风吹过，波形以秒为单位传播——这是 Gust。(2) 中观尺度——在阵风内部，有更细碎、更快的波动——这是 Chop。(3) 微观尺度——每片叶子、每根草各自在轻微抖动，彼此不同——这是 Breeze + Flutter 的分工（Breeze 是全身微动，Flutter 是尖端特化）。

少于四个组分 → 缺少一个时空尺度 → 看起来不自然。多于四个组分 → 边际收益递减，增加计算成本但视觉改善不可感知。

---

## 三、圆形弧线弯曲模型

**为什么不是线性弯曲？**

线性弯曲：`offsetX = sin(angle) * heightT * amplitude`
→ 物体绕根部倾斜——这是"刚体旋转"，不是"弯曲"。

圆形弧线弯曲：物体沿弧线弯曲，根部不动，尖端弯曲最大，中间部分走真正的弧线。
→ 这是"弹性弯曲"——物理上更接近真实草叶/树枝的弯曲行为。

```
几何关系（横截面）：

  根部 (y=0) → 不动
  尖端 (y=height) → 弯曲角 phi，沿弧线移动到 (u, dv)
  
  R = height / phi          ← 弧线半径（phi 越大、半径越小、弯曲越厉害）
  u = R * (1 - cos(phi))    ← 水平位移（尖端）
  dv = R * sin(phi) - height ← 垂直下垂（尖端在弯曲后比原来矮）
  
  中间点 (heightT = y/height, [0,1])：
  a = phi * heightT^bendExponent  ← bendExponent 控制弯曲曲线形状
  u_t = R * (1 - cos(a))          ← 此高度的水平位移
  dv_t = R * sin(a) - y          ← 此高度的垂直下垂
```

**bendExponent 的作用**：
- `bendExponent = 1.0`：线性弯曲——弯曲角随高度线性增加
- `bendExponent = 1.5`（推荐）：大部分弯曲集中在顶部 1/3——底部挺直，顶部弯曲
- `bendExponent = 2.0`：极端——只有顶部弯曲，底部几乎不动

**为什么推荐 1.5？**

真实草叶的弯曲模式：叶片基部（靠近土壤的部分）几乎不动——它被周围叶片支撑。叶片上半部分（暴露在风中）才是弯曲的主要区域。`bendExponent = 1.5` 精确模拟这种"底部挺直、顶部弯曲"的行为。

---

## 四、空间传播：相位 = 世界坐标的函数

**这是让"风"变成"阵风扫过田野"的关键——不是"所有东西同时以相同相位摆动"。**

```
核心公式：
  along = worldX * cos(windAngle) + worldZ * sin(windAngle)
  gustPhase = along * gustScale - time * windSpeed * 0.6 + noiseJitter * 1.5
  
这意味着：
  - 两个元素如果有相同的 along 值（在同一条垂直于风向的线上）→ 相位相同 → 同步摆动
  - 两个元素如果 along 值相差 π/gustScale → 相位差 π → 完全反向（一个弯左，一个弯右）
  - 阵风以速度 (windSpeed * 0.6 / gustScale) 沿地面传播
```

**在实践中的应用**（各技术路线）：

| 技术栈 | 如何获取 worldX/worldZ |
|--------|----------------------|
| Three.js InstancedMesh | 通过 `InstancedBufferAttribute` 传入 `aOrigin`（逐实例世界 XZ） |
| Three.js 普通 Mesh | 直接用 `positionWorld.xz` |
| p5.js (2D) | 元素的画布坐标 `x` 即 `worldX`，`worldZ` 可忽略或用 `y` |
| GLSL (vertex shader) | uniform 或 attribute 传入 |
| CSS | 元素的 `left` 值映射为 `worldX` |

**GPU 实例化的特殊处理（重要）**：

Three.js `InstancedMesh` 中 `positionWorld` 塌缩为所有实例的共享值（因为 GPU 不知道每个实例的独立世界位置）。**必须**通过 `InstancedBufferAttribute` 为每个实例传入其世界 XZ 坐标——这就是 stylized-scene 中 `aOrigin` 和 `aFacing` 的用途。

---

## 五、calm 总线 → 风参数映射

风参数不是独立的——它们从 calm 值派生，确保风随疗愈进程平滑变化。

```
calm 0（压抑态）→ 狂风肆虐、碎浪频繁、尖端剧烈颤振
calm 1（治愈态）→ 轻柔微风、几乎静止、只有呼吸般的微动
```

| 风参数 | calm=0（焦虑峰值） | calm=1（治愈终态） | 映射公式 |
|--------|-------------------|-------------------|---------|
| `strength` | 0.45 | 0.05 | `0.45 - 0.40 * ts` |
| `speed` | 3.5 | 0.8 | `3.5 - 2.7 * ts` |
| `gustScale` | 0.8 | 0.2 | `0.8 - 0.6 * ts` |
| `turbulence` | 0.5 | 0.05 | `0.5 - 0.45 * ts` |
| `flutter` | 0.45 | 0.03 | `0.45 - 0.42 * ts` |

其中 `ts = calm * calm * (3 - 2 * calm)`（smoothstep 缓动），保证过渡不线性。

**映射原理**：
- `strength` 和 `speed` 同时降——风从"猛烈"变为"轻柔"。只降 strength 不降 speed = 快速小幅度摆动 = 看起来"紧张"而非"平静"
- `gustScale` 降——阵风从密集变为稀疏，治愈态几乎没有阵风
- `turbulence` 降——逐元素独立摆动减少，元素趋于同步（平静的微风是一致的，不是混乱的）
- `flutter` 降得最快——尖端颤振是"焦虑"最敏感的视觉信号

---

## 六、三幕剧适配

```
Act 1（美好展示 · 3-5 秒）：
  风参数 = calm 1.0 的配方（轻柔微风）
  相机 Dolly Zoom 入场，草叶/树枝在微风中缓慢摇摆
  → "一切都很好"——用户沉浸在宁静中
  
Act 2（突然破坏 · 自动发生，无需用户操作）：
  风参数在 1.5 秒内从 calm 1.0 过渡到 calm 0.0
  风突然狂暴——阵风频率增加、碎浪剧烈、尖端疯狂颤振
  视觉上：草叶被吹弯到接近 90°、树冠剧烈摇晃
  音频上：风噪从无到有（棕噪声增益从 0 到 0.08）
  → "不请自来的入侵"——对应焦虑/压力的突然到来
  
Act 3（亲手修复 · 用户交互驱动）：
  用户每次交互（擦拭/长按/抚摸）→ calm 从 0 向 1 推进
  风随 calm 平滑减弱——不是瞬间停止，是暴风雨逐渐过去
  当 calm > 0.95 → 触发视觉高潮：所有草叶同时回到直立位 + 金句淡入
  → "亲手把风暴抚平"——从失控走向掌控
```

**关键设计决策**：Act 2 的破坏是"风自动变狂暴"——模拟真实的情绪入侵（不请自来、无法预料）。Act 3 的修复是"用户交互减弱风"——长按/抚摸 = 安抚风暴 = 安抚自己的情绪。

---

## 七、GLSL 实现骨架（Three.js / WebGL）

```glsl
// === 确定性 hash 函数（GPU 友好） ===
float hash(float n) {
  return fract(sin(n) * 43758.5453123);
}

// === 噪声采样（从噪声纹理读取） ===
// noiseMap: 2D 纹理，R 通道为 Perlin/Simplex 噪声

// === 四组分风偏移计算 ===
// 在 vertex shader 中调用，传入逐实例的 worldOrigin.xy
vec3 windOffset(
  vec3 localPos,        // 模型局部坐标
  vec2 worldOrigin,     // 实例的世界 XZ（从 InstancedBufferAttribute 读取）
  float instanceIndex,  // 实例索引
  float baseY,          // 根部 Y 坐标
  float height,         // 叶片总高度
  float time,           // 全局时间
  sampler2D noiseMap,   // 噪声纹理
  // --- 风参数（uniforms，由 calm 总线驱动） ---
  float strength,
  float speed,
  float angle,
  float gustScale,
  float turbulence,
  float flutter
) {
  // 归一化高度
  float heightT = clamp((localPos.y - baseY) / max(height, 0.001), 0.0, 1.0);
  
  // 逐实例相位
  float bladePhase = hash(instanceIndex) * 6.28318;
  float ampVar = 0.65 + hash(instanceIndex + 7.0) * 0.7;
  
  // 风向
  float angleRad = angle * 3.14159 / 180.0;
  
  // 微风：逐元素风向摆动
  float wobble = sin(time * speed * 0.6 + bladePhase) * turbulence * 0.4;
  float wobbleAngle = angleRad + wobble;
  vec2 windDir = vec2(cos(wobbleAngle), sin(wobbleAngle));
  vec2 perpDir = vec2(-windDir.y, windDir.x);
  
  // 沿风向投影
  float along = dot(worldOrigin, windDir);
  
  // 噪声抖动
  float noiseJitter = (texture2D(noiseMap, worldOrigin * 0.03).r - 0.5) * 2.0;
  
  // 阵风
  float gustPhase = along * gustScale - time * speed * 0.6 + noiseJitter * 1.5;
  float gust = pow(sin(gustPhase) * 0.5 + 0.5, 1.6);
  
  // 碎浪
  float chopPhase = along * gustScale * 2.7 - time * speed * 1.3 + bladePhase;
  float chop = sin(chopPhase) * 0.5 + 0.5;
  
  // 总强度
  float intensity = (0.25 + gust * 0.85 + chop * 0.18) * ampVar;
  
  // 圆形弧线弯曲
  float phi = clamp(strength * intensity * 3.0, 0.0, 1.6);
  float bendExp = 1.5;
  float a = phi * pow(heightT, bendExp);
  float safePhi = max(phi, 0.001);
  float R = height / safePhi;
  float u = R * (1.0 - cos(a));
  float dv = R * sin(a) - (localPos.y - baseY);
  
  // 尖端颤振
  float flutterMask = smoothstep(0.55, 1.0, heightT);
  float flutterPhase = time * 10.0 + bladePhase * 3.0 + along * 0.8;
  float flutterAmt = sin(flutterPhase) * flutter * 0.08 * flutterMask;
  
  // 最终偏移
  return vec3(
    windDir.x * u + perpDir.x * flutterAmt,
    dv,
    windDir.y * u + perpDir.y * flutterAmt
  );
}
```

---

## 八、p5.js 实现骨架（2D 像素/有机线条）

```javascript
// === 确定性 hash ===
function hash(n) {
  const x = Math.sin(n) * 43758.5453123;
  return x - Math.floor(x);
}

// === 四组分 2D 风偏移（p5.js 像素或曲线用） ===
// 返回水平偏移量（像素单位）
function windOffset2D(x, y, elemIdx, heightT, time, params, noiseOffsets) {
  const w = params;
  const bladePhase = hash(elemIdx) * TWO_PI;
  const ampVar = 0.65 + hash(elemIdx + 7) * 0.7;
  const angleRad = w.angle * PI / 180;
  
  // 微风摆动
  const wobble = sin(time * w.speed * 0.6 + bladePhase) * w.turbulence * 0.4;
  const wobbleAngle = angleRad + wobble;
  
  // 沿风向投影（2D 只用 x 坐标）
  const along = x * cos(wobbleAngle);
  
  // 噪声抖动 — p5.js 用 noise()
  const nx = x * 0.03 + (noiseOffsets ? noiseOffsets[0] : 0);
  const ny = y * 0.03 + (noiseOffsets ? noiseOffsets[1] : 0);
  const noiseJitter = (noise(nx, ny) - 0.5) * 2.0;
  
  // 阵风
  const gustPhase = along * w.gustScale - time * w.speed * 0.6 + noiseJitter * 1.5;
  const gust = pow(sin(gustPhase) * 0.5 + 0.5, 1.6);
  
  // 碎浪
  const chopPhase = along * w.gustScale * 2.7 - time * w.speed * 1.3 + bladePhase;
  const chop = sin(chopPhase) * 0.5 + 0.5;
  
  // 总强度
  const intensity = (0.25 + gust * 0.85 + chop * 0.18) * ampVar;
  const phi = constrain(w.strength * intensity * 3.0, 0, 1.6);
  
  // 简化的 2D 弧线弯曲（无 Z 轴，无垂直下垂——2D 侧视图不需要 dv）
  const bendExp = 1.5;
  const a = phi * pow(heightT, bendExp);
  const safePhi = max(phi, 0.001);
  const R = 1.0 / safePhi;
  const u = R * (1 - cos(a));
  
  // 尖端颤振
  const flutterMask = heightT < 0.55 ? 0 : (heightT - 0.55) / 0.45;
  const flutterPhase = time * 10.0 + bladePhase * 3 + along * 0.8;
  const flutterAmt = sin(flutterPhase) * w.flutter * 0.08 * flutterMask;
  
  return cos(wobbleAngle) * u + sin(wobbleAngle) * flutterAmt;
}

// 使用示例：每帧更新多个植物的风偏移
function updateWindForPlants(plants, time, windParams) {
  for (const p of plants) {
    // p.x: 植物世界 X 坐标（决定空间相位）
    // p.idx: 植物索引（决定逐植物相位）
    // 主干：heightT=0.5（取中间高度）
    p.trunkOffset = windOffset2D(p.x, p.y, p.idx, 0.5, time, windParams, p.noiseOffsets);
    // 树冠：heightT=0.85（取顶部）
    p.canopyOffset = windOffset2D(p.x, p.y, p.idx + 1000, 0.85, time, windParams, p.noiseOffsets);
  }
}
```

---

## 九、TSL 实现骨架（WebGPU）

TSL（Three.js Shading Language）版本——用于 `MeshStandardNodeMaterial` 的 `positionNode`：

```javascript
import {
  clamp, cos, float, hash, instanceIndex, max, pow,
  positionLocal, sin, smoothstep, texture as tslTexture, time, vec2, vec3
} from 'three/tsl';

export function windSwayOffset({
  baseY, height, origin, windStrength, windSpeed, windAngle,
  gustScale, turbulence, flutter, noiseMap,
  facing,           // 可选：逐实例朝向 (cosY, sinY)
  phase = float(0),
  bendExponent = 1.5,
  clusterScale = 0.0,  // >0 = 从噪声纹理采样簇相位（合并网格用）
  canopyLean = 0.0,    // 额外静态倾斜（树冠用）
  amplitude = 1.0,
}) {
  const t = clamp(positionLocal.y.sub(baseY).div(height), 0, 1);
  const bladeSeed = hash(instanceIndex);

  // 簇相位（合并网格时，不同区域有不同相位）
  const clusterPhase = clusterScale > 0
    ? tslTexture(noiseMap, positionLocal.xz.mul(clusterScale).add(0.5)).r.mul(6.28318)
    : float(0);

  const bladePhase = bladeSeed.mul(6.28318).add(phase).add(clusterPhase);
  const ampVar = float(0.65).add(hash(instanceIndex.add(7.0)).mul(0.7));

  const baseAngle = windAngle.mul(Math.PI / 180);
  const wobble = sin(time.mul(windSpeed).mul(0.6).add(bladePhase))
    .mul(turbulence).mul(0.4);
  const angle = baseAngle.add(wobble);
  const windDir = vec2(cos(angle), sin(angle));
  const perpDir = vec2(windDir.y.negate(), windDir.x);

  const along = origin.dot(windDir);
  const noiseJitter = tslTexture(noiseMap, origin.mul(0.03)).r.sub(0.5).mul(2.0);

  const gustPhase = along.mul(gustScale).sub(time.mul(windSpeed).mul(0.6))
    .add(noiseJitter.mul(1.5));
  const gust = pow(sin(gustPhase).mul(0.5).add(0.5), float(1.6));

  const chopPhase = along.mul(gustScale.mul(2.7))
    .sub(time.mul(windSpeed).mul(1.3)).add(bladePhase);
  const chop = sin(chopPhase).mul(0.5).add(0.5);

  const intensity = float(0.25).add(gust.mul(0.85)).add(chop.mul(0.18)).mul(ampVar);
  const BEND_GAIN = 3.0;
  const phi = clamp(
    windStrength.mul(intensity).mul(BEND_GAIN).mul(amplitude).add(canopyLean),
    0, 1.6
  );

  const shaped = pow(t, bendExponent);
  const a = phi.mul(shaped);
  const safePhi = max(phi, float(1e-3));
  const R = float(height).div(safePhi);
  const u = R.mul(float(1).sub(cos(a)));
  const dv = R.mul(sin(a)).sub(positionLocal.y.sub(baseY));

  const flutterMask = smoothstep(0.55, 1.0, t);
  const flutterPhase = time.mul(10.0).add(bladePhase.mul(3)).add(along.mul(0.8));
  const flutterAmt = sin(flutterPhase).mul(flutter).mul(0.08).mul(flutterMask);

  const horiz = windDir.mul(u).add(perpDir.mul(flutterAmt));

  if (facing) {
    const cosY = facing.x;
    const sinY = facing.y;
    const localX = horiz.x.mul(cosY).sub(horiz.y.mul(sinY));
    const localZ = horiz.x.mul(sinY).add(horiz.y.mul(cosY));
    return vec3(localX, dv, localZ);
  }

  return vec3(horiz.x, dv, horiz.y);
}
```

> 此 TSL 实现直接来自 stylized-scene (MIT License)，适配为 healing-space 可用的代码骨架。完整上下文见该项目的 `src/materials/wind.ts`。

---

## 十、与其他技术路线的兼容性

| 技术路线 | 是否兼容风系统 | 适配方式 |
|---------|--------------|---------|
| Three.js 粒子 | 部分（粒子无"弯曲"概念） | 仅用四组分强度驱动粒子速度和方向——粒子被风吹动而非弯曲 |
| FBO 流体 | ❌ 不兼容 | 流体有自己的动力学——风和流体是两种不同的物理隐喻，不要混用 |
| p5.js 有机曲线 | ✅ 完全兼容 | 用 §八 的 2D 偏移公式，作用于曲线顶点 |
| CSS 元素 | ⚠️ 有限兼容 | 仅用阵风组分驱动 `translateX`，其余组分在 CSS 中无法表达 |
| Reaction-Diffusion | ❌ 不兼容 | RD 的图案由反应参数决定——"风"在 RD 中没有物理意义 |
| Raymarching SDF | ✅ 兼容 | 在 `map()` 函数中应用 §七 的偏移公式到采样点位置 |
| Gerstner 波 (ocean) | ❌ 不要叠加 | 水面波动由 Gerstner 波驱动——在上面再加风偏移会导致双重位移 |

**关键原则：风系统是"细长弹性元素的弯曲"模型。不要把它用在"粒子被推动"或"流体流动"上——那些有不同的物理模型。**

---

## 十一、反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | 单一 sin 摆动 | 致命 | 所有元素同步同向摆动——广播体操 | 使用四组分模型（§二） |
| 2 | 无空间相位差 | 致命 | 所有元素同一相位——塑料假草 | `along = dot(worldOrigin, windDir)` 计算空间相位（§四） |
| 3 | 线性弯曲 | 警告 | `offset = sin(time) * heightT`——刚体旋转 | 使用圆形弧线弯曲（§三） |
| 4 | 忽略逐元素振幅变异 | 警告 | 所有元素弯曲相同幅度——克隆人 | `ampVar = 0.65 + hash(idx+7) * 0.7`（§二） |
| 5 | 风参数不随 calm 变化 | 警告 | Act 2 狂风 → Act 3 仍然狂风——叙事断裂 | 所有风参数从 calm 派生（§五） |
| 6 | 在粒子上应用弧线弯曲 | 致命 | 粒子沿弧线移动而非被力推动——物理错误 | 粒子用 `force += windDir * intensity`，不是弧线 |
| 7 | GPU instancing 无逐实例 origin | 致命 | `positionWorld` 塌缩为共享值——30K 叶片全同步 | 必须用 `InstancedBufferAttribute` 传入逐实例 XZ（§四） |
| 8 | 颤振作用于全高度 | 警告 | 根部也在高频抖动——看起来像"整棵草在震动" | `flutterMask = smoothstep(0.55, 1.0, heightT)`（§二） |

---

## 十二、自检清单

- [ ] 隐喻是否涉及风/草地/户外自然？（不涉及 → 不加载本文件）
- [ ] 四组分（阵风/碎浪/微风/颤振）是否都已实现？
- [ ] 空间相位是否通过 `along = dot(worldOrigin, windDir)` 计算（不是全局统一相位）？
- [ ] 是否使用了圆形弧线弯曲（不是线性 `sin * heightT`）？
- [ ] 逐元素振幅变异（`ampVar = 0.65 + hash(idx+7) * 0.7`）是否已应用？
- [ ] 颤振是否只作用于 `heightT > 0.55` 的部分？
- [ ] 所有风参数是否通过 calm 总线派生（§五映射公式）？
- [ ] 三幕剧是否覆盖：Act 1 微风 → Act 2 狂风（自动）→ Act 3 用户抚平风（交互）？
- [ ] 如果是 GPU instancing → 是否有 `InstancedBufferAttribute` 传入逐实例 origin？
- [ ] 如果是粒子系统 → 是否用的是 `force += windDir * intensity` 而非弧线公式？
- [ ] 是否没有在 FBO 流体或 Gerstner 波上叠加风？（不应叠加）
- [ ] 是否没有在非细长元素（球形/方块）上使用弧线弯曲？
