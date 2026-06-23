# Pixel × Frutiger Aero — 像素化的治愈万物

> 覆盖 p5.js Canvas 像素渲染 + Frutiger Aero 玻璃美学结合的技法配方。
> 像素画的"颗粒温暖" + Frutiger Aero 的"清透光泽" = 童年玻璃弹珠里的另一个世界。

## 核心理念

像素画唤起 NES/GBA 时代的视觉记忆，Fruttiger Aero 唤起 2004-2013 的科技乐观主义。两者在同一帧内碰撞：
- **像素格子** → `pixelDensity(1)` + `noSmooth()` — 故意粗糙的颗粒感
- **玻璃光泽** → CSS `backdrop-filter: blur()` 的毛玻璃卡片 + 半透明高光层
- **渐变底色** → 天空渐变 `#7ad0f5 → #edfafd` 作为场景底板
- **气泡光斑** → 纯 CSS `radial-gradient` 伪元素漂浮在画布上方

**叠加公式：Canvas 像素层（z-index:1） + CSS 玻璃装饰层（z-index:2） + 渐变背景（z-index:0）**

## 场景类型速查

| 场景 | 像素元素 | Aero 玻璃元素 | 参考 |
|------|---------|-------------|------|
| 水族箱 | 像素小鱼、水草、气泡 | 圆角毛玻璃水箱外框、水纹高光 | §水族箱配方 |
| 桌面摆件 | 像素盆栽、像素钟、像素文具 | Windows Aero 窗口边框、桌面阴影 | §桌面摆件配方 |
| 天空之窗 | 像素云、像素鸟、像素飞机 | `backdrop-filter` 窗户框 + 天空渐变 | §天空之窗配方 |
| 天气瓶子 | 像素雨滴/雪花在瓶内 | 玻璃瓶轮廓 + 瓶塞高光 + 背景虚化 | §天气瓶子配方 |
| 掌机屏幕 | 像素角色在 GBA 屏幕内 | 设备外框模拟 + 屏幕反光条 | §掌机屏幕配方 |

---

## 基础骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pixel Aero</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
<style>
  *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

  /* ── Frutiger Aero 渐变底色 ── */
  body {
    background: linear-gradient(160deg, #7ad0f5 0%, #b1e6f5 30%, #dcf4ec 65%, #edfafd 100%);
    width: 100vw; height: 100vh; overflow: hidden;
    font-family: "Segoe UI", "Frutiger", "Noto Serif SC", sans-serif;
  }

  /* ── 玻璃装饰层（DOM，在 canvas 上方） ── */
  .glass-overlay {
    position: fixed; inset: 0; z-index: 2; pointer-events: none;
  }
  /* 环境光斑 */
  .glass-overlay::before {
    content: ''; position: absolute;
    width: 200px; height: 200px; top: 10%; left: 5%;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255,255,255,0.5) 0%, transparent 70%);
    animation: float 12s ease-in-out infinite;
  }
  @keyframes float {
    0%,100% { transform: translate(0,0) scale(1); }
    50% { transform: translate(20px,-30px) scale(1.05); }
  }

  canvas {
    position: fixed; inset: 0; z-index: 1;
  }
</style>
</head>
<body>
<div class="glass-overlay"></div>
<script>
// ── p5.js 像素渲染 ──
function setup() {
  const c = createCanvas(windowWidth, windowHeight);
  pixelDensity(1);   // ← 像素化核心：强制低分辨率
  noSmooth();        // ← 关闭抗锯齿，保持尖锐像素边缘
  // ... 你的像素渲染逻辑
}

function draw() {
  clear();           // ← 透明背景，让 CSS 渐变透过来
  // ... 像素绘制
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
  pixelDensity(1);
}
</script>
</body>
</html>
```

**关键点：**
- `pixelDensity(1)` + `noSmooth()` — 强制像素颗粒感
- `clear()` 替代 `background()` — 让 CSS 渐变底色透出
- CSS 层在 canvas 上方（`z-index: 2`）— 光斑和毛玻璃框不会被子遮挡
- `windowResized()` 里也要 `pixelDensity(1)` — 否则窗口缩放后像素密度被重置

---

## 水族箱配方

### 像素小鱼的绘制

```javascript
// ── 像素鱼（8x6 像素网格，每个"像素"是实际 px 的 N 倍） ──
const PX = 6;  // 像素块大小（调小=精细, 调大=颗粒感）

