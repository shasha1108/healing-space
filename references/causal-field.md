# 因果场架构 — calm 作为单一真相源

> 设计哲学源自 Three.js Awesome Graphics 的 causal field 模式（一个地质场 → 驱动颜色/粗糙度/金属度/法线/发光）。适配到 healing-space：**calm 就是那个地质场。所有用户可感知的视觉/音频参数，必须从 calm 这一个值派生。**
>
> 本文件是 `state-machine.md §三` 的系统化扩展——从"示例"变成"规范"。不替代 state-machine.md，而是定义 calm 总线的完整契约。
>
> **加载时机**：STEP 5"应用四大维度"执行时必读（与 particle-physics.md / gpu-fluid.md / shader-patterns.md 同级，且应在它们之前读取——本文件定义参数如何绑定 calm，那些文件定义参数如何实现）。
>
> **触发条件**：所有场景。calm 总线是 healing-space 的架构常量，无论隐喻是什么、技术路线是什么。

---

## 一、核心声明

```
calm ∈ [0, 1] 是 healing-space 场景中唯一的全局状态变量。

0 = 初始压抑态（焦虑/疲惫/愤怒/孤独的峰值）
1 = 治愈终态（平静/释放/被看见）

所有用户可感知的视觉、物理、音频参数都是 calm 的函数。
不存在"独立于 calm 的视觉参数"——如果有，它就是错的。
```

**为什么这是架构常量而非可选模式：**

healing-space 的核心哲学是"情绪有形状、有温度、有过程"。三幕剧结构（美好→破坏→修复）的数学表达就是 `calm: 0→1`。如果场景中有参数不随 calm 变化，那么在三幕剧推进时，那些参数会说"我还在第一幕"——用户看到的世界是分裂的：墨水被擦掉了，但雾没散、粒子还在焦虑地乱窜、噪音还在响。

**这是"Always Lerp. Never linear."在参数空间维度的等价表达：** Lerp 保证时间维度的平滑，因果场保证参数空间的一致性。

---

## 二、参数映射表（按技术路线）

### 2.1 通用参数（所有技术路线共享）

| 参数 | calm=0（压抑态） | calm=1（治愈态） | 映射公式 | 说明 |
|------|-----------------|-----------------|---------|------|
| `ts`（smoothstep 缓动） | 0 | 1 | `c*c*(3-2*c)` | **所有过渡类参数必须用 ts 而非裸 c**。线性过渡中段太平、两端太突兀 |
| FogExp2 density | 0.003 | 0.0008 | `0.003 - 0.0022*ts` | 压抑态雾浓（视野压抑），治愈态雾散（视野开阔） |
| 环境光强度（Three.js） | 0.3 | 0.9 | `0.3 + 0.6*ts` | 压抑态昏暗，治愈态明亮 |
| 背景 CSS 亮度 | 0.15 | 0.55 | `0.15 + 0.4*ts` | p5.js 场景用 CSS 背景模拟环境光 |
| 相机抖动幅度 | `0.6*(1-c)` | 0 | `0.6*(1-c)` | 焦虑时相机微抖（强化不安），治愈后静止 |
| 相机 FOV | 窄（压抑感） | 宽（开阔感） | `50 + 20*ts` | 从 50° 到 70°，空间"打开" |
| 相机 z 轴 | 近（压迫） | 远（退一步） | `150 + 50*ts` | 治愈后缓慢拉远——"退一步欣赏" |

### 2.2 Three.js 粒子系统（最通用）

> 具体实现参数见 `particle-physics.md` 和 `shader-patterns.md`。本表只定义**绑定的数学关系**。

| 参数 | calm=0 | calm=1 | 映射公式 | 绑定位置 |
|------|--------|--------|---------|---------|
| CURL_STRENGTH | 20 | 2 | `20 - 18*ts` | JS: `PHYS.CURL_STRENGTH` |
| STIFFNESS | 0.5 | 2.5 | `0.5 + 2.0*ts` | JS: `PHYS.STIFFNESS` |
| DAMPING | 0.92 | 0.98 | `0.92 + 0.06*ts` | JS: `PHYS.DAMPING` |
| 粒子全局大小 | 0.6 | 2.0 | `0.6 + 1.4*ts` | GPU: `uGlobalSize` uniform |
| 颜色过渡 | colFrom | colTo | `mix(colFrom, colTo, ts)` | GPU: `uTransition` uniform |
| 粒子速度 | 1.0 | 0.4 | `1.0 - 0.6*ts` | JS: 粒子速度乘数 |

