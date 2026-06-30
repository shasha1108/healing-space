# 代码骨架参考

> 本文件是 SKILL.md 中提取的代码示例。SKILL.md 中保留原则声明和指针，具体代码骨架在此查阅。
> **加载方式**：按需翻阅对应章节，不需要读完。

---

## § 入场序列

三层错开序列骨架——背景 → 粒子 → 文字：

```javascript
const ENTRY = { BG: 0, PARTICLES: 0.5, TEXT: 1.0 }; // 各层延迟（秒）
let entryElapsed = 0;
function entrySequence(dt) {
  entryElapsed += dt;
  if (entryElapsed > ENTRY.BG) startBackgroundEntry(dt);
  if (entryElapsed > ENTRY.PARTICLES) startParticleEntry(dt);
  if (entryElapsed > ENTRY.TEXT) showIntroText();
}
```

---

## § Dolly Zoom 入场

相机从极远推近 + FOV 收窄，2-3 秒：

```javascript
// Dolly Zoom 入场示例
const entryDuration = 2.5; // 秒
let entryProgress = 0;

function entryDollyZoom(dt) {
    if (entryProgress >= 1) return;
    entryProgress = Math.min(1, entryProgress + dt / entryDuration);
    const t = easeInOutCubic(entryProgress);
    camera.position.z = 500 - 340 * t;    // 500 → 160
    camera.fov = 90 - 40 * t;             // 90° → 50°
    camera.updateProjectionMatrix();
}
function easeInOutCubic(x) { return x < 0.5 ? 4*x*x*x : 1-Math.pow(-2*x+2,3)/2; }
```

---

## § 字体系统

宋体系 + 字间距 10-15 + 字重 200：

```css
.title {
    font-size: clamp(20px, 4vw, 28px);   /* 不大，保持精致 */
    letter-spacing: 10px;                 /* 核心！拉开字间距 = 通透 */
    font-weight: 200;
}
.subtitle {
    font-size: clamp(12px, 2.4vw, 17px); /* = 标题 × 60% */
    letter-spacing: 10px;
    font-weight: 200;
    opacity: 0.65;
}
.hint {
    font-size: clamp(11px, 1.8vw, 14px);
    letter-spacing: 15px;                /* 提示文字间距最大 */
    opacity: 0.45;
}
```

> 字间距 10~15 是"高级感"和"普通"的分界线。拉开的字距让画面通透、安静、有留白——这正是疗愈类作品需要的呼吸感。

---

## § 光标系统

### 光标 CSS

```css
#spirit-cursor {
    position: fixed;
    width: 20px; height: 20px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(180,210,255,0.6) 40%, transparent 70%);
    mix-blend-mode: screen;
    pointer-events: none; z-index: 999;
    /* JS 驱动 transform，不用 left/top（性能更好） */
}
```

### 光标 Lerp 跟随

```javascript
// Lerp 平滑跟随——液态/悬浮的延迟感
const cursor = { x: 0, y: 0, targetX: 0, targetY: 0 };

document.addEventListener('mousemove', e => {
    cursor.targetX = e.clientX;
    cursor.targetY = e.clientY;
});

function updateCursor() {
    const lerpFactor = 0.12;  // 0.08=更悬浮, 0.2=更跟手
    cursor.x += (cursor.targetX - cursor.x) * lerpFactor;
    cursor.y += (cursor.targetY - cursor.y) * lerpFactor;
    spiritCursor.style.transform = `translate(${cursor.x - 10}px, ${cursor.y - 10}px)`;
}
```

> `lerpFactor = 0.08~0.15`：越小越像在水中、越大越跟手。移动端（<768px）隐藏自定义光标。

**光标变体（按隐喻选择）：**
- 发光光点（默认）：圆形 radial-gradient
- 空心圆环：`border: 1px solid rgba(255,255,255,0.5); background: transparent;` + 呼吸动画
- 粒子拖尾：每帧在光标位置 spawn 3~5 个小粒子，粒子自行衰减消失

