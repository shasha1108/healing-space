# p5.js Patterns — 手工感有机创意编程

p5.js 的独特价值：**内置 Perlin noise、流畅的曲线绘制 API、setup/draw 循环范式**。适合"手工绘制""有机生长""自然模拟"类隐喻——那些不应该看起来很"完美"的效果。

## 何时用 p5.js（而非 Three.js 或 CSS）

| 隐喻指向... | 用 p5.js？ | 原因 |
|------------|----------|------|
| 流沙/风痕/发丝/水草 | ✅ 首选 | flow field + curveVertex = 天然有机线条 |
| 水墨笔触/毛笔/书法 | ✅ 首选 | noise 抖动的贝塞尔曲线 = 毛笔的"涩"感 |
| 花粉/孢子/蒲公英飘散 | ✅ 首选 | 粒子 + Perlin wind + 极轻量，万级粒子无压力 |
| 心跳/脑电波/呼吸波形 | ✅ 首选 | beginShape + vertex 逐帧绘制，像示波器 |
| 年轮/指纹/等高线 | ✅ | concentric generative patterns 是 p5.js 的舒适区 |
| 萤火虫/光点群落 | ✅ | 简单粒子 + glow，不需要 3D 空间 |
| 3D 体积光/星系/时钟 | ❌ | 用 Three.js |
| 流体模拟/水墨扩散 | ❌ | 用 FBO/GLSL |
| CRT 终端/DOM 动画 | ❌ | 用 CSS + GSAP |
| >5 万粒子 | ❌ | p5.js CPU 渲染，万级以上用 Three.js |

## 基础骨架

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js"></script>
<script>
// p5.js 自动调用 setup() 一次，draw() 每帧循环
let particles = [];
const N = 3000; // p5.js 舒适区：万级以下

function setup() {
    const canvas = createCanvas(windowWidth, windowHeight);
    canvas.style('position', 'fixed');
    canvas.style('inset', '0');
    canvas.style('z-index', '1');
    // 初始化粒子...
    for (let i = 0; i < N; i++) {
        particles.push({
            x: random(width), y: random(height),
            vx: 0, vy: 0,
            seed: random(1000)
        });
    }
}

function draw() {
    // 半透明背景 = 拖尾效果（自然的运动模糊）
    background(0, 0, 0, 15); // RGBA 的 A 越低拖尾越长
    // 更新 + 绘制...
}

function windowResized() {
    resizeCanvas(windowWidth, windowHeight);
}
</script>
```

> `background(r, g, b, alpha)` 是 p5.js 最被低估的特性——`alpha=10~25` 产生自然的运动拖尾，不需要手动管理粒子历史位置。

## 三大核心 Recipe

### 1. Flow Field（流场）——风痕/发丝/水流

p5.js 的内置 `noise()` 让流场变得极其简洁：

```javascript
const N = 4000;
const points = [];
for (let i = 0; i < N; i++) {
    points.push({ x: random(width), y: random(height) });
}

function draw() {
    background(5, 5, 12, 20); // 深色拖尾

    stroke(255, 255, 255, 80);
    strokeWeight(0.8);
    noFill();

    for (let p of points) {
        // Perlin noise 驱动角度——有机、平滑、永不重复
        const angle = noise(p.x * 0.005, p.y * 0.005, frameCount * 0.003) * TWO_PI * 2;
        p.x += cos(angle) * 0.8;
        p.y += sin(angle) * 0.8;

        // 边界回绕
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        point(p.x, p.y);
    }
}
```

> 调参：`noise(..., frameCount * speed)` 的 speed 控制"风"的快慢。`0.001`=微风，`0.01`=劲风。

### 2. 毛笔笔触（Brush Stroke）——水墨/书法

noise 驱动的贝塞尔曲线 = 毛笔的"涩"感和自然抖动：

```javascript
function drawBrushStroke(startX, startY, length, seed) {
    stroke(0, 0, 0, 160);
    strokeWeight(2);
    noFill();
    beginShape();
    for (let i = 0; i < length; i++) {
        const t = i / length;
        const x = startX + t * 200; // 横向书写
        // noise 产生微小的"手抖"偏移——这就是毛笔的涩感
        const jitterY = (noise(t * 5, seed) - 0.5) * 8;  // 笔画的上下抖动
        const jitterX = (noise(t * 5, seed + 100) - 0.5) * 2; // 笔画的快慢
        const pressure = noise(t * 3, seed + 200) * 0.5 + 0.5; // 0~1 压力
        strokeWeight(1 + pressure * 4); // 压力大→笔画粗
        curveVertex(x + jitterX, startY + jitterY);
    }
    endShape();
}
```

> 关键：`noise(t * 5, seed)` 产生连续的抖动——不是随机跳变，而是"手在微微颤抖"的自然感。

### 3. 粒子群落（Swarm）——萤火虫/花粉/光点

```javascript
const N = 1500;
const particles = [];
for (let i = 0; i < N; i++) {
    particles.push({
        x: random(width), y: random(height),
        vx: 0, vy: 0,
        seed: random(1000),
        size: random(1, 3)
    });
}

