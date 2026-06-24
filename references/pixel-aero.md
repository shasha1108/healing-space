# Pixel × Frutiger Aero — 像素化的治愈万物

> 📦 **此技法已独立为专属 skill：** [pixel-aero](https://github.com/shasha1108/pixel-aero) — 赛博养宠/养花/水族箱等玻璃容器像素生命体场景，请使用该 skill 获得更专注的生成体验。本文档在 healing-space 中保留作为技法参考。
>
> 覆盖 p5.js Canvas 像素渲染 + Frutiger Aero 玻璃美学结合的工业级技法配方。
> 像素画的"颗粒温暖" + Frutiger Aero 的"清透光泽" = 童年玻璃弹珠里的另一个世界。
> 适用于赛博养宠、赛博养花、电子水族箱等一切"玻璃容器内的像素生命体"场景。

## 核心理念

像素画唤起 NES/GBA 时代的视觉记忆，Frutiger Aero 唤起 2004-2013 的科技乐观主义。两者在同一帧内碰撞：
- **像素格子** → `pixelDensity(1)` + `noSmooth()` — 故意粗糙的颗粒感
- **玻璃光泽** → CSS `backdrop-filter: blur()` 毛玻璃 + 半透明高光层
- **渐变底色** → 天空渐变 `#7ad0f5 → #edfafd` 作为场景底板
- **材质对比** → 像素实体（锐利 rect）+ 非像素流体（光滑 circle）= 视觉张力

**叠加公式（Z-index 三明治）：**
```
底板层 (blur 毛玻璃) < Canvas 像素层 (锐利) < 玻璃壳 (透明高光 + 无 blur)
```

---

## 防御性前端骨架（Safari/iOS 兼容）

`backdrop-filter: blur()` 在 Safari 中会强制创建新的层叠上下文，导致 Canvas 被压在毛玻璃下面消失。必须通过 JS 强控层级：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>Pixel Aero</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
  html, body {
    width: 100vw; height: 100vh; overflow: hidden;
    background: linear-gradient(160deg, #6ac5f8 0%, #90dcf4 35%, #bdf2e4 70%, #e6fcf5 100%);
    font-family: "Segoe UI", "Frutiger", sans-serif;
    user-select: none; -webkit-user-select: none; touch-action: none;
  }

  /* 环境光斑（底层，z-index: 1）*/
  .ambient-light {
    position: fixed; z-index: 1; pointer-events: none; border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.6) 0%, transparent 60%);
  }

  /* 毛玻璃底板（z-index: 2 — canvas 之下）*/
  .glass-bg {
    position: fixed; z-index: 2; pointer-events: none;
    top: 6vh; left: 5vw; right: 5vw; bottom: 6vh;
    border-radius: 24px;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
  }

  /* 透明玻璃外壳（z-index: 4 — canvas 之上，无 blur）*/
  .glass-shell {
    position: fixed; z-index: 4; pointer-events: none;
    top: 6vh; left: 5vw; right: 5vw; bottom: 6vh; border-radius: 24px;
    border-top: 2px solid rgba(255,255,255,0.85);
    border-left: 2px solid rgba(255,255,255,0.5);
    border-right: 1px solid rgba(255,255,255,0.25);
    border-bottom: 1px solid rgba(255,255,255,0.15);
    box-shadow: inset 0 0 20px rgba(255,255,255,0.35),
                inset 0 50px 50px rgba(255,255,255,0.15);
  }
  .glass-shell::after {
    content: ''; position: absolute;
    top: -20%; left: -5%; width: 120%; height: 45%;
    background: linear-gradient(180deg, rgba(255,255,255,0.4) 0%, transparent 100%);
    border-radius: 50%; transform: rotate(-10deg);
  }

  /* 交互拦截层（z-index: 5）*/
  #interact-layer { position: fixed; inset: 0; z-index: 5; }
</style>
</head>
<body>

<div class="ambient-light" style="width:30vw;height:30vw;top:-5%;left:5%;"></div>
<div class="ambient-light" style="width:22vw;height:22vw;bottom:8%;right:5%;"></div>
<div class="glass-bg"></div>
<div class="glass-shell"></div>
<div id="interact-layer"></div>