### 双光标 Bug 修复

`cursor: none` 只设在 `body` 上，对 JS 动态插入的 `canvas`（position:fixed）在某些浏览器中不生效——导致系统光标和自定义光标同时可见。同时，自定义光标 div 初始在 `left:0, top:0`，在用户移动鼠标前已可见，等同于出现两个光标。三选一不够，三条必须同时做：

```css
/* 1. 全局强制隐藏系统光标（不仅是 body） */
* { cursor: none !important; }
```

```css
/* 2. 自定义光标初始不可见 */
#spirit-cursor { opacity: 0; }
```

```javascript
/* 3. 首次 mousemove 才显示并初始化位置 */
document.addEventListener('mousemove', e => {
  spiritCursor.style.opacity = '1';
  cursor.targetX = e.clientX;
  cursor.targetY = e.clientY;
}, { once: true });
```

---

## § Lerp 平滑

一切过渡都用 lerp，不用线性赋值：

```javascript
// 差：生硬
camera.position.z = targetZ;

// 好：有机
camera.position.z += (targetZ - camera.position.z) * 0.05;
```

应用位置：
- 光标跟随：`cursor += (target - cursor) * 0.12`
- 相机移动：`camera.z += (targetZ - camera.z) * 0.05`
- calm 过渡：`calm += (targetCalm - calm) * Math.min(1, dt * 1.5)`
- 颜色过渡：GPU 端 `mix(colFrom, colTo, smoothstep(calm))`——也是 lerp
- 音频参数：`gain.setTargetAtTime(target, ctx.currentTime, 0.1)`——内置指数平滑

---

## § 贝塞尔路径约束流（Structured Flow）

> **Always Lerp. Never linear.** 粒子不靠力场/噪声自由漂移，而是用贝塞尔曲线作为骨架——粒子沿骨架流动，法向偏移产生有机的"流束"厚度。

### 何时用路径约束流（而非力场/噪声）

| 隐喻特征 | 用路径约束流？ | 原因 |
|---------|-------------|------|
| 从固定源头喷发/升空（蒸汽、数据流、能量束） | ✅ 首选 | 贝塞尔骨架 = 看得见的"路" |
| 粒子需要形成明确的 S/C/J/弧线形状 | ✅ 首选 | 控制点直接决定曲线形态 |
| 粒子自由漂浮/弥漫/无方向性 | ❌ | 用力场粒子（particle-physics.md） |
| 粒子被风/气流/不可见力量带动 | ❌ | 用 Perlin 流场（p5-patterns.md §1） |
| 需要字符/文字作为粒子（数据/科技/表达隐喻） | ✅ 配合使用 | 字符渲染变体（见下方 §字符渲染变体） |

**路径约束流的本质：粒子不自己决定去哪——骨架曲线替它们决定了。** 这恰好符合"释放/升空/送出去"类情绪——不是失控的爆炸，也不是漫无目的的飘散，而是**沿着一条有方向的路，离开**。

### 核心组件一：Bézier 路径骨架

三次贝塞尔方程——4 个控制点定义一条曲线的完整形态：

```javascript
/**
 * 三次贝塞尔曲线 —— 4 个控制点定义任意 S/C/J/弧线
 * @param {number} t - 进度 0~1
 * @param {{x,y}[]} cp - 控制点数组 [p0, p1, p2, p3]
 *   p0: 起点（源头位置）
 *   p1: 出射方向控制（拉得越远曲线越"冲"）
 *   p2: 入射方向控制（拉得越远曲线越"卷"）
 *   p3: 终点（消散位置）
 */
function getBezierPoint(t, cp) {
  const mt = 1 - t;
  const mt2 = mt * mt, mt3 = mt2 * mt;
  const t2 = t * t, t3 = t2 * t;
  return {
    x: mt3 * cp[0].x + 3 * mt2 * t * cp[1].x + 3 * mt * t2 * cp[2].x + t3 * cp[3].x,
    y: mt3 * cp[0].y + 3 * mt2 * t * cp[1].y + 3 * mt * t2 * cp[2].y + t3 * cp[3].y,
  };
}
```