**治愈态的物理含义**：高刚度 + 高阻尼 + 低 Curl = 粒子趋向"归位"——像平静的水面，微微荡漾而非翻涌。压抑态的物理含义：低刚度 + 低阻尼 + 高 Curl = 粒子被外力推动后剧烈反弹——像沸腾的思绪。

### 2.3 FBO 流体模拟

> 具体实现见 `gpu-fluid.md`。流体 Shader 的 uniform 绑定。

| 参数 | calm=0 | calm=1 | 映射公式 | 绑定位置 |
|------|--------|--------|---------|---------|
| 扩散速度 | 0.97 | 0.995 | `0.97 + 0.025*ts` | Shader uniform `uDiffusion` |
| 密度衰减 | 0.98 | 0.92 | `0.98 - 0.06*ts` | Shader uniform `uDecay` |
| 画笔力度 | 1.0 | 0.3 | `1.0 - 0.7*ts` | JS: brush strength multiplier |
| 墨水颜色 | 浓黑/深色 | 浅色/透明 | `mix(inkDark, inkLight, ts)` | Shader uniform `uInkColor` |
| 背景颜色 | 压抑底色 | 治愈底色 | `mix(bgDark, bgLight, ts)` | Shader uniform `uBgColor` |

**治愈态的流体含义**：扩散快（墨迹迅速消散）、衰减慢（净化后的水保持清澈）、画笔弱（不需要用力擦了——已经干净了）。压抑态相反：扩散慢（墨迹滞留在水中）、衰减快但画笔强（需要用力才能推开）。

### 2.4 p5.js 流场 / 有机线条

> 具体实现见 `p5-patterns.md`。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 噪声缩放（Noise Scale） | 0.03 | 0.008 | `0.03 - 0.022*ts` | 压抑态噪声密集（短促转折），治愈态舒展 |
| 笔触速度 | 快 | 慢 | `2.0 - 1.2*ts` | 压抑态笔触急促，治愈态从容 |
| 笔触透明度 | 0.6 | 0.25 | `0.6 - 0.35*ts` | 压抑态痕迹重，治愈态轻盈 |
| 背景拖尾透明度 | 0.15 | 0.05 | `0.15 - 0.1*ts` | 压抑态残影重（混乱堆积），治愈态近乎无残影 |
| 粒子群落大小 | 小 | 大 | `1.5 + 2.5*ts` | 治愈态光点更大更柔和 |

### 2.5 Raymarching SDF

> 具体实现见 `raymarching.md`。⚠️ 仅单体抽象几何体场景使用。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 域扭曲强度 | 0.12 | 0.02 | `0.12 - 0.1*ts` | 压抑态扭曲强烈（形状躁动），治愈态近乎完美几何 |
| 表面发光强度 | 0.3 | 0.7 | `0.3 + 0.4*ts` | 压抑态暗沉，治愈态从内部发光 |
| 极光背景强度 | 0.2 | 0.6 | `0.2 + 0.4*ts` | 治愈态背景更亮更温暖 |
| Raymarch 步数 | 64 | 80 | `64 + 16*ts` | 治愈态更高精度（性能余裕时） |

### 2.6 CSS 平面叙事

> 具体实现见 `css-aesthetic.md`。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 毛玻璃 blur | 2px | 6px | `2 + 4*ts` | 压抑态清晰（尖锐），治愈态柔焦（柔软） |
| 背景色 | 压抑色 | 治愈色 | CSS `transition: background-color 0.8s` 或 JS `style.backgroundColor` | 从压抑色板渐变到治愈色板 |
| 文字透明度 | 0.9 | 0.6 | `0.9 - 0.3*ts` | 压抑态文字沉重，治愈态文字轻盈 |
| 元素间距 | 紧缩 | 舒展 | `1.0 + 0.5*ts` rem | 压抑态拥挤，治愈态呼吸 |

### 2.7 音频引擎

