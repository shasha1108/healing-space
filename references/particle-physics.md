# Particle Physics — 粒子运动模型武器库

本文件是粒子运动方程的真实可复用代码。**照着改，不要从零发明。**

设计原则：每个粒子存 `position + velocity + home（归位点）`，每帧用欧拉积分（`v += a*dt; p += v*dt`）推进。所有"力"都是可叠加的加速度项。

## 目录

- [零、性能预算 ⚠️](#零性能预算踩坑后回灌的铁律)
- [一、数据布局](#一数据布局每个粒子要存什么)
- [二、初始分布生成](#二初始分布生成决定初始形态)（球面 / 球壳 / 立方云团 / 环面 / 文字形态）
- [三、核心力函数](#三核心力函数每帧叠加到加速度)（弹簧归位 / 鼠标斥力/引力 / 重力 / Curl Noise）
- [四、交互脉冲](#四交互脉冲点击瞬间的冲击波)
- [五、完整主循环结构](#五完整的主循环物理更新推荐结构)
- [六、dt 帧率无关处理](#六dt-的处理帧率无关)
- [速查：主题 → 物理配置](#速查主题--物理配置)

---

## ⚠️ 零、性能预算（踩坑后回灌的铁律）

**这是本文件最重要的一节。** 10 万级粒子最容易死在物理循环的 CPU 成本上——典型的"按住就卡死"bug 几乎都是因为这一节没遵守。

### 单帧 16ms 预算的硬约束

```
每帧总预算：16ms（60fps）/ 33ms（30fps 容忍线）
三角函数（sin/cos）单次成本：~75ns（V8/SpiderMonkey 实测）
→ 单帧可用于三角函数的预算：约 21 万次（16ms 全用光）
→ 留 50% 给渲染/状态机/音频后：约 10 万次
```

### 推导出的硬规则

| 规则 | 公式 | 反例（卡死） |
|------|------|------------|
| **每粒子三角函数 ≤ 3 次** | `COUNT × trigPerParticle ≤ 100k` | 14 万粒子 × 6 次 = 84 万次 ≈ 63ms ❌ |
| **不要在循环里访问对象属性** | 把 `PHYS.STIFF`、`mouse.x` 等提到局部常量 | 14 万次 `mouse.x` 属性查找 = 额外 8ms ❌ |
| **不要在循环里调用函数** | curl 直接内联展开，不调用 `curl()` | 14 万次函数调用 + 闭包 = 12ms ❌ |
| **不要在循环里 `new` 任何东西** | 复用 Vector3，或纯标量运算 | 14 万次 `new THREE.Vector3` = GC 爆炸 ❌ |

### 合格的物理循环骨架（14 万粒子，实测 ~8ms/帧）

```javascript
function updatePhysics(dt, time) {
    // ① 把所有要用的值提到局部变量——避免循环内属性查找
    const p = positions, vel = velocities, h = homes;
    const stiff = PHYS.STIFFNESS, damp = PHYS.DAMPING, curlS = PHYS.CURL_STRENGTH;
    const mx = mouse.x, my = mouse.y, mz = mouse.z, mActive = mouse.active;

    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        const px = p[i3], py = p[i3+1], pz = p[i3+2];   // 一次性读出

        // ② 弹簧归位（无三角函数）
        let ax = (h[i3]   - px) * stiff;
        let ay = (h[i3+1] - py) * stiff;
        let az = (h[i3+2] - pz) * stiff;

        // ③ curl 扰动：每轴一次三角函数（共 3 次）——见下方"合格 curl"
        ax += Math.sin(py * 0.05 + time * 0.3) * curlS;
        ay += Math.sin(pz * 0.05 + time * 0.25) * curlS;
        az += Math.sin(px * 0.05 + time * 0.2) * curlS;

        // ④ 积分（无三角函数）
        vel[i3]   = (vel[i3]   + ax * dt) * damp;
        vel[i3+1] = (vel[i3+1] + ay * dt) * damp;
        vel[i3+2] = (vel[i3+2] + az * dt) * damp;
        p[i3]   += vel[i3]   * dt;
        p[i3+1] += vel[i3+1] * dt;
        p[i3+2] += vel[i3+2] * dt;
    }
    geo.attributes.position.needsUpdate = true;
}
```

### 自检清单（写完物理循环必查）

1. 循环体内 `Math.sin`/`Math.cos` 总次数 × COUNT ≤ 100,000？
2. 循环体内有没有 `.` 访问对象属性（除了 `p[i3]` 这种数组下标）？
3. 循环体内有没有函数调用？
4. 循环体内有没有 `new`？
5. 所有 `PHYS.xxx` / `mouse.xxx` 是否都在循环前提到了局部变量？

任一项不满足，14 万粒子场景就会卡。

---

## 一、数据布局（每个粒子要存什么）

```javascript
const COUNT = 150000;
const positions = new Float32Array(COUNT * 3);  // 当前位置（喂给 geometry）
const velocities = new Float32Array(COUNT * 3); // 速度
const homes      = new Float32Array(COUNT * 3); // 归位目标点（弹簧力的锚）
// 可选：seeds（每粒子的随机相位，用于扰动差异化）
const seeds = new Float32Array(COUNT);
for (let i = 0; i < COUNT; i++) seeds[i] = Math.random();
```

> `homes` 是关键概念：很多效果（球面、网格、文字、曼陀罗）的本质是"给每粒子指定一个目标位置，再用弹簧力把它拉回去"。

---

## 二、初始分布生成（决定初始形态）

### 球面分布（光球、能量核心）

```javascript
function distributeSphere(radius = 60) {
    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        // 均匀球面采样：u,v 在 [0,1]
        const u = Math.random();
        const v = Math.random();
        const theta = 2 * Math.PI * u;
        const phi   = Math.acos(2 * v - 1);
        const r     = radius * Math.cbrt(Math.random()); // 立方根→实心球
        positions[i3]   = r * Math.sin(phi) * Math.cos(theta);
        positions[i3+1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i3+2] = r * Math.cos(phi);
        homes[i3]=positions[i3]; homes[i3+1]=positions[i3+1]; homes[i3+2]=positions[i3+2];
    }
}
```

### 球壳（空心光球，更亮）

把上面 `r = radius * Math.cbrt(Math.random())` 改成 `r = radius * (0.95 + Math.random()*0.05)`。

### 立方云团（混沌初始态）

```javascript
function distributeCube(size = 200) {
    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        positions[i3]   = (Math.random()-0.5) * size;
        positions[i3+1] = (Math.random()-0.5) * size;
        positions[i3+2] = (Math.random()-0.5) * size;
        homes[i3]=positions[i3]; homes[i3+1]=positions[i3+1]; homes[i3+2]=positions[i3+2];
    }
}
```

### 环面 / 涟漪（枯山水、曼陀罗）

```javascript
function distributeRing(innerR = 40, outerR = 80) {
    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        const a = Math.random() * Math.PI * 2;
        const r = innerR + Math.random() * (outerR - innerR);
        positions[i3]   = Math.cos(a) * r;
        positions[i3+1] = (Math.random()-0.5) * 4;  // 薄薄一层
        positions[i3+2] = Math.sin(a) * r;
        homes[i3]=positions[i3]; homes[i3+1]=positions[i3+1]; homes[i3+2]=positions[i3+2];
    }
}
```

### 文字形态（极有力的治愈隐喻：从混沌聚成一句话）

```javascript
// 思路：用 2D canvas 画文字 → 读像素 → 亮像素坐标作为 homes
function distributeFromText(text = '释', fontSize = 300) {
    const c = document.createElement('canvas');
    c.width = 512; c.height = 512;
    const cx = c.getContext('2d');
    cx.fillStyle = '#000'; cx.fillRect(0,0,512,512);
    cx.fillStyle = '#fff';
    cx.font = `bold ${fontSize}px serif`;
    cx.textAlign = 'center'; cx.textBaseline = 'middle';
    cx.fillText(text, 256, 256);
    const data = cx.getImageData(0,0,512,512).data;
    const pts = [];
    for (let y=0;y<512;y+=2) for (let x=0;x<512;x+=2) {
        if (data[(y*512+x)*4] > 128) pts.push([x-256, -(y-256)]); // y 翻转
    }
    for (let i = 0; i < COUNT; i++) {
        const i3 = i*3;
        const [hx, hy] = pts[Math.floor(Math.random()*pts.length)];
        homes[i3]   = hx * 0.3;
        homes[i3+1] = hy * 0.3;
        homes[i3+2] = (Math.random()-0.5) * 10;
        // 初始位置随机散布（混沌），靠弹簧力慢慢聚成字
        positions[i3]   = (Math.random()-0.5)*400;
        positions[i3+1] = (Math.random()-0.5)*400;
        positions[i3+2] = (Math.random()-0.5)*200;
    }
}
```

> 这是"《释·茧》"那类作品的原理。文字一定要繁体/书法感强的字（释、静、息、空、和）。

---

## 三、核心力函数（每帧叠加到加速度）

### 弹簧归位力（把粒子拉回 home）

最常用。让粒子"记住"自己的位置，被扰动后慢慢归位。

**关键技法（archetype《太极时钟》验证）：每粒子用独立的刚度 `k`，而非全局 STIFFNESS。** 不同部件用不同刚度 → 行为层次丰富：刻度强（稳）、秒针强（干脆）、时针弱（厚重拖沓）、分针中（流体感）。这是让画面"有层次"的核心：

```javascript
// init 时给每个粒子分配 k（按类型/位置）
for (let i = 0; i < COUNT; i++) {
    // 例：外圈粒子刚度大（稳固），内圈小（柔软）
    const k = 0.02 + 0.06 * (homes[i*3] 的半径 / MAX_RADIUS);
    particleK[i] = k;   // 存一个独立数组
}

// 在主循环里，对每个粒子 i：
const i3 = i*3;
const k = particleK[i];                        // 每粒子独立刚度
const ax = (homes[i3]   - positions[i3])   * k;   // 弹簧
const ay = (homes[i3+1] - positions[i3+1]) * k;
const az = (homes[i3+2] - positions[i3+2]) * k;
velocities[i3]   += ax * dt;
velocities[i3+1] += ay * dt;
velocities[i3+2] += az * dt;
// 阻尼（摩擦），否则永远振荡
velocities[i3]   *= DAMPING;
velocities[i3+1] *= DAMPING;
velocities[i3+2] *= DAMPING;
// 积分
positions[i3]   += velocities[i3]   * dt;
positions[i3+1] += velocities[i3+1] * dt;
positions[i3+2] += velocities[i3+2] * dt;
```

> archetype《太极时钟》的刚度配方（参考）：表盘刻度 `k=0.08`（极稳，不易打散）、秒针 `k=0.06`（干脆）、分针 `k=0.03`（流体感）、时针 `k=0.02`（厚重拖沓）。四种刚度让四种部件各有性格。

**简化场景**（单形态光球）：如果所有粒子是同一种（如纯球面光球），用全局 STIFFNESS 也行（`STIFFNESS=0.6+2.0*calm`，随治愈进度从软变硬）。**只有当画面有多种部件/层次时，才必须用每粒子独立 k**。

**调参**：`k = 0.02~0.15`（越大归位越快越硬），`DAMPING = 0.85~0.96`（越小停得越快）。焦虑态用低 k + 低阻尼（软而振荡，躁动感）；治愈态用高 k + 高阻尼（硬而安定）。

### 鼠标斥力（点击/拖拽推开粒子）

```javascript
// mouseWorld 是鼠标在 3D 空间的投影点
const dx = positions[i3]   - mouseWorld.x;
const dy = positions[i3+1] - mouseWorld.y;
const dz = positions[i3+2] - mouseWorld.z;
const dist2 = dx*dx + dy*dy + dz*dz;
const dist  = Math.sqrt(dist2) + 0.001;
if (dist < REPEL_RADIUS) {
    const force = (1 - dist/REPEL_RADIUS) * REPEL_STRENGTH;
    velocities[i3]   += (dx/dist) * force;
    velocities[i3+1] += (dy/dist) * force;
    velocities[i3+2] += (dz/dist) * force;
}
```

**调参**：`REPEL_RADIUS = 30~80`，`REPEL_STRENGTH = 5~20`。点击瞬间设 strength 大、半径大；持续拖拽时持续施加。

### 鼠标引力（吸引粒子聚集，做"聚拢"效果）

把上面 `+=` 改成 `-=` 即可。

### 重力（坠落雨滴、剥落碎片）

```javascript
velocities[i3+1] -= GRAVITY * dt;   // y 轴向下（Three.js 里 -y 通常向下）
// 触底反弹或回收
if (positions[i3+1] < -FLOOR) {
    positions[i3+1] = -FLOOR;
    velocities[i3+1] *= -0.3;   // 弱反弹
}
```

### Curl Noise 流体扰动（让粒子像烟雾、星云般卷动）

最"高级"的力。伪 curl noise 用正弦叠加近似旋度场，比真 Perlin 快得多。

> ⚠️ **性能陷阱（回灌）**：早期版本写成 `curl(x,y,z,t)` 函数、每轴 2 个三角函数（共 6 次），14 万粒子调用 = **84 万次三角函数 ≈ 63ms/帧，直接卡死**。必须用下面"合格版"——**内联、每轴只 1 次三角函数（共 3 次）**。

#### ❌ 不合格版（会卡死，禁止使用）

```javascript
// 反例：函数调用 + 每轴 2 次 trig = 6 次/粒子
function curl(x, y, z, t) {
    const n1 = Math.sin(y*0.05 + t*0.3) + Math.cos(z*0.05 + t*0.2);
    const n2 = Math.sin(z*0.05 + t*0.25) + Math.cos(x*0.05 + t*0.3);
    const n3 = Math.sin(x*0.05 + t*0.2) + Math.cos(y*0.05 + t*0.25);
    return [n1*0.5, n2*0.5, n3*0.5];
}
// 主循环里调用：const [cx,cy,cz] = curl(px,py,pz,time);  ← 14 万次函数调用 + GC
```

#### ✅ 合格版（内联，每轴 1 次 trig，共 3 次）

```javascript
// 在主循环内，直接内联（参考"零、性能预算"的骨架）
const curlS = PHYS.CURL_STRENGTH;
// ...循环体内：
ax += Math.sin(py * 0.05 + time * 0.3) * curlS;
ay += Math.sin(pz * 0.05 + time * 0.25) * curlS;
az += Math.sin(px * 0.05 + time * 0.2) * curlS;
```

**调参**：`CURL_STRENGTH = 3~15`（回灌修正：旧文档写 5~30 偏大，14 万粒子下 >15 会让弹簧归位失效）。配低阻尼（`DAMPING=0.98`）时粒子会持续卷动，像星云。**先让弹簧力主导（粒子稳定），再加 curl（有生命感）**——一次性全开会很乱。

**进阶：三层叠加消除重复周期。** 单层 Curl 仍有可感知的重复。用三个不同频率且互质的缩放因子叠加（`小*0.03 + 中*0.015 + 大*0.007`），让周期交错——人眼无法锁定任何一个频率。实现方式：在上方内联 curl 的三行中，每行分别乘以 0.03/0.015/0.007 再求和。

---

## 四、交互脉冲（点击瞬间的冲击波）

点击不只是给鼠标位置加斥力，而是发一个**全局脉冲**，所有粒子按距离衰减被推开：

```javascript
let pulseStrength = 0;   // 全局，每次 click 设一个值，每帧衰减

function onClick(e) {
    pulseStrength = 50;   // 冲击波强度
}

// 主循环里，对每个粒子：
if (pulseStrength > 0) {
    // 从屏幕中心（或点击点）向外推
    const dx = positions[i3];
    const dy = positions[i3+1];
    const dz = positions[i3+2];
    const d = Math.sqrt(dx*dx+dy*dy+dz*dz) + 0.001;
    velocities[i3]   += (dx/d) * pulseStrength * dt;
    velocities[i3+1] += (dy/d) * pulseStrength * dt;
    velocities[i3+2] += (dz/d) * pulseStrength * dt;
}
pulseStrength *= 0.9;   // 每帧衰减
```

---

## 五、完整的主循环物理更新（推荐结构）

把所有力整合到一个 `updatePhysics(dt)` 里。注意循环顺序：**收集力 → 积分 → 阻尼 → 边界处理**：

```javascript
const PHYS = {
    STIFFNESS: 1.2, DAMPING: 0.94,
    REPEL_RADIUS: 50, REPEL_STRENGTH: 12,
    CURL_STRENGTH: 8, GRAVITY: 0,
    pulse: 0,
};

function updatePhysics(dt, time, mouse) {
    // ① 全部提到局部变量（避免循环内属性查找）
    const p = positions, v = velocities, h = homes;
    const stiff = PHYS.STIFFNESS, damp = PHYS.DAMPING;
    const curlS = PHYS.CURL_STRENGTH, grav = PHYS.GRAVITY;
    const repelR = PHYS.REPEL_RADIUS, repelR2 = repelR*repelR, repelS = PHYS.REPEL_STRENGTH;
    const mx = mouse.x, my = mouse.y, mz = mouse.z, mActive = mouse.active;
    const pulse = PHYS.pulse;

    for (let i = 0; i < COUNT; i++) {
        const i3 = i*3;
        const px = p[i3], py = p[i3+1], pz = p[i3+2];   // 一次性读出

        // 1. 弹簧归位力（无 trig）
        let ax = (h[i3]   - px) * stiff;
        let ay = (h[i3+1] - py) * stiff;
        let az = (h[i3+2] - pz) * stiff;

        // 2. Curl noise 扰动（内联，每轴 1 次 trig，共 3 次 —— 见"性能预算"）
        ax += Math.sin(py * 0.05 + time * 0.3) * curlS;
        ay += Math.sin(pz * 0.05 + time * 0.25) * curlS;
        az += Math.sin(px * 0.05 + time * 0.2) * curlS;

        // 3. 鼠标斥力
        if (mActive) {
            const dx = px-mx, dy = py-my, dz = pz-mz;
            const d2 = dx*dx+dy*dy+dz*dz;
            if (d2 < repelR2) {
                const d = Math.sqrt(d2)+0.001;
                const f = (1 - d/repelR) * repelS;
                ax += (dx/d)*f; ay += (dy/d)*f; az += (dz/d)*f;
            }
        }

        // 4. 点击脉冲（全局，仅在触发时进入分支，无 trig）
        if (pulse > 0.1) {
            const d = Math.sqrt(px*px+py*py+pz*pz)+0.001;
            ax += (px/d)*pulse; ay += (py/d)*pulse; az += (pz/d)*pulse;
        }

        // 5. 积分 + 阻尼 + 重力（无 trig）
        v[i3]   = (v[i3]   + ax * dt) * damp;
        v[i3+1] = (v[i3+1] + ay * dt - grav * dt) * damp;
        v[i3+2] = (v[i3+2] + az * dt) * damp;

        // 6. 位置更新
        p[i3]   += v[i3]   * dt;
        p[i3+1] += v[i3+1] * dt;
        p[i3+2] += v[i3+2] * dt;
    }
    PHYS.pulse *= 0.9;
    geo.attributes.position.needsUpdate = true;
}
```

---

## 六、dt 的处理（帧率无关）

不要直接用 `1/60`，要用真实帧间隔，否则不同设备物理速度不一致：

```javascript
let lastT = performance.now();
function loop() {
    const now = performance.now();
    let dt = (now - lastT) / 1000;
    dt = Math.min(dt, 0.033);   // 钳制：切后台再回来不会大跳
    lastT = now;

    updatePhysics(dt, now/1000, mouse);
    // ...
    requestAnimationFrame(loop);
}
```

---

## 速查：主题 → 物理配置

| 主题 | 初始分布 | 主力 | 鼠标交互 | 脉冲 |
|------|---------|------|---------|------|
| 光球/能量核 | 球面/球壳 | 弹簧归位 + 弱 curl | 斥力 | 点击爆开 |
| 烟雾/星云 | 立方云团 | 强 curl + 弱弹簧 | 引力聚拢 | 无 |
| 雨滴/碎片坠落 | 顶部带状 | 重力 + 弱弹簧 | 击碎（强斥力） | 点击击碎 |
| 枯山水涟漪 | 环面 | 弹簧 + 沿切向 curl | 拖拽产生同心波 | 无 |
| 文字聚形 | 散布→文字 home | 强弹簧 | 斥力打散 | 无 |
| 剥落/解构 | 壳形态 | 重力 + 失去 home | 摩擦触发剥落 | 点击剥一片 |

调参的"手感"：先让弹簧力主导（粒子稳定），再加 curl（有生命感），最后加交互力（响应人）。一次性全开会很乱。

---

## 七、复杂目标拓扑（Complex Target Shapes）

基础分布（球/环/立方）之外的高级几何目标。

### 太极阴阳拓扑

```javascript
const TAI_CHI_RADIUS = 45;

function distributeTaiji() {
    for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        // 在太极图范围内随机撒点作为 homes
        const angle = Math.random() * Math.PI * 2;
        const r = Math.random() * TAI_CHI_RADIUS;
        const tx = Math.cos(angle) * r;
        const ty = Math.sin(angle) * r;

        // 判断阴阳
        let isYang = tx > 0;
        const distTop = Math.sqrt(tx*tx + (ty - TAI_CHI_RADIUS/2)**2);
        const distBot = Math.sqrt(tx*tx + (ty + TAI_CHI_RADIUS/2)**2);
        if (distTop < TAI_CHI_RADIUS/2) isYang = true;
        if (distBot < TAI_CHI_RADIUS/2) isYang = false;
        // 鱼眼（反向点）
        if (distTop < TAI_CHI_RADIUS/6) isYang = false;
        if (distBot < TAI_CHI_RADIUS/6) isYang = true;

        homes[i3]   = tx;
        homes[i3+1] = ty;
        homes[i3+2] = (Math.random() - 0.5) * 3;
        // 颜色：阳=白/暖金，阴=黑/深蓝
        if (isYang) {
            colTo[i3]=0.95; colTo[i3+1]=0.9; colTo[i3+2]=0.8;
        } else {
            colTo[i3]=0.05; colTo[i3+1]=0.08; colTo[i3+2]=0.2;
        }
        // 初始散布（混沌态）
        positions[i3]   = (Math.random()-0.5)*300;
        positions[i3+1] = (Math.random()-0.5)*300;
        positions[i3+2] = (Math.random()-0.5)*100;
    }
}
```

### 星系螺旋（银河治愈目标）

```javascript
// 每粒子存储：healR（距离中心）, healTheta（角度偏移）
for (let i = 0; i < COUNT; i++) {
    const healR = 10 + Math.pow(Math.random(), 1.5) * 100; // 幂分布：中心密、外疏
    const healTheta = Math.random() * Math.PI * 2;

    // 主循环中将角度随时间旋转：
    // const rotSpeed = 0.3 * (50 / (healR + 10)); // 内圈快、外圈慢
    // const targetX = Math.cos(healTheta + time * rotSpeed) * healR;
    // const targetY = (Math.random() - 0.5) * (15 - healR * 0.1);
    // const targetZ = Math.sin(healTheta + time * rotSpeed) * healR;
}
```

### 模拟时钟指针几何

```javascript
const PI2 = Math.PI * 2;
for (let i = 0; i < COUNT; i++) {
    const type = Math.random() < 0.6 ? 0 : (i % 3 + 1); // 0=表盘刻度(60%), 1/2/3=针
    // type 0: 均匀分布在外圈 → homes 固定
    // type 1/2/3: 沿指针线性分布 → homes 随角度实时更新
    let r, theta;
    if (type === 0) {
        r = 45 + Math.random() * 3;
        theta = Math.random() * PI2;
    } else {
        r = Math.random() * (type === 1 ? 16 : type === 2 ? 35 : 40);
        theta = secAngle + (Math.random() - 0.5) * (type === 3 ? 0.03 : 0.06);
    }
    particleType[i] = type;
    // 每粒子刚度：表盘 0.08(极稳) / 秒针 0.06 / 分针 0.03 / 时针 0.02
    particleK[i] = type === 0 ? 0.08 : (0.08 - type * 0.02);
}
```

> 关键思想：不同 `type` 的粒子用不同 `k`（刚度），产生"表盘刻度纹丝不动、秒针干脆利落、时针厚重拖沓"的物理层次。

---

## 八、虚拟时间偏移（Drag-to-Rewind）

拖拽水平方向来加速/减速/倒转"时间"（粒子运动的速度/方向）：

```javascript
const timeState = { offsetSeconds: 0, speedMultiplier: 1 };
let dragStartX = 0;

window.addEventListener('mousedown', e => { dragStartX = e.clientX; });
window.addEventListener('mousemove', e => {
    if (e.buttons) {
        timeState.offsetSeconds += (e.clientX - dragStartX) * 15; // 1px = 15s
        dragStartX = e.clientX;
    }
});

function updateTime(dt) {
    // 释放后偏移逐渐归零
    timeState.offsetSeconds *= 0.94;
    const virtualTime = performance.now()/1000 + timeState.offsetSeconds;
    timeState.speedMultiplier = 1 + Math.abs(timeState.offsetSeconds) * 0.1;
    return virtualTime;
}
```

> 应用场景：粒子时钟（拖拽=倒拨/快进时间）、宇宙时间线（拖拽=穿梭时空）。

---

## 速查新增：复杂拓扑

| 主题 | 初始分布 | home 形状 | 特殊技法 |
|------|---------|----------|---------|
| 太极/水墨 | 随机散布 | 太极拓扑 | 按住→收敛成太极，松手→散开 |
| 银河/宇宙 | 球面混沌 | 星系螺旋 | `pow(random, 1.5)` 幂分布 + 角度旋转 |
| 时钟/机械 | 随机散布 | 指针线段 | 4 类型粒子 × 4 种刚度 + 实时角度更新 |