function draw() {
    background(2, 2, 8, 30);

    noStroke();
    for (let p of particles) {
        // Perlin noise 驱动加速度——产生"被看不见的风带着走"的感觉
        const angle = noise(p.x * 0.003, p.y * 0.003, frameCount * 0.002) * TWO_PI * 2;
        const force = 0.15;
        p.vx += cos(angle) * force;
        p.vy += sin(angle) * force;
        // 阻尼
        p.vx *= 0.95;
        p.vy *= 0.95;
        p.x += p.vx;
        p.y += p.vy;
        // 边界回绕
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;
        // 萤火虫般的柔和发光
        const alpha = map(noise(p.seed, frameCount * 0.02), 0, 1, 60, 200);
        fill(180, 220, 255, alpha);
        ellipse(p.x, p.y, p.size * 2, p.size * 2);
    }
}
```

## p5.js × 心理疗愈的独特优势

p5.js 有一个 Three.js 很难做到的特质：**它产出的画面看起来"不完美"但"很温暖"**——noise 的抖动、半透明背景的拖尾、手绘线条的涩感——这些恰好是疗愈类内容需要的"人味"。

选择 p5.js 的隐喻判断标准：
- 你的隐喻是一个"手工"的东西（笔、纸、织物、风）→ p5.js
- 你的隐喻是一个"物理"的东西（星系、时钟、流体、玻璃）→ Three.js/FBO
- 你的隐喻是一个"屏幕"上的东西（终端、书本、海报）→ CSS/GSAP

## 性能注意

- p5.js 是 CPU 渲染（Canvas 2D），粒子数控制在 **8,000** 以下保持 60fps
- `background(r,g,b,alpha)` 的 alpha 越小拖尾越长，但每帧要重绘全屏——移动端 alpha 不宜 < 15
- `noise()` 调用次数 = 粒子数 × 调用频率。如果每个粒子每帧调用 3 次 `noise()`、8000 粒子 = 24000 次/帧——仍在可接受范围
- 移动端：粒子数减半，alpha 加倍（减少重绘负担）

---

## 4. 多层笔触光轨（Quality Rendering）

p5.js 实现"发光丝带/光轨"的核心技法——不是 Three.js 粒子，但效果更好。

### 三层笔触叠加 = 光晕层次

```javascript
function drawRibbon(points, r, g, b) {
    noFill();
    for (let layer = 0; layer < 3; layer++) {
        strokeWeight(map(layer, 0, 2, 4, 1));        // 外层粗(4) → 内层细(1)
        stroke(r, g, b, map(layer, 0, 2, 20, 180));  // 外层暗(20) → 内层亮(180)
        beginShape();
        for (let p of points) curveVertex(p.x, p.y);
        endShape();
    }
}
```

> **为什么 3 层**：粗暗的外层 + 中等的中间层 + 细亮的内层 = 天然的光晕渐变。比单层 `strokeWeight(2)` 高级一个量级。

### SCREEN 混合 + Retina 清晰度

```javascript
function draw() {
    background(11, 14, 22, 45); // 半透明背景 = 拖尾残影
    blendMode(BLEND);           // 先画主角（正常混合）
    drawCore(cx, cy);
    blendMode(SCREEN);          // 再画光轨（SCREEN = Additive 发光）
    drawRibbons(...);
    blendMode(BLEND);           // 最后画暗线（正常混合）
    drawDarkLines(...);
}

function setup() {
    createCanvas(windowWidth, windowHeight);
    pixelDensity(min(window.devicePixelRatio, 2)); // ← Retina 清晰！必须！
}
```

> `pixelDensity()` 是 p5.js 最容易被忽略但影响最大的一个调用——没有它，Retina 屏幕上全是马赛克。

### 安抚脉冲波纹

```javascript
const pulses = []; // { x, y, r, alpha }

function createPulse(x, y) {
    pulses.push({ x, y, r: 20, alpha: 180 });
}

function drawPulses() {
    noFill(); blendMode(SCREEN);
    for (let i = pulses.length - 1; i >= 0; i--) {
        let p = pulses[i];
        p.r += 3; p.alpha -= 2.5;
        if (p.alpha <= 0) { pulses.splice(i, 1); continue; }
        strokeWeight(2); stroke(255, 240, 210, p.alpha);
        ellipse(p.x, p.y, p.r * 2);
    }
}
```

> 每次长按触发 `createPulse()` + `AudioSys.playPulse()` ——视觉波纹和听觉水滴同时发生。这就是视听联觉的最小实现。