> 具体实现见 `audio-engine.md`。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 底噪 gain | 0.08 | 0 | `0.08*(1-c)` | 压抑态底噪强（建立不安地基），治愈态完全消失 |
| 治愈音色 gain | 0 | 0.05 | `0.05*c` | 治愈态轻柔音色升起 |
| 底噪低通滤波频率 | 1200Hz | 300Hz | `1200 - 900*ts` | 压抑态噪音刺耳（高频），治愈态噪音退远 |
| 颂钵音量 | 0 | 0.8 | `0.8*(c>0.95?1:0)` | 仅在高潮/治愈瞬间触发 |
| LFO 调制频率 | 4Hz | 1Hz | `4 - 3*ts` | 压抑态快速颤动（焦虑），治愈态缓慢呼吸 |

### 2.8 路径约束流

> 具体实现见 `code-snippets.md §贝塞尔路径约束流`。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 粒子速度 | 快（0.003） | 慢（0.001） | `0.003 - 0.002*ts` | 压抑态粒子急流，治愈态缓慢飘升 |
| 粒子数量 | 多 | 少 | `N*(1 - 0.5*ts)` | 治愈态部分粒子消散——不再需要那么多"表达" |
| 蜿蜒幅度 | 大（0.8） | 小（0.2） | `0.8 - 0.6*ts` | 压抑态流束剧烈蜿蜒，治愈态平稳 |
| 字符亮度（如有） | 高亮 | 柔和 | `1.0 - 0.4*ts` | 治愈态不需要"喊" |

### 2.9 Reaction-Diffusion（无序→有序）

> 具体实现见 `reaction-diffusion.md`。Gray-Scott 模型的参数绑定。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 喂入率 F | 0.025 | 0.045 | `0.025 + 0.02*ts` | 压抑态低喂入率（图案稀疏/碎片化），治愈态高喂入率（图案丰富/有序） |
| 杀死率 k | 0.062 | 0.055 | `0.062 - 0.007*ts` | 压抑态高杀死率（图案难以维持），治愈态低杀死率（图案稳定结晶） |
| 扩散速度 Du | 0.16 | 0.20 | `0.16 + 0.04*ts` | 治愈态扩散更快——有序结构更快形成 |
| 颜色过渡 | 压抑色板 | 治愈色板 | `mix(colFrom, colTo, ts)` | 图案颜色随 calm 从暗沉到明亮 |

**治愈态的 RD 含义**：高喂入率 + 低杀死率 + 快扩散 = 图案稳定、丰富、有序结晶。压抑态相反——图案碎片化、难以维持形态。

### 2.10 Physarum（孤独→连接）

> 具体实现见 `physarum.md`。粘菌信息素网络的参数绑定。

| 参数 | calm=0 | calm=1 | 映射公式 | 说明 |
|------|--------|--------|---------|------|
| 信息素扩散速度 | 0.5 | 0.9 | `0.5 + 0.4*ts` | 压抑态信息素滞留在原地（无法连接），治愈态信息素扩散远（建立连接） |
| 信息素衰减 | 0.02 | 0.005 | `0.02 - 0.015*ts` | 压抑态痕迹快速消失（孤独无记忆），治愈态痕迹持久（连接被记住） |
| Agent 转向角 | 大（45°） | 小（15°） | `45 - 30*ts` | 压抑态 Agent 随机乱转（无法定向），治愈态 Agent 沿信息素轨道稳定行进 |
| Agent 数量 | 少 | 多 | `N*(0.6 + 0.4*ts)` | 治愈态更多 Agent 参与网络构建 |
| 网络线宽 | 细 | 粗 | `0.5 + 1.0*ts` | 治愈态连接线更明显——"连接被看见了" |

**治愈态的 Physarum 含义**：信息素扩散远 + 衰减慢 = Agent 之间能互相找到 = **连接在形成、在持续**。压抑态：信息素来不及扩散就消失 = Agent 各自随机游走 = **没有连接、各自孤独**。这是"孤独→连接"隐喻的数学同构。

### 2.11 跨路线情绪强度校准

> 设计哲学源自 OceanThreejs 的频谱能量归一化：不同频谱（Phillips/JONSWAP/PM）在相同风速下产生不同振幅 → 归一化到同一有效波高 Hs。适配到 healing-space：**不同技术路线在同一个 calm 值下产生不同的视觉平静度 → 应用路线特定的 calm 偏置因子进行校准。**

#### 问题

当前每条技术路线的映射公式是独立定义的。但不同路线在 calm=0.5 时的"感知平静度"不同：