**控制点调参指南（决定曲线的情绪）：**

| 情绪方向 | p0（源头） | p1-p2 关系 | 曲线形态 | 视觉感受 |
|---------|-----------|-----------|---------|---------|
| 释放/升空 | 画面中下方 | 水平拉宽 + 垂直拉高 | S 型上升 | "从胸口升起来散掉" |
| 表达/输出 | 画面左侧 | 水平为主 | 横 C 弧线 | "把话说出去" |
| 坠落/坍塌 | 画面上方 | 垂直下压 | 倒 J 型 | "一切都在往下掉" |
| 回旋/不散 | 任意 | p1-p2 形成闭环趋势 | 螺旋 | "绕了一圈又回来" |

> S 型上升不是唯一答案——控制点就是情绪的形状。改 p1-p2 的位置和距离，就能改变整个流束的情感走向。

### 核心组件二：法向偏移 + 扩散控制

粒子不精准落在骨架上——在骨架曲线周围形成**有机厚度的流束**。偏移量包含两个部分：
1. **静态法向偏移**：每个粒子出生时随机分配，决定它在流束横截面上的"座位"
2. **动态蜿蜒偏移**：随时间正弦变化，模拟流体中的涡旋层次

```javascript
/**
 * 创建沿贝塞尔路径流动的粒子
 * @param {number} cw - 画布宽度
 * @param {number} ch - 画布高度
 * @param {object} opts
 * @param {number} opts.maxSpread - 终点最大扩散比（0.05~0.3，默认 0.15）
 *   小值 = 细束，大值 = 粗壮流束。⚠️ 超过 0.3 终点会散成雾
 * @param {number} opts.wobbleAmp - 蜿蜒幅度（默认 0.5）
 * @param {number} opts.wobbleFreq - 蜿蜒频率（默认 10）
 */
function createFlowParticle(cw, ch, opts = {}) {
  const { maxSpread = 0.15, wobbleAmp = 0.5, wobbleFreq = 10 } = opts;
  return {
    progress: Math.random() * 0.1, // 初始分散在路径起点附近
    speed: Math.random() * 0.003 + 0.002,
    // 静态法向偏移——决定粒子在流束横截面上的位置
    offsetX: (Math.random() - 0.5) * cw * maxSpread,
    offsetY: (Math.random() - 0.5) * ch * maxSpread,
    // 动态蜿蜒的相位——每个粒子不同，产生"流束中有涡旋"的层次感
    wobblePhase: Math.random() * Math.PI * 2,
  };
}

/**
 * 更新粒子蜿蜒偏移（每帧调用）
 * @param {object} p - 粒子对象
 * @param {number} time - 全局时间（秒），用于驱动蜿蜒
 */
function updateFlowParticle(p, time, opts = {}) {
  const { wobbleAmp = 0.5, wobbleFreq = 10 } = opts;
  p.progress += p.speed;
  // 正弦蜿蜒——不同粒子相位不同 = 多层缭绕
  p.offsetX += Math.sin(p.progress * wobbleFreq + p.wobblePhase + time) * wobbleAmp;
}

/**
 * 计算粒子在画布上的实际位置
 * @param {object} p - 粒子对象
 * @param {{x,y}[]} cp - 贝塞尔控制点
 * @param {function} spreadFn - 扩散曲线 t→spread，默认线性
 * @returns {{x,y,progress}|null} null 表示粒子已流出终点
 */
function getFlowParticlePos(p, cp, spreadFn = t => t * 1.5) {
  if (p.progress > 1) return null;
  const pos = getBezierPoint(Math.min(p.progress, 1), cp);
  const spread = spreadFn(p.progress);
  return {
    x: pos.x + p.offsetX * spread,
    y: pos.y + p.offsetY * spread,
    progress: p.progress,
  };
}
```