<script>
function setup() {
  let cvs = createCanvas(windowWidth, windowHeight);
  // 致命关键：JS 强控层级，夹在 glass-bg(2) 和 glass-shell(4) 之间
  cvs.style('position', 'fixed');
  cvs.style('top', '0');
  cvs.style('left', '0');
  cvs.style('z-index', '3');
  cvs.style('pointer-events', 'none');
  // 增加水下景深感
  cvs.style('filter', 'drop-shadow(0px 8px 6px rgba(0,80,120,0.15))');

  pixelDensity(1);
  noSmooth();
}

function draw() {
  clear(); // 透明背景，让 CSS 渐变透出
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
  pixelDensity(1); // 缩放后必须重设
}
</script>
</body>
</html>
```

**关键点：**
- Canvas `z-index: 3` 精准夹在毛玻璃底板(2)和透明外壳(4)之间
- 玻璃壳 `z-index: 4` **不加 blur**，否则像素层被模糊
- `cvs.style('filter', 'drop-shadow(...)')` — CSS 层面给整个像素世界增加景深
- `pointer-events: none` 让 canvas 不拦截事件，由独立 `#interact-layer` 统一处理

---

## 基础造型配方

### Frutiger Aero 标准气泡（铁律）

Aero 气泡必须是正圆 `circle()`，绝对禁止使用圆角矩形 `rect()`。高光为同心偏移的实心小白圆，产生曲面反射感。

```javascript
function drawAeroBubble(x, y, size) {
  push();
  // 1. 晶莹剔透的外壳（极细白边）
  noFill(); stroke(255, 200); strokeWeight(1.5);
  circle(x, y, size);

  // 2. 曲面高光（向左上角偏移的纯白小圆 — Crescent Highlight）
  noStroke(); fill(255, 255);
  let hOff = size * 0.18;
  let hSize = size * 0.35;
  circle(x - hOff, y - hOff, hSize);
  pop();
}
```

### 像素角色（通用 Sprite 网格）

```javascript
// 角色像素数据：0=空, 1=身体主色, 2=眼睛/高光, 3=附属色(鳍/翅膀/耳朵)
// 使用时 translate(round(x), round(y)) 后调用
function drawPixelSprite(shape, palette, px) {
  for (let row = 0; row < shape.length; row++) {
    for (let col = 0; col < shape[row].length; col++) {
      const cell = shape[row][col];
      if (!cell) continue;
      const sx = (col - floor(shape[row].length / 2)) * px;
      const sy = (row - floor(shape.length / 2)) * px;
      noStroke();
      if (cell === 1) fill(palette.body);
      else if (cell === 2) fill(palette.eye);
      else if (cell === 3) fill(palette.accent);
      rect(sx, sy, px, px);
    }
  }
}
```

---

## 程序化生态生成（Procedural Flora）

不手画每一个像素，用算法生成具备有机感的聚落。以下三种模型覆盖赛博养花/养宠的绝大部分场景。

### 模型 A：向上堆叠 + 正弦摇摆（水草/海带/花茎/柳条）

```javascript
function drawStackSway(baseX, baseY, segments, px, color1, color2, phase) {
  for (let i = 0; i < segments; i++) {
    let sway = sin(phase + i * 0.3) * (i * px * 0.2);
    fill(i % 2 === 0 ? color1 : color2);
    rect(round(baseX + sway), baseY - i * px, px * 1.5, px);
  }
}
```

### 模型 B：网格阵列 + 随机剔除（海绵/灌木/树冠/草丛）

```javascript
function drawGridCluster(baseX, baseY, gridW, gridH, px, palette, density) {
  for (let by = 0; by < gridH; by++) {
    for (let bx = -gridW; bx <= gridW; bx++) {
      if (random() > density) continue;
      fill(random(palette));
      rect(baseX + bx * px, baseY - by * px, px, px);
    }
  }
}
```