| 技术路线 | 主要视觉参数 | calm=0.5 时的感知状态 | 问题 |
|---------|------------|---------------------|------|
| **p5.js 流场** | 噪声缩放 0.03→0.008 | 笔触已明显变慢（感知 ~60% 平静） | 太快——在 calm=0.3 时就看起来"快结束了" |
| **Three.js 粒子** | CURL 20→2 | 粒子仍在剧烈旋转（感知 ~25% 平静） | 太慢——到 calm=0.7 才"刚开始安静" |
| **FBO 流体** | 扩散 0.97→0.995 | 墨迹扩散中等（感知 ~50% 平静） | 刚好——基准参照 |
| **Gerstner 海浪** | 波幅 1.0→0.1，choppiness 1.5→0 | 浪仍较尖锐（感知 ~35% 平静） | 偏慢——choppiness 的非线性导致中段过渡慢 |
| **路径约束流** | 粒子速度 0.003→0.001 | 粒子速度中等（感知 ~50% 平静） | 刚好 |

#### 校准方法

不是改变映射公式本身——是在 calm 值传入公式**之前**，应用路线特定的偏置因子。这是**一次性的线性映射**：

```javascript
// 路线校准因子——让所有路线在 calm=0.5 时达到 ~50% 的感知平静度
const ROUTE_CALM_BIAS = {
  'p5js-field':      { bias: -0.12 },  // 太快了——压低 calm 使过渡慢下来
  'particles':       { bias: +0.15 },  // 太慢了——抬高 calm 使过渡快一些
  'fbo-fluid':       { bias:  0.00 },  // 基准——不需要校准
  'gerstner-ocean':  { bias: +0.08 },  // 偏慢——微抬 calm
  'path-flow':       { bias:  0.00 },  // 刚好
  'reaction-diff':   { bias: -0.05 },  // 图案形成快——微压
  'physarum':        { bias: -0.05 },  // 连接形成快——微压
  'css-plane':       { bias:  0.00 },  // CSS 过渡是线性的——刚好
  'raymarching':     { bias:  0.00 },  // 域扭曲过渡非线性——暂不校准
};

/**
 * 应用路线校准——在 calm 传入映射公式之前调用
 * @param {number} rawCalm - 原始 calm 值（0~1）
 * @param {string} route - 技术路线标识
 * @returns {number} 校准后的 calm 值
 */
function calibrateCalm(rawCalm, route) {
  const cfg = ROUTE_CALM_BIAS[route];
  if (!cfg) return rawCalm;  // 未知路线——不使用偏置

  // 偏置因子：线性偏移 calm 值
  // bias > 0 → 视觉提前到达治愈态（用于"太慢"的路线）
  // bias < 0 → 视觉延迟到达治愈态（用于"太快"的路线）
  const calibrated = rawCalm + cfg.bias * rawCalm * (1 - rawCalm) * 4;
  // rawCalm * (1 - rawCalm) * 4 = 钟形曲线——在中段(0.5)影响最大，两端(0,1)影响为零
  return Math.max(0, Math.min(1, calibrated));
}
```

**偏置公式的设计原理**：`bias * calm * (1-calm) * 4` 是一个钟形曲线——
- 在 calm=0 处：影响 = 0（压抑态起点不变）
- 在 calm=0.5 处：影响 = bias × 0.25 × 4 = bias（最大校准效果）
- 在 calm=1 处：影响 = 0（治愈态终点不变）

**这保证校准只影响中段的过渡速度，不改变起点和终点。**

#### 使用方式

```javascript
// 在 applyCalmState 中——对每个技术路线使用校准后的 calm
const rawCalm = State.calm;
const calmParticles = calibrateCalm(rawCalm, 'particles');  // +0.15 偏置
const calmP5js     = calibrateCalm(rawCalm, 'p5js-field');  // -0.12 偏置
const calmFluid    = calibrateCalm(rawCalm, 'fbo-fluid');   // 0.00 不变

// 然后各路线用自己的校准值计算 ts 和映射
const tsParticles = calmParticles * calmParticles * (3 - 2 * calmParticles);
const tsP5js      = calmP5js * calmP5js * (3 - 2 * calmP5js);
```

#### 何时不校准

