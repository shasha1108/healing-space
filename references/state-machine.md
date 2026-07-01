# State Machine — 情感弧线设计武器库

本文件是情感弧线（emotional arc）设计的真实可复用代码与模式。**照着改，不要从零发明。**

核心思想：**治愈体验 = 一个从压抑走向释放的"进度条" `calm: 0→1`，由用户的持续交互推动**。所有视觉、物理、音频参数都从这一个值派生。这个设计把"叙事"变成一个可计算的连续量。

## 目录

- [一、单一核心变量模型](#一单一核心变量模型最推荐)
- [二、交互如何推动 calm](#二交互如何推动-calm)（模式 A 长按 / B 点击释放 / C 拖拽梳理 / D 静止心流）
- [三、calm 驱动一切（总线）](#三calm-如何驱动一切视听联觉的总线)
- [四、阶段切换的文案与 UI](#四阶段切换的文案与-ui叙事感来源)
- [五、相机动力学](#五相机动力学被严重低估的沉浸感来源)
- [六、自动运镜入场](#六自动运镜入场页面加载时必做)
- [七、4-7-8 呼吸引导](#七-4-7-8-呼吸引导治愈达成后的留白仪式)
- [八、进阶：可逆 vs 不可逆](#八进阶可逆-vs-不可逆决定体验的重量感)
- [九、避免的坑](#九避免的坑)
- [十、文案递进模式](#十文案递进模式subtitle-progression)
- [十一、文案节奏与视觉高潮同步](#十一文案节奏与视觉高潮同步)
- [十二、交互模式 E：拖拽操控时间](#十二交互模式-e拖拽操控时间drag-to-manipulate-time)
- [十三、交互模式 F：定时自动疗愈](#十三交互模式-f定时自动疗愈timed-auto-healing)
- [十四、交互模式 G：长按安抚](#十四交互模式-g长按安抚最推荐用于疗愈类)
- [十五、高潮触发条件设计](#十五高潮触发条件设计反模式对照)
- [速查：主题 → 状态机配置](#速查主题--状态机配置)
- [速查新增](#速查新增)

---

## 一、单一核心变量模型（最推荐）

绝大多数治愈网页只需要**一个**核心进度变量，我称之为 `calm`（平静度，0=压抑初始，1=治愈终态）：

```javascript
const State = {
    calm: 0,           // 核心进度，0→1
    calmTarget: 0,     // 目标值（交互推动它）
    phase: 'intro',    // 'intro' | 'active' | 'complete' 离散阶段（用于切文案/UI）
    interactCount: 0,  // 用户交互累计（用于推进阶段）
    time: 0,           // 累计时间
};

// 每帧把 calm 平滑追上 calmTarget（缓动，避免突变）
function updateState(dt) {
    State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * 1.5);  // 全局常量 CALM_LERP_SPEED（见 causal-field.md §三 规则 3）
    State.time += dt;

    // 阶段切换
    if (State.calm < 0.05)       State.phase = 'intro';
    else if (State.calm < 0.95)  State.phase = 'active';
    else                         State.phase = 'complete';
}
```

> **为什么用 `calm += (target - calm) * k` 而不是直接赋值**：这是指数缓动，天然有"惯性感"——你松手后画面不会立刻塌回初始态，而是慢慢漂。这种"滞后"是沉浸感的关键。

---

## 二、交互如何推动 calm

不同交互方式对应不同的"治愈隐喻"。选一个最贴主题的：

### 模式 A：持续长按 = 攒气（呼吸/专注类）

按住时 calm 缓慢上升，松手缓慢回落。隐喻"需要持续投入才能维持平静"：

```javascript
let pressing = false;
window.addEventListener('mousedown', () => pressing = true);
window.addEventListener('mouseup',   () => pressing = false);
window.addEventListener('touchstart', () => pressing = true);
window.addEventListener('touchend',   () => pressing = false);

function updateState(dt) {
    if (pressing) {
        State.calmTarget = Math.min(1, State.calmTarget + dt * 0.25);  // 每秒涨 0.25
    } else {
        State.calmTarget = Math.max(0, State.calmTarget - dt * 0.08);  // 松手慢慢回落
    }
    State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * 1.5);
    // ...阶段切换
}
```

> 完整一次（0→1）约需按住 4 秒。可调。

### 模式 B：点击 = 释放脉冲（情绪释放类）

每次点击给 calm 一个跳升，然后画面"消化"它。隐喻"一次次的小释放累积成大转变"：

```javascript
window.addEventListener('mousedown', () => {
    State.calmTarget = Math.min(1, State.calmTarget + 0.08);
    PHYS.pulse = 50;   // 同时触发物理脉冲（见 particle-physics.md）
    State.interactCount++;
});

function updateState(dt) {
    // 不主动回落，calm 只能单调上升（释放不可逆）
    State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * 0.6);
}
```

> ~13 次点击达到满 calm。适合"剥落""击碎"类主题。

### 模式 C：滑动/拖拽 = 梳理（禅意/枯山水类）

拖拽距离累积转化为 calm。隐喻"用动作梳理混乱"：

```javascript
let lastMouse = null;
let dragAccum = 0;
window.addEventListener('mousemove', (e) => {
    if (lastMouse) {
        const dx = e.clientX - lastMouse.x;
        const dy = e.clientY - lastMouse.y;
        dragAccum += Math.sqrt(dx*dx + dy*dy);
    }
    lastMouse = {x: e.clientX, y: e.clientY};
});

function updateState(dt) {
    State.calmTarget = Math.min(1, dragAccum / 5000);  // 拖拽 5000 像素路程满
    State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * 1.0);
}
```

### 模式 D：静止保持 = 心流（专注类）

鼠标移动 = 失分，鼠标静止 = 加分。隐喻"保持专注"：

```javascript
let lastMoveTime = performance.now();
window.addEventListener('mousemove', () => lastMoveTime = performance.now());

function updateState(dt) {
    const stillFor = (performance.now() - lastMoveTime) / 1000;
    if (stillFor > 0.5) {
        State.calmTarget = Math.min(1, State.calmTarget + dt * 0.15);
    } else {
        State.calmTarget = Math.max(0, State.calmTarget - dt * 0.4);  // 乱动掉得快
    }
    State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * 1.2);
}
```

---

## 三、calm 如何驱动一切（总线）

`calm` 是**唯一的状态源**。所有视觉、物理、音频参数都从它派生。

**smoothstep 根基**（所有过渡类参数的起点）：

```javascript
const c  = State.calm;
const ts = c * c * (3 - 2 * c);   // smoothstep，S 形过渡——"起势慢→中段快→收尾慢"
```

**颜色过渡（GPU 端）** → `shader-patterns.md §六` — 主循环只需一行 `material.uniforms.uTransition.value = ts`。

**完整参数映射表 + applyCalmState 骨架 + 过渡一致性规则** → `causal-field.md §二~§四`（权威定义）。

> 本节的快速上手示例已被 causal-field.md 替代——后续更新只在该文件进行，避免两处值漂移。

---

## 四、阶段切换的文案与 UI（叙事感来源）

光有数值变化不够，要配**文案**让用户知道自己在经历什么。三阶段文案模板：

```javascript
const COPY = {
    intro: {
        title: '这里很吵',                          // 初始压抑
        hint:  '按住屏幕，让它慢慢安静下来',
    },
    active: {
        title: '正在平息',
        hint:  '继续，感受它的呼吸',
    },
    complete: {
        title: '安静了',
        hint:  '松手，它会记得这份平静',             // 治愈终态
    },
};

const titleEl = document.getElementById('title');
const hintEl  = document.getElementById('hint');
let lastPhase = null;
function updateUI(phase) {
    if (phase === lastPhase) return;
    lastPhase = phase;
    // 淡出 → 换字 → 淡入
    titleEl.style.transition = 'opacity 0.8s';
    hintEl.style.transition  = 'opacity 0.8s';
    titleEl.style.opacity = 0;
    hintEl.style.opacity  = 0;
    setTimeout(() => {
        titleEl.textContent = COPY[phase].title;
        hintEl.textContent  = COPY[phase].hint;
        titleEl.style.opacity = 1;
        hintEl.style.opacity  = 1;
    }, 800);
}
```

> 文案要**克制**。治愈类网页文案越少越有力量。每个阶段一两句，且要贴合主题改写（愤怒主题用"它在烧"/"火小了"/"熄了"）。

---

### UI 层的 CSS（极简、不打扰）

```css
#ui-layer {
    position: fixed; inset: 0;
    z-index: 20;
    pointer-events: none;          /* 不挡 canvas 交互 */
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    color: rgba(255,255,255,0.85);
    font-family: 'Georgia', 'Songti SC', serif;  /* 衬线感更疗愈 */
    text-align: center;
    user-select: none;
}
#title {
    font-size: clamp(28px, 5vw, 56px);
    font-weight: 300;
    letter-spacing: 0.15em;
    text-shadow: 0 0 20px rgba(0,0,0,0.8), 0 0 40px rgba(100,150,255,0.3);
    margin-bottom: 18px;
    transition: opacity 0.8s;
}
#hint {
    font-size: clamp(13px, 2vw, 16px);
    font-weight: 300;
    letter-spacing: 0.25em;
    opacity: 0.6;
    text-shadow: 0 0 10px rgba(0,0,0,0.9);
    transition: opacity 0.8s;
}
```

> `pointer-events: none` 是关键——UI 层浮在最上但不挡交互，所有点击穿透到 canvas。

---

## 五、相机动力学（被严重低估的沉浸感来源）

archetype《释·茧》验证了一个关键事实：**相机本身就该参与叙事**。焦虑时相机轻微抖动（强化"不安"），治愈时缓慢拉远（"退一步欣赏"）。这点几乎没人做，但效果立竿见影：

```javascript
function updateCamera(time) {
    if (State.healed) {
        // 治愈：缓慢拉远，"退一步欣赏"
        camera.position.z += (200 - camera.position.z) * 0.005;
        camera.position.x *= 0.95;
        camera.position.y *= 0.95;
    } else {
        // 焦虑：相机抖动，越焦虑抖得越厉害
        const shake = (1.0 - State.calm) * 0.6;
        camera.position.x = Math.sin(time * 20) * shake;
        camera.position.y = Math.cos(time * 23) * shake;   // x/y 用不同频率，避免机械感
        camera.position.z += (160 - camera.position.z) * 0.02;
    }
    camera.lookAt(0, 0, 0);
}
```

> 调参要点：`shake` 系数 `0.3~0.8`；频率用两个**互质**的数（如 20 和 23），否则抖动会周期性同步，显得假。治愈态拉远的 target `200` 比初始 `160` 远约 25%，足够明显但不至于看不清。

## 六、自动运镜入场（页面加载时必做）

相机不能"就那么出现"。加载后执行入场动作，建立空间感和仪式感。

### Dolly Zoom（希区柯克变焦）——推荐默认

相机从极远处快速推近 + FOV 同时收窄，产生"空间压缩"的沉浸入口：

```javascript
const entryDuration = 2.5; // 秒
let entryProgress = 0;

function easeInOutCubic(x) {
    return x < 0.5 ? 4*x*x*x : 1 - Math.pow(-2*x + 2, 3) / 2;
}

function entryDollyZoom(dt) {
    if (entryProgress >= 1) return;
    entryProgress = Math.min(1, entryProgress + dt / entryDuration);
    const t = easeInOutCubic(entryProgress);
    camera.position.z = 500 - 340 * t;    // 500 → 160
    camera.fov = 90 - 40 * t;             // 90°(广角) → 50°(标准)
    camera.updateProjectionMatrix();
}

// 主循环最前面调用
function loop() {
    if (entryProgress < 1) {
        entryDollyZoom(dt);
        renderer.render(scene, camera);
        requestAnimationFrame(loop);
        return; // 入场期间暂停交互
    }
    // ... 正常循环 ...
}
```

### Orbit 旋转入场——适合"探索/发现"类隐喻

```javascript
let entryAngle = Math.PI * 0.3; // 从侧面开始
function entryOrbit(dt) {
    entryAngle += (0 - entryAngle) * 0.03; // Lerp 归零
    camera.position.x = Math.sin(entryAngle) * 160;
    camera.position.z = Math.cos(entryAngle) * 160;
    camera.lookAt(0, 0, 0);
    if (Math.abs(entryAngle) < 0.001) entryComplete = true;
}
```

> 入场期间暂停用户交互。入场完成后恢复正常。
> 
> **入场→破坏过渡时序**：入场完成后**立即**触发 Act 2 破坏（0ms 延迟）。破坏动画本身有 1-2 秒渐变（墨迹从边缘渗入、外壳从顶部开始剥落），渐变期就是自然的视觉缓冲——不需要额外停顿。停顿 = 用户以为页面卡住了。

---

## 七、4-7-8 呼吸引导（治愈达成后的"留白"仪式）

archetype《释·茧》的做法：治愈达成（`calm>=1`）后**不结束**，而是进入一段持续的 4-7-8 呼吸引导——吸气 4 秒、屏息 7 秒、呼气 8 秒，共 19 秒一个周期。这是真实的临床放松法，让治愈不只是"到达"，而是"持续沉浸"。

```javascript
// 全局状态加一个 breathePhase 记录当前在哪个阶段
const breatheHint = document.getElementById('breathe-hint');

function computeBreathe(time) {
    if (!State.healed) return 0;          // 未治愈不引导
    const cycle = time % 19;              // 4 + 7 + 8 = 19s

    if (cycle < 4) {
        // 吸气 0→1
        if (State.breathePhase !== 1) {
            breatheHint.innerText = '吸气 ···';
            State.breathePhase = 1;
            Audio.strikeBowl(0.8);        // 开始吸气时轻敲颂钵
        }
        return cycle / 4;
    } else if (cycle < 11) {
        // 屏息 保持在 1
        if (State.breathePhase !== 2) {
            breatheHint.innerText = '屏息 ···';
            State.breathePhase = 2;
        }
        return 1.0;
    } else {
        // 呼气 1→0
        if (State.breathePhase !== 3) {
            breatheHint.innerText = '呼气 ···';
            State.breathePhase = 3;
            Audio.strikeBowl(0.4);        // 呼气时再轻敲一次，释放压力
        }
        return 1.0 - (cycle - 11) / 8;
    }
}
```

`breathe` 这个 0~1 的值用途极广（这是视听联觉的高阶用法）：
1. 传给 shader 的 `uBreathe` uniform → 粒子大小随呼吸起伏（吸气变大、呼气变小）
2. 传给 `Audio.update(calm, breathe)` → 海浪噪音的音量和滤波器跟随呼吸开合（吸气=浪起、呼气=浪落）
3. 驱动呼吸文字的 `transform: scale()` + `opacity` → 文字本身随吸气微微变大变亮，视觉引导更强

```javascript
// 呼吸文字跟随呼吸（在主循环里，State.showBreathUI 在治愈后 3 秒才置 true，留个停顿）
if (State.showBreathUI) {
    const s = 1.0 + breathe * 0.15;
    breatheHint.style.transform = `scale(${s})`;
    breatheHint.style.opacity = 0.3 + breathe * 0.7;
}
```

> **颂钵敲击时机**：不是匀速敲，而是卡在呼吸的"转换点"——吸气开始时强敲(0.8)、呼气开始时弱敲(0.4)。这让声音成为呼吸的"节拍器"，比任何视觉提示都有效。

## 八、进阶：可逆 vs 不可逆（决定体验的"重量感"）

| 类型 | 行为 | 适合主题 | 心理效果 |
|------|------|---------|---------|
| **可逆** | 松手 calm 回落 | 呼吸/正念/专注 | "平静需要持续维护"——日常修行感 |
| **不可逆** | calm 只升不降 | 剥落/释放/解构 | "一旦释放就回不去"——仪式感、解脱感 |

情绪释放类（愤怒、悲伤）用**不可逆**更有力量；正念呼吸类用**可逆**更真实。黄金范例用的是可逆（长按攒、松手回落），对应"呼吸"主题。

---

## 九、避免的坑

1. **不要让 calm 涨太快**。秒级达到终点会让用户觉得"这就完了？"——失去过程感。目标 15~40 秒走完全程。
2. **不要在 intro 阶段就把声音开足**。压抑阶段的声音应该也是"压抑"的（刺耳/低沉），随 calm 渐变到治愈音色。否则一开始就治愈了，没有弧线。
3. **complete 阶段要给"留白"**。不要一达到 100% 就弹窗或重置。让治愈的终态停留至少 5~10 秒，让用户体验"沉浸"本身。可以在 complete 后 15 秒才出现一个极淡的"重新开始"提示。
4. **阶段切换不要太频繁**。`phase` 只在三段间切，不要切成 5、6 段。段越多文案越碎，越像闯关游戏而非冥想。

---

## 速查：主题 → 状态机配置

| 主题 | 交互模式 | 可逆? | fromCol→toCol | 全程时长 |
|------|---------|-------|---------------|---------|
| 呼吸光球 | 长按攒气 | 可逆 | 暗红→暖白蓝 | ~20s |
| 化解愤怒 | 点击释放 | 不可逆 | 烈焰红→静水蓝 | ~25s (13击) |
| 枯山水 | 拖拽梳理 | 可逆 | 灰土→金砂 | ~30s |
| 专注共振 | 静止保持 | 可逆(易失) | 暗紫→金白 | 开放式 |
| 剥落自卑 | 点击剥落 | 不可逆 | 灰壳→璀璨暖金 | ~30s |
| 化雪归海 | 长按升温 | 不可逆 | 冰青→暖海蓝绿 | ~35s |

记住：**先定交互模式和 fromCol/toCol，其他参数都是衍生的**。这一步定对，作品就成了一半。

---

## 十、文案递进模式（Subtitle Progression）

三阶段文案不仅切 phase，还可以用 `calm` 的连续值驱动中间态的淡入淡出：

```javascript
const COPY = [
    { threshold: 0.0,  title: '这里很吵',     hint: '按住屏幕，让它安静下来' },
    { threshold: 0.3,  title: '正在平复',     hint: '继续，感受它的节律' },
    { threshold: 0.85, title: '安静了',       hint: '松手，它会记得这份平静' },
];

let activeIdx = 0;
function updateSubtitle(calm) {
    let targetIdx = 0;
    for (let i = COPY.length-1; i >= 0; i--) {
        if (calm >= COPY[i].threshold) { targetIdx = i; break; }
    }
    if (targetIdx !== activeIdx) {
        // 淡出 → 换字 → 淡入
        titleEl.style.opacity = 0;
        setTimeout(() => {
            titleEl.textContent = COPY[targetIdx].title;
            hintEl.textContent  = COPY[targetIdx].hint;
            titleEl.style.opacity = 1;
        }, 800);
        activeIdx = targetIdx;
    }
}
```

> `threshold` 数组定义每个文案的出现门槛。`calm` 从 0→1 的过程中，文案按门槛自动切换。

---

## 十一、文案节奏与视觉高潮同步

### 三段式文案结构

```
压抑态 → 命名（"这就是你现在的感受"）
转化中 → 陪伴（"它在变。你也在变。"）
释放后 → 见证（"它过去了。你在这里。"）
```

每阶段 1~2 句。绝不循环。文字数量越少越有力量。

### 金句在高潮时出现

不是一直挂在屏幕上——而是在粒子爆发/外壳剥落/雾气散开的瞬间淡入。视觉高潮 + 文字击中 = 双重锚定。

```javascript
function triggerClimax() {
    // 1. 视觉爆发
    PHYS.pulse = 60;
    Audio.strikeBowl(1.5);
    // 2. 文字同时出现
    climaxText.style.opacity = 0;
    climaxText.textContent = '它过去了。你在这里。';
    climaxText.style.transition = 'opacity 2s';
    setTimeout(() => { climaxText.style.opacity = 1; }, 50);
}
```

### 文案写作原则
- **看见，不说教**："这里很吵" > "你需要安静下来"
- **陪伴，不解救**："我看到了" > "你应该这样做"
- **见证，不总结**：终态文字只是安静地陈述一个事实，不给人生建议

---

## 十二、交互模式 E：拖拽操控时间（Drag-to-Manipulate-Time）

水平拖拽控制虚拟时间流速——左拖=倒拨，右拖=快进。适用于时钟、时间线、宇宙主题：

```javascript
let timeOffset = 0, lastDragX = 0, isDragging = false;

window.addEventListener('mousedown', e => { isDragging = true; lastDragX = e.clientX; });
window.addEventListener('mousemove', e => {
    if (!isDragging) return;
    timeOffset += (e.clientX - lastDragX) * 15; // 1px=15s
    lastDragX = e.clientX;
});
window.addEventListener('mouseup', () => { isDragging = false; });

// 主循环：
function updateTime(dt) {
    timeOffset *= 0.94; // 释放后缓慢归零
    return performance.now()/1000 + timeOffset;
}
```

> ⚠️ 此模式不适合触屏——单指拖拽已被页面滚动占用。如需移动端支持，用双指或限制在卡片容器内。

---

## 十三、交互模式 F：定时自动疗愈（Timed Auto-Healing）

不用交互，靠时间自动推进。适用于叙事型/被动体验型 H5：

```javascript
// 10 秒后自动触发疗愈
setTimeout(() => {
    isHealing = true;
    // ... 动画触发代码 ...
}, 10000);

// 使用 setInterval 控制焦虑元素生成速率（如每 120ms 弹出一个终端窗口）
const spawnInterval = setInterval(spawnThought, 120);

// 疗愈后清空
function triggerHealing() {
    clearInterval(spawnInterval);
    // GSAP 炸碎所有焦虑元素
    gsap.to(thoughts, {
        opacity: 0, scale: 2.5, filter: "blur(15px)",
        duration: 0.6, stagger: 0.005,
        onComplete: () => { container.innerHTML = ''; }
    });
}
```

> 自动疗愈的核心技巧：**累积焦虑 → 临界点爆发 → 清空**。让"焦虑期"足够长（10s+）积累代入感，爆发要瞬间、干脆（0.6s）。

---

## 速查新增

| 主题 | 交互模式 | 特殊参数 |
|------|---------|---------|
| 时间粒子时钟 | E: 拖拽操控时间 | 1px=15s，释放衰减 0.94 |
| 终端焦虑引擎 | F: 定时自动疗愈 | 10s 触发，120ms 弹窗，45 上限 |
| **长按安抚（最推荐）** | **G: 长按=安抚，松手=衰减** | **soothe 涨速 0.4/s，跌速 0.6/s（松手比按住掉得快）** |

---

## 十四、交互模式 G：长按安抚（最推荐用于疗愈类）

这是经过验证的"仪式感"交互——**一个连贯动作，一个清晰含义**。

```javascript
let isPressing = false;
let soothe = 0;

function startInteract() {
    isPressing = true;
    document.body.classList.add('pressing');
    createPulse(cx, cy); // 视觉反馈
    AudioSys.playPulse(); // 音频反馈——每次按压都播放
}
function endInteract() {
    isPressing = false;
    document.body.classList.remove('pressing');
}

// 主循环：
if (isPressing) {
    soothe = min(1, soothe + dt * 0.4);  // 按住涨
} else {
    soothe = max(0, soothe - dt * 0.6);  // 松手掉更快——需要持续投入
}
```

**光标随按压变形**（缩小=专注，放大=扩散）：
```css
#cur { width: 30px; height: 30px; transition: width 0.3s, height 0.3s; }
body.pressing #cur { width: 15px; height: 15px; } /* 按住缩小——聚焦 */
```

**引导文字智能显隐**（只在需要时出现，不打扰）：
```javascript
const hintEl = document.getElementById('hint');
// 第二幕开始 + 用户还没开始按压 → 显示引导
if (act === 2 && !act3_trigger && !isPressing) {
    hintEl.classList.add('show');
} else {
    hintEl.classList.remove('show');
}
```

> 引导文字样式：`animation: breatheHint 3s infinite alternate`（呼吸式淡入淡出），`font-weight: 200; letter-spacing: 4px;`，放在底部 8vh。不喧宾夺主。

---

## 十五、高潮触发条件设计（反模式对照）

**❌ 错误：自动触发**
```javascript
// 等 soothe 自然衰减到阈值就触发——用户没有参与感
if (soothe < 0.03 && !climax) { climax = true; }
```

**✅ 正确：挣来的高潮**
```javascript
// 四个条件同时满足：
// 1. act3 已触发（用户已经开始安抚）
// 2. 用户正在按压（主动在做）
// 3. 时间超过阈值（不能秒达——过程感）
// 4. 所有暗线被推回足够远（视觉上能看到结果）
if (act3_trigger && isPressing && S_time > 15 && !climax) {
    let allClear = true;
    for (let d of darkLines) {
        if (dist(cx, cy, d.x, d.y) < 300) allClear = false;
    }
    if (allClear) { climax = true; changeText("秩序回来了。是我让它回来的。"); }
}
```

> **核心原则**：高潮触发条件里必须有一条是"用户的持续动作产生了可见的结果"。用户必须能**看见自己的动作改变了画面**，然后才能感觉到"我做到了"。
