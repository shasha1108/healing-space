# CSS Aesthetic — 非 WebGL 纯 CSS/GSAP 疗愈美学武器库

本文件覆盖**不用 Three.js** 的疗愈 H5 技法。当作品不需要 3D 粒子，而适合用 CSS 动画、DOM 元素、GSAP 时间线来表达时，参考此文件。

## 目录

- [一、CRT 复古终端美学](#一crt-复古终端美学)
- [二、GSAP 爆发动画](#二gsap-爆发动画)
- [三、卡片布局（非全屏）](#三卡片布局非全屏)
- [四、定制光标 + 光环](#四定制光标--光环)
- [五、噪点/纸纹叠加变体](#五噪点纸纹叠加变体)
- [六、印章元素](#六印章元素)

---

## 一、CRT 复古终端美学

适用于"过度思考""信息过载""焦虑"类主题。

### 扫描线

```css
.scanlines {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background:
        linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%),
        linear-gradient(90deg, rgba(255,0,0,0.06), rgba(0,255,0,0.02), rgba(0,0,255,0.06));
    background-size: 100% 4px, 3px 100%;
    z-index: 5; pointer-events: none;
    opacity: 0.6;
}
```

`background-size: 100% 4px` = 水平扫描线每 4px 一条。`3px 100%` = 垂直 RGB 子像素条纹每 3px 一条。

### CRT 闪烁

```css
@keyframes flicker {
    0%   { filter: brightness(0.8) contrast(1.2) hue-rotate(0deg); }
    50%  { filter: brightness(0.9) contrast(1.5) hue-rotate(2deg); }
    100% { filter: brightness(0.7) contrast(1.1) hue-rotate(-1deg); }
}
.crt-frame:not(.is-holding) {
    animation: flicker 0.15s infinite;
}
```

### 四角压暗（Vignette）

```css
.vignette {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    box-shadow: inset 0 0 150px rgba(0,0,0,0.9);
    z-index: 15; pointer-events: none;
}
```

> `box-shadow: inset` 比伪元素 + `radial-gradient` 更简洁，且不挡交互（`pointer-events: none`）。

---

## 二、GSAP 爆发动画

GSAP 的 `stagger` + `blur` 组合可以制造"所有念头炸碎消散"的戏剧性瞬间：

```javascript
// 炸碎所有 DOM 元素
gsap.to(elements, {
    opacity: 0,
    scale: 2.5,
    filter: "blur(15px)",
    y: () => (Math.random() - 0.5) * 200,
    x: () => (Math.random() - 0.5) * 200,
    duration: 0.6,
    stagger: 0.005,          // 每个元素延迟 5ms——产生"波"的感觉
    ease: "power3.out",
    onComplete: () => { container.innerHTML = ''; }
});
```

> `y: () => ...` 使用函数返回值——GSAP 对每个元素调用一次，产生随机方向弹飞的效果。

### 元素入场（打字机/终端弹窗感）

```javascript
gsap.fromTo(box,
    { opacity: 0, scale: 0.8, y: 10 },
    { opacity: 0.7, scale: 1, y: 0, duration: 0.2, ease: "back.out(1.5)" }
);
```

> `back.out(1.5)` 产生过冲回弹——数字终端弹窗的"咔"一声感。

### 定时自动触发

```javascript
// 10 秒后自动触发疗愈转折
setTimeout(triggerHealing, 10000);
```

### DOM 自清理（防泄漏）

```javascript
// 每 120ms 新生一个元素，超过 45 个时删除最早的一个
function spawn() {
    // ... create DOM element ...
    if (container.children.length > 45) {
        container.removeChild(container.firstChild);
    }
}
setInterval(spawn, 120);
```

---

## 三、卡片布局（非全屏）

不是所有疗愈作品都该全屏。手机卡片模式更贴合"私密空间"感：

```css
body {
    background: #020202;
    display: flex; justify-content: center; align-items: center;
    min-height: 100dvh;
}

.card-frame {
    position: relative;
    width: 100%; max-width: 540px;
    aspect-ratio: 3 / 4;
    max-height: 90vh;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 0 80px rgba(0,0,0,1);
    cursor: pointer;
}
```

> `aspect-ratio: 3/4` + `max-height: 90vh` 保证竖屏手机完美适配。"画框"感 + 黑色背景让体验像在看一幅会动的画。

---

## 四、定制光标 + 光环

增强交互的"仪式感"——光标变成一个发光的球体，按压时放大变色：

```css
#spirit-cursor {
    position: fixed;
    width: 24px; height: 24px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,1) 0%, rgba(100,200,255,0.8) 40%, transparent 70%);
    mix-blend-mode: screen;
    pointer-events: none;
    z-index: 100;
    transform: translate(-50%, -50%);
}

#spirit-halo {
    position: fixed;
    width: 48px; height: 48px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.2);
    pointer-events: none;
    z-index: 99;
    transform: translate(-50%, -50%);
    animation: breathe 4s infinite ease-in-out;
}

@keyframes breathe {
    0%,100% { transform: translate(-50%,-50%) scale(0.8); opacity:0.2; }
    50%    { transform: translate(-50%,-50%) scale(1.2); opacity:0.5; }
}
```

```javascript
// JS 驱动光标跟随 + 按压态变化
document.addEventListener('mousemove', e => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top  = e.clientY + 'px';
    halo.style.left   = e.clientX + 'px';
    halo.style.top    = e.clientY + 'px';
});

function onPressStart() {
    cursor.style.width = '40px'; cursor.style.height = '40px';
    cursor.style.background = 'radial-gradient(circle, #fff 0%, rgba(255,215,0,0.8) 40%, transparent 70%)';
    halo.style.borderColor = 'rgba(255,215,0,0.5)';
}
```

> 移动端隐藏（`if(window.innerWidth < 768) return`）——触屏没有光标概念。

---

## 五、噪点/纸纹叠加变体

### 暗色背景 + overlay（默认）

```css
.noise-overlay {
    background-image: url("data:image/svg+xml,...");
    mix-blend-mode: overlay;
    opacity: 0.04;
}
```

### 亮色纸纹 + multiply（宣纸/水墨）

```css
.paper-texture {
    background-image: url("data:image/svg+xml,...");
    mix-blend-mode: multiply;
    opacity: 0.35;
}
```

> `multiply` 在亮背景上模拟宣纸纤维感；`overlay` 在暗背景上增加胶片颗粒。选择取决于背景色。

---

## 六、印章元素

传统中国画常配印章，CSS 可以做一个极简的：

```css
.seal {
    width: 30px; height: 30px;
    border: 2px solid #8B0000;
    color: #8B0000;
    font-size: 10px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 4px;
    font-family: 'KaiTi', serif;
}
```

---

## 速查：主题 → CSS 技法

| 主题方向 | 推荐技法 | 理由 |
|---------|---------|------|
| 过度思考/焦虑 | CRT 扫描线 + GSAP 弹窗爆炸 | 终端监控感 → 清空缓存 |
| 水墨/禅意 | 宣纸 multiply + 竖排文字 | 东方纸本美学 |
| 私密疗愈 | 3:4 卡片 + 定制光标 | 画框私密感 + 交互仪式 |
| 温暖治愈 | 定制光标（金色按压态）+ 光环呼吸 | 光标本身成为治愈工具 |

---

## 七、字体系统（Typography System）

### 铁律
- **首选**：宋体/明朝体 — 思源宋体 `Noto Serif SC`（Google Fonts）或系统宋体 `'Songti SC', 'STSong', serif`
- **次选**：细黑体 — `'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif`（字重 300 Light）
- **禁忌**：卡通体、综艺体、粗黑体、圆体 — 永远不用

宋体自带文学属性和呼吸感——笔画粗细变化本身就是一种视觉节奏。

### 字号与间距（高级感的分界线）

```css
.title {
    font-family: 'Noto Serif SC', 'Songti SC', serif;
    font-size: clamp(20px, 4vw, 28px);   /* 精致，不大 */
    font-weight: 300;
    letter-spacing: 10px;                 /* 核心！拉开 = 通透 */
    margin-left: 10px;                    /* 补偿最后一个字的间距 */
}
.subtitle {
    font-size: clamp(12px, 2.4vw, 17px); /* = 标题 × 60% */
    font-weight: 300;
    letter-spacing: 10px;
    margin-left: 10px;
    opacity: 0.65;
}
.hint {
    font-size: clamp(11px, 1.8vw, 14px);
    font-weight: 300;
    letter-spacing: 15px;                /* 提示文字间距最大 */
    margin-left: 15px;
    opacity: 0.45;
}
```

> 字间距 10~15 是"高级感"和"普通"的分界线。拉开的空间让画面有留白、有呼吸。

### 竖排中文（传统美学）

```css
.vertical-text {
    writing-mode: vertical-rl;
    text-orientation: upright;
    letter-spacing: 0.6em;
    font-family: 'KaiTi', 'Noto Serif SC', serif;
}
```

---

## 八、自定义光标体系（Visual Anchor Cursor）

### 基础：Lerp 液态跟随

```javascript
const cursor = { x: window.innerWidth/2, y: window.innerHeight/2, targetX: 0, targetY: 0 };
const LERP = 0.12; // 0.08=悬浮感, 0.15=跟手感, 0.2=接近即时

document.addEventListener('mousemove', e => {
    cursor.targetX = e.clientX;
    cursor.targetY = e.clientY;
});

function updateCursor() {
    cursor.x += (cursor.targetX - cursor.x) * LERP;
    cursor.y += (cursor.targetY - cursor.y) * LERP;
    el.style.transform = `translate(${cursor.x - elW/2}px, ${cursor.y - elH/2}px)`;
}
```

> 关键：用 `transform` 而非 `left/top`（GPU 加速），Lerp 因子 0.08~0.15。

### 三种光标形态（按隐喻选择）

**发光光点（默认）：**
```css
#spirit-cursor {
    width: 20px; height: 20px; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(180,210,255,0.6) 40%, transparent 70%);
    mix-blend-mode: screen;
}
```

**空心圆环（禅意/精准感）：**
```css
#spirit-cursor {
    width: 32px; height: 32px; border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.5);
    background: transparent;
    animation: cursorBreathe 4s infinite ease-in-out;
}
@keyframes cursorBreathe {
    0%,100% { transform: scale(0.9); opacity: 0.4; }
    50% { transform: scale(1.1); opacity: 0.7; }
}
```

**粒子拖尾（能量感）：**
每帧在光标位置 spawn 3~5 个微型 DOM 粒子（`position: fixed`），粒子用 `gsap.to` 或 CSS `@keyframes` 在 0.5s 内 `opacity: 0; scale: 0;` 自行消散。保持粒子总数 ≤ 30。

### 按压态变化

```javascript
function onPressStart() {
    cursorEl.style.width = '36px'; cursorEl.style.height = '36px';
    cursorEl.style.background = 'radial-gradient(circle, #fff 0%, rgba(255,215,0,0.8) 40%, transparent 70%)';
}
function onPressEnd() {
    cursorEl.style.width = '20px'; cursorEl.style.height = '20px';
    cursorEl.style.background = 'radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(180,210,255,0.6) 40%, transparent 70%)';
}
```

> 移动端（`window.innerWidth < 768`）隐藏自定义光标。
| 信息过载 | 噪点 overlay + flicker 动画 | 模拟故障电子设备 |