- 场景只有**一种**技术路线 → 不需要校准。校准的价值只在多路线混合场景中体现
- 校准因子是**可选**的——如果跳过，映射公式本身仍然是正确的，只是多路线之间的同步性有偏差

---

## 三、过渡一致性规则

### 规则 1：所有参数使用同一个 ts

```javascript
// ✅ 正确：所有系统从同一个 ts 派生
const c  = State.calm;
const ts = c * c * (3 - 2 * c);  // smoothstep

particleSystem.update(ts);       // 粒子用 ts
fluidSim.update(ts);             // FBO 用 ts
audioEngine.update(ts);          // 音频用 ts
cssTransition.update(ts);        // CSS 用 ts

// ❌ 错误：不同系统有各自的过渡变量
particleSystem.update(particleProgress);  // 粒子有自己的进度
fluidSim.update(fluidProgress);           // FBO 有自己的进度
audioEngine.setTarget(calm, 0.5);         // 音频有自己的时间线
```

### 规则 2：禁止独立时间线

`gain.setTargetAtTime(target, ctx.currentTime, 0.1)` 这种 Web Audio 内置平滑是允许的——它的 target 仍然是 `calm` 的函数。但以下做法是禁止的：

```javascript
// ❌ 禁止：音频用独立的 setTimeout 时间线
setTimeout(() => { droneGain.gain.value = 0; }, 8000);  // 8 秒后关底噪
// 问题：如果用户交互慢、calm 到 1 用了 30 秒，8 秒后底噪就关了——和 calm 脱节

// ✅ 正确：底噪 gain 永远是 calm 的函数
droneGain.gain.setTargetAtTime(0.08 * (1 - ts), ctx.currentTime, 0.1);
```

### 规则 3：calm lerp 因子全局统一

```javascript
const CALM_LERP_SPEED = 1.5;  // 全局常量，只在一处定义

// 所有地方用同一个因子
State.calm += (State.calmTarget - State.calm) * Math.min(1, dt * CALM_LERP_SPEED);
```

不要在不同地方使用不同的 lerp 速度——如果粒子系统用 0.8、音频用 2.0、CSS 用 1.2，那三个系统对 calm 变化的响应速度不同，用户会感到"不同步"。

### 规则 4：calm 可以反向驱动破坏态的强度

三幕剧中，第一幕（intro）calm 不变，第二幕（active）calm 从 0 开始上升。但破坏本身（如墨水滴入、弹窗出现）发生在第二幕开始时——此时 calm 还不高。破坏的强度应该是 `(1 - calm)` 的函数：

```javascript
// 破坏强度 = 1 - calm。calm 越低，破坏越强。
const intrusionStrength = 1 - c;  // 0→1, 当 calm 上升时入侵衰减
```

---

## 四、统一入口代码骨架

```javascript
// === 因果场总线 —— 唯一真相源 ===
// 放在主循环中，updateState(dt) 之后、render() 之前

function applyCalmState(dt) {
  const c  = State.calm;
  const ts = c * c * (3 - 2 * c);  // smoothstep——所有过渡类参数的根基

  // ─── 通用：大气 + 光 ───
  scene.fog.density = 0.003 - 0.0022 * ts;       // FogExp2
  ambientLight.intensity = 0.3 + 0.6 * ts;        // 环境光

  // ─── 粒子物理（如有）───
  if (PHYS) {
    PHYS.CURL_STRENGTH = 20 - 18 * ts;
    PHYS.STIFFNESS     = 0.5 + 2.0 * ts;
    PHYS.DAMPING       = 0.92 + 0.06 * ts;
  }

  // ─── GPU 着色器（如有）───
  if (particleMat) {
    particleMat.uniforms.uGlobalSize.value  = 0.6 + 1.4 * ts;
    particleMat.uniforms.uTransition.value  = ts;
  }

  // ─── FBO 流体（如有）───
  if (fluidSim) {
    fluidMat.uniforms.uDiffusion.value = 0.97 + 0.025 * ts;
    fluidMat.uniforms.uDecay.value     = 0.98 - 0.06 * ts;
  }

  // ─── 相机（如有 DollyZoom 入场则入场完成后生效）───
  if (entryComplete) {
    camera.fov = 50 + 20 * ts;
    camera.updateProjectionMatrix();
    // 相机抖动（仅压抑态）
    if (c < 0.5) {
      const shake = (1 - c) * 0.6;
      camera.position.x = baseCamX + Math.sin(State.time * 20) * shake;
      camera.position.y = baseCamY + Math.cos(State.time * 23) * shake;
    }
  }

  // ─── 音频（如有）───
  if (Audio && audioCtx) {
    Audio.update(ts);  // Audio.update 内部根据 ts 设置 gain/filter/LFO
  }

  // ─── CSS 背景 / UI（如有）───
  if (bgEl) {
    const bgLum = 0.15 + 0.4 * ts;
    bgEl.style.filter = `brightness(${bgLum})`;
  }
}
```