function drawPixelFish(x, y, facingRight, colorPalette) {
  // 鱼形像素数据：[row][col] = 0(空) | 1(身体) | 2(眼睛) | 3(鳍)
  // 8列 × 6行
  const fishShape = [
    [0,0,0,0,1,0,0,0],  // 背鳍
    [0,0,1,1,2,1,1,0],  // 身体+眼睛
    [1,1,1,1,1,1,1,1],  // 身体
    [1,1,1,1,1,1,1,1],  // 身体
    [0,0,1,1,2,1,1,0],  // 身体+眼睛
    [0,0,0,0,3,0,0,0],  // 腹鳍
  ];

  push();
  translate(x, y);
  if (!facingRight) scale(-1, 1);

  for (let row = 0; row < fishShape.length; row++) {
    for (let col = 0; col < fishShape[row].length; col++) {
      const cell = fishShape[row][col];
      if (cell === 0) continue;

      const px = (col - 4) * PX;   // 居中对齐
      const py = (row - 3) * PX;

      if (cell === 1) fill(colorPalette.body);
      else if (cell === 2) fill(colorPalette.eye || '#ffffff');
      else if (cell === 3) fill(colorPalette.fin);

      noStroke();
      rect(px, py, PX, PX);
    }
  }
  pop();
}

// 使用示例
const palettes = [
  { body: '#f4a460', fin: '#ff8c69', eye: '#ffffff' },  // 橙金
  { body: '#87ceeb', fin: '#5f9ea0', eye: '#ffffff' },  // 天蓝
  { body: '#ffb6c1', fin: '#ff69b4', eye: '#ffffff' },  // 粉白
];
```

### 像素水草

```javascript
function drawPixelSeaweed(x, baseY, height, phase) {
  const W = PX * 2;  // 水草宽度：2个像素块
  push();
  noStroke();
  for (let i = 0; i < height; i++) {
    const sway = sin(phase + i * 0.3) * (i * 0.3);  // 越往上摆幅越大
    const alpha = map(i, 0, height, 200, 80);         // 越往上越透明
    fill(100, 180, 140, alpha);
    rect(x + sway, baseY - i * PX, W, PX, 1);
  }
  pop();
}
```

### 像素气泡

```javascript
function drawPixelBubble(x, y, size) {
  push();
  noFill();
  stroke(255, 180);       // 半透明白边
  strokeWeight(1);
  rect(x, y, size, size, 2);  // 圆角矩形 = 像素气泡

  // 高光点（左上角白点）
  noStroke();
  fill(255, 200);
  rect(x + 1, y + 1, size * 0.3, size * 0.3, 1);
  pop();
}
```

---

## 桌面摆件配方

### Windows Aero 窗口边框模拟

```css
/* 毛玻璃窗口框 — 叠加在 canvas 上方 */
.aero-window {
  position: fixed; z-index: 3; pointer-events: none;
  border: 1px solid rgba(255,255,255,0.8);
  border-bottom: 1px solid rgba(255,255,255,0.3);
  border-right: 1px solid rgba(255,255,255,0.3);
  border-radius: 12px;
  background: rgba(255,255,255,0.08);
  backdrop-filter: blur(1px);  /* 极轻微模糊 — 暗示玻璃存在 */
  box-shadow:
    inset 0 1px 3px rgba(255,255,255,0.6),
    0 8px 24px rgba(0,80,120,0.12);
}
```

### 窗口标题栏

```html
<div class="aero-titlebar">
  <!-- 左侧图标 + 标题 -->
  <span class="aero-icon">🐠</span>
  <span class="aero-title">pixel_aquarium.exe</span>
  <!-- 右侧三按钮：最小化/最大化/关闭 -->
  <span class="aero-btn aero-min"></span>
  <span class="aero-btn aero-max"></span>
  <span class="aero-btn aero-close"></span>
</div>
```

---

## 天空之窗配方

场景：像素云在窗外飘，窗外是 Frutiger Aero 蓝天。窗口框是毛玻璃质感。

```javascript
// 像素云绘制
function drawPixelCloud(cx, cy, size) {
  push(); noStroke();
  // 云 = 几个错位方块堆叠
  const s = size * PX;
  fill(255, 230);
  rect(cx - s*0.5, cy,        s*0.6, s*0.3, 2);
  rect(cx - s*0.3, cy - s*0.2, s*0.7, s*0.35, 2);
  rect(cx,        cy - s*0.1, s*0.5, s*0.3, 2);
  pop();
}
```

---

## 天气瓶子配方

```javascript
// 瓶内像素雨滴（受重力 + 瓶壁碰撞）
class PixelRaindrop {
  constructor(bottleX, bottleY, bottleW, bottleH) {
    this.x = random(bottleX + 4, bottleX + bottleW - 4);
    this.y = random(bottleY, bottleY + bottleH * 0.3);
    this.speed = random(1.5, 3.5);
    this.bx = bottleX; this.by = bottleY;
    this.bw = bottleW; this.bh = bottleH;
  }
  update() {
    this.y += this.speed;
    if (this.y > this.by + this.bh - 4) {  // 瓶底反弹
      this.y = this.by + this.bh - 4;
      this.speed *= -0.3;  // 小反弹
    }
    if (this.y < this.by + 4) this.y = this.by + random(4, this.bh * 0.3);
  }
  draw() {
    fill(180, 210, 255, 180);
    noStroke();
    rect(this.x, this.y, PX * 0.6, PX * 2, 1);
  }
}
```

---

## 像素平滑运动

像素画不需要 lerp！像素的"卡顿感"本身就是 charm。但需要一些技巧防止太抖：

```javascript
// ❌ 差：直接用浮点坐标画 — 像素会"闪"
rect(mouseX, mouseY, PX, PX);