**扩散曲线选择（决定流束末端形态）：**

```javascript
// 线性扩散（默认）——流束均匀展开
const linearSpread = t => t * 1.5;

// 缓出扩散——前期收紧、末端快速散开（"升到顶才散去"）
const easeOutSpread = t => 1 - Math.pow(1 - t, 3);

// 钳制扩散——扩散有上限，不会散成雾
const clampedSpread = t => Math.min(t * 1.5, 1.2);
```

### 核心组件三：路径进度颜色插值

颜色沿路径进度插值——用**色标数组（color stops）**参数化，不硬编码具体颜色值：

> ⚠️ **函数命名**：这里命名为 `lerpPathColor` 而非 `lerpColor`。p5.js 内置了 `lerpColor(col1, col2, amt)` 函数（操作 p5.Color 对象），如果使用 p5.js 全局模式且函数重名，p5.js 会覆盖自定义函数导致运行时崩溃。**在 p5.js 环境下，永远用 `lerpPathColor` 这个前缀命名。**

```javascript
/**
 * 沿路径进度插值颜色
 * @param {number} t - 进度 0~1
 * @param {{t:number, r:number, g:number, b:number}[]} stops - 色标数组
 *   至少 2 个，t 值应在 0~1 范围内并按升序排列
 */
function lerpPathColor(t, stops) {
  let i = 0;
  while (i < stops.length - 2 && stops[i + 1].t < t) i++;
  const a = stops[i], b = stops[i + 1];
  const lt = (t - a.t) / (b.t - a.t);
  return {
    r: Math.round(a.r + (b.r - a.r) * lt),
    g: Math.round(a.g + (b.g - a.g) * lt),
    b: Math.round(a.b + (b.b - a.b) * lt),
  };
}
```

**预制色标组合（从 color-palettes.md 的 5 套疗愈色板中取色）：**

| 情绪方向 | stops 配置 | 视觉感受 |
|---------|-----------|---------|
| 数据释放/表达 | `[{t:0, r:255,g:204,b:0}, {t:0.5, r:255,g:68,b:136}, {t:1, r:217,g:38,b:76}]` | 黄→粉→绛红，"说出来的热度" |
| 宁静升空 | `[{t:0, r:180,g:210,b:255}, {t:0.5, r:140,g:180,b:230}, {t:1, r:200,g:220,b:245}]` | 浅蓝→灰蓝→珍珠白，"轻了" |
| 温暖愈合 | `[{t:0, r:255,g:220,b:180}, {t:0.5, r:255,g:200,b:150}, {t:1, r:240,g:230,b:210}]` | 暖杏→奶油→米白，"被捂热了" |

> 二段插值（2 stops）= 全路径均匀渐变。三段插值（3 stops）= 有中点转折（如"热→烫→冷却"）。stop 数越多颜色节奏越丰富。

### § 字符渲染变体（可选·⚠️ 仅数据/科技/表达隐喻）

**触发条件：仅当隐喻明确涉及"数据""信息""代码""文字""表达"时才启用字符渲染。** 自然隐喻（森林/海洋/呼吸/蒸汽）用光点渲染替代——`ctx.arc()` 比 `ctx.fillText()` 快 5-8 倍且不会产生审美冲突。

```javascript
const CHAR_POOL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

// 字符粒子——数据/科技/表达隐喻专用
function drawCharParticle(ctx, x, y, char, size, color, alpha) {
  ctx.fillStyle = `rgba(${color.r},${color.g},${color.b},${alpha})`;
  ctx.font = `bold ${size}px monospace`;
  ctx.fillText(char, x, y);
}

// 光点粒子——自然隐喻的默认选择
function drawDotParticle(ctx, x, y, size, color, alpha) {
  ctx.fillStyle = `rgba(${color.r},${color.g},${color.b},${alpha})`;
  ctx.beginPath();
  ctx.arc(x, y, size * 0.5, 0, Math.PI * 2);
  ctx.fill();
}
```