> 这个骨架是**声明式接口**。每个 `if (xxx)` 块的内部实现在各自的 reference 文件中（粒子在 particle-physics.md，流体在 gpu-fluid.md，音频在 audio-engine.md）。本文件只定义**绑定的数学关系**——即"什么参数在 calm=0 和 calm=1 时分别是什么值"。

---

## 五、反模式（违反复查）

| # | 反模式 | 级别 | 说明 |
|---|--------|------|------|
| 1 | FBO 有自己的进度变量不和 calm 同步 | **致命** | 典型错误：`let fluidHealProgress = 0` 作为独立变量。FBO 的扩散/衰减/颜色必须绑定 `ts` |
| 2 | 音频用独立 setTimeout 时间线 | **致命** | 典型错误：`setTimeout(() => {gain=0}, 10000)`。音频参数必须绑定 `ts`，不能有自己的时钟 |
| 3 | 不同系统使用不同的 calm lerp 速度 | **警告** | 粒子用 0.8、音频用 2.0、CSS 用 1.2 → 用户感知到不同步 |
| 4 | 某参数在 calm 全程保持不变 | **警告** | 如果 FogExp2 density 永远 0.001——雾没有参与情绪弧线，它是死的 |
| 5 | calm 过渡使用裸线性值而非 smoothstep | **警告** | `c` 和 `ts` 的视觉差异在中段（0.3~0.7）最明显。裸 `c` 中段太平——情绪转化的"中间段"恰好是最需要变化感的 |
| 6 | 移动端用不同映射表 | **警告** | 移动端的映射公式应与桌面相同——品质降级用 §六 的品质层级机制，不改变公式 |

---

## 六、品质层级：移动端的差异化体验

> 启发自 Three.js Pack 的品质层级架构——不对称预算分配。不是"移动端 = 桌面 × 40%"一刀切。

| 参数 | 桌面端 | 移动端 | 降级策略 |
|------|--------|--------|---------|
| 粒子数 | 150K | 60K | 减少数量，但映射公式不变——每个粒子的行为仍由 calm 驱动 |
| FBO 分辨率 | 1024² | 512² | HalfFloatType 强制（移动端显存减半） |
| FogExp2 | ✅ 启用 | ❌ 用 CSS 渐变雾替代 | CSS `radial-gradient` 透明度绑定 ts，视觉近似但零 GPU 成本 |
| 相机抖动 | ✅ 启用 | ❌ 禁用 | 移动端陀螺仪可能冲突，且小屏抖动易晕 |
| 音频 LFO 调制 | Full range | 频率减半 | 移动端扬声器对高频调制响应差 |
| 粒子笔触层数（p5.js） | 3 层 SCREEN 叠加 | 1 层 | 移动端 GPU fillRate 有限，多层叠加帧率骤降 |

**关键原则**：品质层级改变的是**算力分配**，不是**情绪映射**。移动端用户看到的 calm=0→1 的情绪弧线应该和桌面端一致——只是实现细节更轻量。

**性能硬约束（所有平台）**：
- 粒子物理循环：三角函数 ≤ 3 次/粒子，禁止循环内属性访问/函数调用/`new`
- 大粒子数（>100K）+ 复杂交互 → 用 GLSL 端噪声替代 CPU 端噪声（GPU 并行计算，不在 CPU 循环内逐粒子调用 `noise()`）

---

## 七、与 state-machine.md §三 的关系