### 模型 C：圆域筛选 / 勾股定理（脑纹珊瑚/花蕊/蘑菇/球形灌木）

```javascript
function drawRadialCluster(baseX, baseY, radius, px, palette) {
  for (let dy = 0; dy < radius; dy++) {
    let limit = round(sqrt(radius * radius - dy * dy));
    for (let dx = -limit; dx <= limit; dx++) {
      if (random() > 0.15) {
        fill(random(palette));
        rect(baseX + dx * px, baseY - dy * px, px, px);
      }
    }
  }
}
```

### 模型 D：扇形展开（海扇/孔雀屏/棕榈叶/扇形珊瑚）

```javascript
function drawFan(baseX, baseY, height, px, color1, color2) {
  for (let dy = 0; dy < height; dy++) {
    let spread = round(dy * 0.8);
    for (let dx = -spread; dx <= spread; dx++) {
      if (random() > 0.4 || abs(dx) === spread) {
        fill(random() > 0.5 ? color1 : color2);
        rect(baseX + dx * px, baseY - dy * px, px, px);
      }
    }
  }
}
```

**组合原则：** 一次场景中至少使用两种模型（如 A+C 做水草+珊瑚礁，B+D 做灌木+扇形花卉）。每种模型用独立调色板，产生色彩层次。

---

## 赛博生命体状态机（AI FSM）

不论是养鱼、养猫、养史莱姆还是电子盆栽，通用以下状态结构：

```javascript
// 状态枚举
const STATE = { WANDER: 'wander', CHASE: 'chase', FLEE: 'flee' };

function updateCreature(c) {
  // 状态转换逻辑
  if (c.state === STATE.FLEE) {
    c.fleeTimer--;
    if (c.fleeTimer <= 0) c.state = STATE.WANDER;
  } else if (targetNearby(c)) {
    c.state = STATE.CHASE;
    if (reachedTarget(c)) { c.state = STATE.WANDER; c.reaction = 30; }
  } else {
    c.state = STATE.WANDER;
  }

  // Wander: 使用 noise() 产生不可预测的平滑探索运动
  if (c.state === STATE.WANDER) {
    c.vx += (noise(c.x * 0.01, frameCount * 0.005) - 0.5) * 0.1;
    c.vy += (noise(c.y * 0.01, frameCount * 0.005 + 100) - 0.5) * 0.1;
  }
  // Chase: atan2 角度 + 固定加速度靠近目标
  else if (c.state === STATE.CHASE) {
    let angle = atan2(c.targetY - c.y, c.targetX - c.x);
    c.vx += cos(angle) * 0.12; c.vy += sin(angle) * 0.12;
  }
  // Flee: 远离触发源，摩擦力衰减
  else if (c.state === STATE.FLEE) {
    c.vx *= 0.92; c.vy *= 0.92;
  }

  // 速度钳制（不同状态不同上限）
  let limit = c.state === STATE.FLEE ? 8 : (c.state === STATE.CHASE ? 3 : 1.5);
  let spd = sqrt(c.vx * c.vx + c.vy * c.vy);
  if (spd > limit) { c.vx = (c.vx / spd) * limit; c.vy = (c.vy / spd) * limit; }

  c.x += c.vx; c.y += c.vy;

  // reaction 衰减 — 吃到东西/被摸时短暂播放反馈动画
  if (c.reaction > 0) c.reaction--;
}
```

**状态切换规则（通用）：**
- `WANDER → CHASE`：目标（食物/鼠标/同伴）进入检测半径
- `CHASE → WANDER`：到达目标（距离 < 阈值）或超时
- `任意 → FLEE`：外部事件触发（敲玻璃/点击惊吓），持续 N 帧后自动回到 WANDER

---

## 防坑铁律 + 标准交互模板

### 1. 像素渲染与丝滑运动的终极公式

- **物体坐标 (`f.x`, `f.y`)**：保持**浮点数**（如 `10.453`），速度累加才不卡顿。
- **绘制原点 (`translate`)**：包裹 `round()`（如 `translate(round(f.x), round(f.y))`），像素边缘绝对锐利。

