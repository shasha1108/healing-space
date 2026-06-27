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