| | state-machine.md §三 | 本文件 |
|---|---|---|
| 定位 | 快速上手示例 | 完整架构规范 |
| 覆盖范围 | Three.js 粒子系统 | 全部 7 种技术路线 |
| 参数映射 | 4 个参数（CURL/STIFFNESS/DAMPING/size） | 每路线 4~7 个参数，共 30+ 参数 |
| 过渡一致性 | 未覆盖 | §三 4 条规则 |
| 反模式 | 未覆盖 | §五 6 条 |
| 品质层级 | 仅"移动端 40% 粒子" | §六 5 维度差异化降级 |
| 何时读 | STEP 5 按需翻阅 | STEP 5 必读——在任何技术 reference 之前 |

**state-machine.md §三 的代码骨架仍然有效**——它是本文件在 Three.js 粒子路线上的具体实现示例。但 architecturally，本文件定义的契约优先于 state-machine.md 的示例。

---

## 八、自检清单（生成后、浏览器前）

- [ ] 场景中每个用户可感知的视觉/音频参数，都能回答"它在 calm=0 和 calm=1 时分别是什么值？"
- [ ] 所有过渡类参数使用了 smoothstep `ts` 而非裸 `c`？
- [ ] 不存在任何独立的进度变量（如 `healProgress`、`fluidPhase`）绕过 calm？
- [ ] 不存在 `setTimeout` 驱动音频/视觉参数的时间线？
- [ ] 移动端的品质降级是"差异化体验"而非"打折版桌面"？
- [ ] FogExp2 density / 环境光 / 相机 FOV 绑定 ts？（最容易漏的三项）

---

## 九、场派生触发 — 高潮从场的性质中涌现

> 设计哲学源自 OceanThreejs 的 Jacobian 泡沫：泡沫不是 `if (waveHeight > 3.0)` 的外部阈值——它是位移场 Jacobian 行列式 `J < threshold` 时的**自动几何产物**。适配到 healing-space：**第三幕的高潮触发条件，不应该只是 `calm > 0.95`——应该从场的数学性质中派生。**

### 9.1 为什么硬阈值不够

不同技术路线的"转折点"在 calm 轴上的位置不同：
- FBO 流体：墨迹在 calm=0.7 时可能已经视觉上干净了——硬阈值 0.95 太晚
- 粒子系统：粒子在 calm=0.9 时才开始归位——硬阈值 0.95 刚好
- Gerstner 海浪：choppiness 在 calm=0.6 时就降到 < 0.1 了——硬阈值 0.95 远远太晚

硬阈值 `calm > 0.95` 假设所有场景的情绪弧线同形状——但不同的物理过程有不同的转折点。**高潮应该由"场是否已经到达了它的治愈态"来判定，而不是由 calm 的绝对值判定。**

### 9.2 通用规则

```
高潮触发 = 场性质达标 AND calm > 0.6（保底）
```

- **场性质达标**：负责回答"视觉上真的治愈了吗？"
- **calm > 0.6**：防止场在 calm 很低时误触发（如初始化时的零状态可能"看起来"很干净）

如果场检测不可用（技术路线不支持场分析），回退到 fallback：`calm > 0.95`。

### 9.3 按技术路线的场检测函数

#### FBO 流体：墨水密度梯度

```javascript
/**
 * FBO 流体"清澈"检测——墨迹边缘是否已模糊到不可辨识
 * @param {WebGLRenderTarget} fboTexture - FBO 当前帧纹理
 * @param {number} threshold - 梯度阈值，默认 0.02
 * @returns {boolean} 水已清澈？
 */
function isFluidClear(fboTexture, threshold = 0.02) {
  // 轻量采样——读 FBO 的 16 个采样点的像素值
  // FBO 分辨率 1024²，采样步长 256px → 4×4 网格
  const STEP = 256;
  let maxGradient = 0;

  // 需要先读取 fboTexture 的像素数据（仅在关键帧执行——如每 30 帧一次）
  // const pixels = new Float32Array(4); // 单像素 RGBA
  // ... 读取逻辑取决于 FBO 的绑定方式

  // 简化版：如果 FBO 有对应的 CPU 密度数组
  for (let sy = STEP; sy < FBO_SIZE - STEP; sy += STEP) {
    for (let sx = STEP; sx < FBO_SIZE - STEP; sx += STEP) {
      const cx = sample(sx, sy);       // 中心像素
      const rx = sample(sx + 1, sy);   // 右邻
      const bx = sample(sx, sy + 1);   // 下邻
      const gx = rx - cx;
      const gy = bx - cx;
      const grad = Math.sqrt(gx * gx + gy * gy);
      maxGradient = Math.max(maxGradient, grad);
    }
  }
  return maxGradient < threshold;
}
```