```javascript
// ✅ 正确
c.x += c.vx; c.y += c.vy;      // 浮点运动
translate(round(c.x), round(c.y)); // 仅绘制时对齐

// ❌ 错误：直接 snap 坐标 → 一格一格跳跃
c.x = floor(c.x / PX) * PX;
```

### 2. 单击/双击分离模板（直接复制使用）

放弃 p5.js 内置事件（`mousePressed` + `doubleClicked` 必然冲突）。使用原生 DOM `pointerdown` + 时间差判断：

```javascript
let lastTapTime = 0, tapTimeout;
document.getElementById('interact-layer').addEventListener('pointerdown', (e) => {
  let now = Date.now();
  if (now - lastTapTime < 300) {
    clearTimeout(tapTimeout);
    onDoubleTap(e.clientX, e.clientY); // 双击
    lastTapTime = 0;
  } else {
    lastTapTime = now;
    tapTimeout = setTimeout(() => { onSingleTap(e.clientX, e.clientY); }, 300); // 单击
  }
});
```

### 3. 敲击涟漪 CSS（直接复制使用）

```css
.knock-ripple {
  position: fixed; z-index: 6; pointer-events: none;
  border-radius: 50%; border: 3px solid rgba(255,255,255,0.9);
  background: radial-gradient(circle, rgba(255,255,255,0.5) 0%, transparent 60%);
  animation: ripple 0.8s cubic-bezier(0.1, 0.8, 0.3, 1) forwards;
  transform: translate(-50%, -50%);
}
@keyframes ripple {
  0%   { width: 0; height: 0; opacity: 1; border-width: 8px; }
  100% { width: 250px; height: 250px; opacity: 0; border-width: 1px; }
}
```

---

## 颜色配方

### Frutiger Aero 天空/水色（作为背景渐变）

```javascript
const AERO_SKY = ['#6ac5f8', '#90dcf4', '#bdf2e4', '#e6fcf5'];
```

### 通用调色板模板

```javascript
// 暖色系（珊瑚/日落/秋叶）
const WARM_PALETTES = [
  ['#ff7e67', '#ff4c29'], ['#ffa502', '#eccc68'], ['#ffb6c1', '#ff69b4']
];
// 冷色系（海洋/冰川/夜空）
const COOL_PALETTES = [
  ['#50c878', '#228b22'], ['#87cefa', '#4169e1'], ['#00cec9', '#81ecec']
];
// 荧光系（热带/霓虹/游戏感）
const NEON_PALETTES = [
  ['#ff4757', '#ff6b81'], ['#9b59b6', '#cd84f1'], ['#ffd700', '#ffa500']
];
```

使用方式：为场景中不同物体分配不同调色板，而非每个物体独立随机 RGB。这样画面有色调统一感。

---

## 质量自检清单

交付前逐条确认：

- [ ] `pixelDensity(1)` + `noSmooth()`，且 `windowResized` 中重复设置
- [ ] `clear()` 而非 `background()`，CSS 背景透出
- [ ] Canvas 使用 JS 强控 `position:fixed; z-index:3`（夹在底板和外壳之间）
- [ ] 毛玻璃 `backdrop-filter: blur()` 在 canvas 下层，外壳层无 blur
- [ ] 运动浮点计算 + `translate(round())` 对齐，不对坐标做 grid snap
- [ ] 交互使用自定义 `pointerdown` + 300ms 时间差，非 p5 内置事件
- [ ] 主体角色有状态机（≥ 3 个状态：wander / chase / flee）
- [ ] 主体角色有动画反馈（尾巴摆动/爱心/缩放/颜色变化等）
- [ ] 气泡使用 `circle()` + 偏移高光，禁止 `rect()` 气泡
- [ ] 环境 ≥ 2 种形态装饰元素（至少使用 2 种程序化生成模型）
- [ ] 颜色来自预设调色板数组，非每个物体独立随机 RGB
- [ ] Canvas 有 CSS `filter: drop-shadow()` 产生景深感
- [ ] 移动端：`user-scalable=no`，`touch-action: none`