**尾部淡出（字符和光点通用）：**
```javascript
// 粒子在最后 20% 路径逐渐透明——不是突然消失，是"化开了"
const alpha = t > 0.8 ? (1 - t) * 5 : 1;
```

### 完整最小骨架（Canvas2D 版本）

```javascript
// === 贝塞尔路径约束流 —— 最小可运行骨架 ===
const cw = window.innerWidth, ch = window.innerHeight;

// ① 控制点（按隐喻调整——见上方"控制点调参指南"）
const cp = [
  { x: cw * 0.5, y: ch * 0.8 },   // p0: 源头
  { x: cw * 0.9, y: ch * 0.8 },   // p1: 出射方向
  { x: cw * 0.8, y: ch * 0.3 },   // p2: 入射方向
  { x: cw * 0.95, y: ch * 0.45 }, // p3: 终点
];

// ② 色标（从上方预制表中选一组）
const colorStops = [
  { t: 0, r: 255, g: 204, b: 0 },
  { t: 0.5, r: 255, g: 68, b: 136 },
  { t: 1, r: 217, g: 38, b: 76 },
];

// ③ 粒子池
const N = 80; // 字符粒子性能敏感——≤200（桌面）/ ≤80（移动端）
const USE_CHARS = true; // 改为 false = 降级为光点渲染
const particles = [];
for (let i = 0; i < N; i++) {
  const p = createFlowParticle(cw, ch, { maxSpread: 0.15 });
  if (USE_CHARS) {
    p.char = CHAR_POOL[Math.floor(Math.random() * CHAR_POOL.length)];
    p.size = Math.random() * 8 + 8;
  } else {
    p.size = Math.random() * 3 + 2;
  }
  particles.push(p);
}

// ④ 每帧
function drawFlow(time) {
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i];
    updateFlowParticle(p, time);
    const drawn = getFlowParticlePos(p, cp, linearSpread);
    if (!drawn) {
      // 粒子流出终点 → 重生在起点
      const fresh = createFlowParticle(cw, ch, { maxSpread: 0.15 });
      Object.assign(p, fresh);
      if (USE_CHARS) {
        p.char = CHAR_POOL[Math.floor(Math.random() * CHAR_POOL.length)];
        p.size = Math.random() * 8 + 8;
      }
      continue;
    }
    const color = lerpPathColor(drawn.progress, colorStops);
    const alpha = drawn.progress > 0.8 ? (1 - drawn.progress) * 5 : 1;
    if (USE_CHARS) {
      drawCharParticle(ctx, drawn.x, drawn.y, p.char, p.size, color, alpha);
    } else {
      drawDotParticle(ctx, drawn.x, drawn.y, p.size, color, alpha);
    }
  }
}
```

### 性能注意

| 项目 | 限制 | 原因 |
|------|------|------|
| 字符粒子数 | ≤ 200（桌面）/ ≤ 80（移动端） | `fillText()` 每帧触发字体光栅化，比 `arc()` 慢 5-8 倍 |
| 仅用 ASCII 字符 | A-Z / 0-9 / 基本标点 | 中文字体光栅化成本是 ASCII 的 20 倍以上，且移动端字体文件不完整 |
| 字体系列 | `monospace` | 等宽字体光栅化路径最短，且字符间视觉重量一致 |
| 光点粒子数 | ≤ 2000（桌面）/ ≤ 800（移动端） | 不渲染字符时大幅提升粒子上限 |
| `getBezierPoint()` | 每粒子每帧 1 次 | 三次贝塞尔仅 12 次乘加——极轻，不是瓶颈 |
| `lerpPathColor()` | 每可见粒子每帧 1 次 | 与粒子数成正比，三段色标比二段多一次判断——可忽略不计