> 性能注意：FBO 纹理回读（`readRenderTargetPixels`）是昂贵的——**只在 calm > 0.5 后每 30 帧检测一次**。不要在每帧检测。

#### Gerstner 海浪：choppiness + 泡沫

```javascript
/**
 * 海浪"平静"检测——直接读 material uniform（零成本）
 */
function isOceanCalm(oceanMaterial) {
  const u = oceanMaterial.uniforms;
  // choppiness 已接近 0 且泡沫几乎消失
  return u.uChoppiness.value < 0.1 && u.uFoamIntensity.value < 0.05;
}
```

#### 粒子系统：粒子平均速度

```javascript
/**
 * 粒子"安定"检测——平均速度降到初始值的 20% 以下
 * @param {object} phys - 粒子物理对象
 * @param {number} initialAvgSpeed - calm=0 时的平均速度（初始化时记录）
 */
function areParticlesSettled(phys, initialAvgSpeed) {
  // 每 60 帧计算一次平均速度——避免每帧遍历 150K 粒子
  let sumSpeed = 0;
  const sampleSize = Math.min(phys.count, 1000);  // 采样 1000 个粒子
  const step = Math.max(1, Math.floor(phys.count / sampleSize));
  for (let i = 0; i < phys.count; i += step) {
    sumSpeed += Math.sqrt(
      phys.vx[i] * phys.vx[i] + phys.vy[i] * phys.vy[i] + phys.vz[i] * phys.vz[i]
    );
  }
  const avgSpeed = sumSpeed / (phys.count / step);
  return avgSpeed < initialAvgSpeed * 0.2;
}
```

### 9.4 集成到 calm 总线

```javascript
// === 高潮触发逻辑（放在 applyCalmState 末尾） ===
let climaxTriggered = false;
let initialAvgSpeed = null;  // 粒子系统：初始化时记录

function checkClimax() {
  if (climaxTriggered) return false;
  if (State.calm < 0.6) return false;  // 保底——calm 不够高时不检测

  let fieldReady = false;

  // 根据技术路线选择检测函数
  switch (activeTechRoute) {
    case 'fbo-fluid':
      if (frameCount % 30 === 0) {  // 每 30 帧检测一次
        fieldReady = isFluidClear(fboTexture);
      }
      break;
    case 'gerstner-ocean':
      fieldReady = isOceanCalm(oceanMaterial);  // 零成本——直接读 uniform
      break;
    case 'particles':
      if (initialAvgSpeed === null) {
        // 首次调用——记录初始速度
        initialAvgSpeed = computeAvgSpeed();
      }
      if (frameCount % 60 === 0) {  // 每 60 帧检测一次
        fieldReady = areParticlesSettled(phys, initialAvgSpeed);
      }
      break;
    default:
      // fallback——技术路线不支持场分析
      fieldReady = State.calm > 0.95;
  }

  if (fieldReady) {
    climaxTriggered = true;
    triggerClimax();  // 金句淡入 + 视觉爆发 + 颂钵
  }
  return fieldReady;
}
```

### 9.5 反模式

| # | 反模式 | 级别 | 说明 |
|---|--------|------|------|
| 1 | 每帧读 FBO 纹理 | **致命** | `readRenderTargetPixels` 是同步 GPU→CPU 传输——每帧调用帧率从 60 降到 5 |
| 2 | 场检测替代 calm 映射 | **致命** | 场检测**只**用于高潮触发——不替代 calm 驱动参数。calm 仍然是单一真相源 |
| 3 | 忘记 calm 保底 | 警告 | 场性质可能在 calm 很低时误达标（如初始化时 FBO 是空的）→ `calm > 0.6` 防止误触发 |
| 4 | 场检测失败时无 fallback | 警告 | 如果 `activeTechRoute` 不详或检测函数报错 → 回退到 `calm > 0.95` |

### 9.6 自检

- [ ] 高潮触发条件是"场性质达标 AND calm > 0.6"（不是纯 `calm > 0.95`）？
- [ ] FBO 纹理回读每 30 帧一次（不是每帧）？
- [ ] 场检测只用于高潮触发——不替代 calm 的参数映射？
- [ ] 有不支持场检测时的 fallback（`calm > 0.95`）？