// ✅ 好：snap 到像素网格
let sx = floor(mouseX / PX) * PX;
let sy = floor(mouseY / PX) * PX;
rect(sx, sy, PX, PX);

// ✅ 更好：对半透明物体不用 snap，对实体物体 snap
// → 气泡/光斑：浮点坐标 + alpha（柔和的玻璃感）
// → 鱼/水草/石头：snap 到网格（锐利的像素感）
```

---

## 交互模式

### 点击投食（水族箱）

```javascript
function mousePressed() {
  // 在点击位置掉一颗像素鱼食
  fishFood.push({
    x: floor(mouseX / PX) * PX,
    y: floor(mouseY / PX) * PX,
    vy: 0,
    alpha: 255
  });
}
```

鱼食缓慢下沉，鱼群向食物聚集（可以用简单的 `lerp` 引导鱼的方向）。

### 敲玻璃

```javascript
// 双击 = 敲水族箱玻璃，像素鱼短暂散开
function doubleClicked() {
  fish.forEach(f => {
    // 给每条鱼一个远离点击位置的冲击向量
    f.fleeX = (f.x - mouseX) * 3;
    f.fleeY = (f.y - mouseY) * 3;
  });
  // CSS 添加短暂的水纹涟漪动画
}
```

### 拖拽放大镜

按住鼠标拖出一个毛玻璃放大镜矩形，框内的像素被放大 2x 渲染（`scale(2)` 局部重绘）。

---

## 颜色配方

### Frutiger Aero 水族箱配色

```javascript
const AERO_AQUARIUM = {
  bgGradient: ['#7ad0f5', '#b1e6f5', '#dcf4ec', '#edfafd'],
  glassBorder: 'rgba(255,255,255,0.7)',
  glassShadow: 'rgba(10,80,120,0.08)',
  fishWarm:  ['#f4a460', '#ff8c69', '#ffb6c1'],  // 暖色鱼
  fishCool:  ['#87ceeb', '#5f9ea0', '#b0c4de'],  // 冷色鱼
  seaweed:   '#64b48c',
  bubble:    'rgba(255,255,255,0.5)',
  sand:      '#e8d5b0',
};
```

### 像素游戏的 Nostalgia 配色

```javascript
const GAMEBOY_PALETTE = ['#0f380f', '#306230', '#8bac0f', '#9bbc0f']; // Game Boy 四阶绿
const NES_PALETTE     = ['#000000', '#fcfcfc', '#f8a4c8', '#c084fc']; // NES 暖色系
```

可以在页面加载时用 `color()` 函数动态混色：`lerpColor(gameboyGreen, aeroTeal, 0.3)`。

---

## 实现铁律

### 像素运动

运动计算用浮点，只在绘制原点时 `round()` 到像素网格。禁止对物体坐标本身做 grid snap。

### 交互事件

不使用 p5.js 内置的双击检测（会先触发单击）。统一使用自定义 `pointerdown` + 时间间隔判断单击/双击。

### Z-index 分层

模糊底板 < canvas 像素层 < 玻璃壳/UI。`backdrop-filter` 绝不放在 canvas 上层。

---

## 质量自检清单

- [ ] `pixelDensity(1)` + `noSmooth()`，且 `windowResized` 中重复设置
- [ ] `clear()` 而非 `background()`，CSS 背景透出
- [ ] Z-index 三层分离，毛玻璃模糊在 canvas 之下
- [ ] 运动浮点计算 + `translate(round())` 对齐
- [ ] 交互用自定义 `pointerdown` + 时间差判断，非 p5 内置事件
- [ ] 主体角色有状态机（≥ 3 个状态）
- [ ] 主体角色有动画反馈（非纯静态贴图）
- [ ] 玻璃/容器有立体感（边框不等宽、高光、内发光至少两项）
- [ ] canvas 有 CSS 景深效果（`drop-shadow` 或等效阴影）
- [ ] 环境中 ≥ 2 种不同形态装饰元素
- [ ] 颜色来自预设调色板数组，非硬编码随机 RGB
- [ ] 移动端适配：`user-scalable=no`，触摸不触发页面缩放
