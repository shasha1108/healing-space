# 视觉验证协议 — 运行时视觉正确性证据链

> 设计哲学源自 Three.js Awesome Graphics 的 `threejs-visual-validation` 技能（冻结输入 → 诊断马赛克 → 极值扫掠 → 时间证据 → 预算记录）。适配到 healing-space：**没有多 pass 渲染管线，但有 calm 状态变化轴和 viewport 响应面。calm 状态快照替代诊断马赛克，viewport 扫掠替代相机距离包络。**
>
> **加载时机**：STEP 4.8 对抗式检查之后、质量自检之前。对抗式检查验证"代码结构安全"，本文件验证"运行时视觉正确"——两者之间是互补关系，不是替代关系。
>
> **触发条件**：所有场景必读。

---

## 一、验证定位

```
STEP 4.8  对抗式检查  →  代码层：JS语法 / API兼容 / 纯黑纯白 / smin / dt / 光标
STEP 4.9  视觉验证    →  运行时：calm状态快照 / viewport响应 / 极值压力 / 时间稳定性
STEP 5    质量自检    →  体验层：14项清单
STEP 5.5  读者测试    →  感受层：5个体验问题
```

**为什么对抗式检查之后还需要视觉验证：**

对抗式检查验证的是"代码有没有写错"——语法错误、API 误用、纯黑纯白。但它不能验证"参数在运行时是否产生了正确的视觉"——因为参数交互的复杂性远超单个参数的范围。

具体来说，以下问题**只有运行时验证能发现**：
- 粒子 STIFFNESS=0.5 + DAMPING=0.92 在 calm=0.3 时产生了非线性聚集（代码正确，参数交互不当）
- FBO 扩散速度 0.97 在 ts→1 时与衰减 0.92 产生边缘锯齿闪烁（各自在合法范围内，组合不稳定）
- 移动端 375px 视口下光标直径 30px 覆盖了交互热区（桌面端完全正常）
- 底噪 LFO 调制频率在 calm=0.95 时仍有 1.5Hz——安静中突兀可闻的残余嗡声

---

## 二、7 步验证序列

### Step 0：冻结输入

**目的**：确保验证可复现。如果每次刷新都看到不同的粒子分布，就无法判断"改了参数后是不是变好了"。

**方法**：

```javascript
// 冻结确定性输入——仅在验证模式下启用
const VALIDATION_MODE = true;

if (VALIDATION_MODE) {
  // 1. 固定伪随机种子（如果用了随机）
  // 使用 seeded random 替代 Math.random()
  let seed = 42;
  function seededRandom() {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  }

  // 2. 固定 viewport 为设计基准尺寸
  // window.innerWidth / innerHeight 在验证模式下覆写
  const VALIDATION_VIEWPORT = { w: 1280, h: 800 };

  // 3. 固定 calm 起始值（可手动切换）
  // 默认从 0 开始，然后手动推进到各检查点
  State.calm = 0;
  State.calmTarget = 0;

  // 4. 录制 calm 推进函数（验证用）
  function setCalmForValidation(value) {
    State.calm = value;
    State.calmTarget = value;
    // 跳过 lerp 过渡——直接设置到目标值
  }
}
```

**通过标准**：同一 calm 值、同一 viewport 下，刷新页面 3 次，视觉输出完全一致（像素级）。

---

### Step 1：无后处理基线

**目的**：验证底层几何/粒子/流体在没有气氛修饰的情况下，本身是否可读。**不要用雾遮盖构图问题，不要用 SCREEN 混合遮盖粒子稀疏。**

**方法**：

```javascript
// 逐项关闭后处理，每项关闭后截图对比
function disablePostForValidation() {
  // 1. 关闭 FogExp2
  scene.fog = null;  // 或 scene.fog.density = 0

  // 2. p5.js: 关闭 SCREEN/ADD 混合模式
  // blendMode(BLEND);  // 恢复正常混合

  // 3. 关闭 CSS 滤镜（毛玻璃 blur / brightness）
  // glassEl.style.backdropFilter = 'none';

  // 4. Three.js: 关闭 AdditiveBlending
  // material.blending = THREE.NormalBlending;

  // 5. 关闭粒子拖尾（半透明背景）
  // background(0);  // 不透明背景，不做拖尾
}
```

**检查清单**：

| 检查项 | 通过标准 | 失败含义 |
|--------|---------|---------|
| 主体几何体/粒子是否可见？ | 主体占据画面 ≥ 15% 面积 | 粒子太稀/太小——靠 SCREEN 叠加伪装密度 |
| 构图是否可读？ | 前/中/远景可区分，主体不淹没 | 构图依赖雾来制造深度——底层结构混乱 |
| 颜色是否有层次？ | 至少有 3 个可辨色阶 | 颜色单调——靠混合模式制造假层次 |
| 交互区是否可见？ | 可交互区域与其他区域有视觉差异 | 交互入口不明确——靠动画指引掩盖 |

**失败处理**：无后处理基线不过 = 底层结构有问题。不要加回后处理来遮盖——回到 STEP 2（三幕剧）或 STEP 4（生成）修复底层。

---

### Step 2：calm 状态快照

**目的**：验证 calm 从 0→1 的视觉过渡是否平滑、连续、有层次。这是视觉验证的核心——**calm 是单一真相源，它的视觉输出必须在每个中间状态都正确。**

**方法**：

```javascript
// 在 5 个检查点分别截图
const CHECKPOINTS = [0, 0.25, 0.5, 0.75, 1.0];

for (const cp of CHECKPOINTS) {
  setCalmForValidation(cp);
  // 等待 2 帧让渲染稳定
  render(); render();
  // 截图保存为 calm_0.png, calm_025.png, ...
  // captureFrame(`validation/calm_${String(cp).replace('.','')}.png`);
}
```

**每个检查点的验证清单**：

| 检查点 | calm 值 | 三幕剧阶段 | 必须可见的视觉特征 | 禁止出现的视觉特征 |
|--------|---------|-----------|-------------------|-------------------|
| CP0 | 0 | intro（压抑态） | 雾浓、色暗、粒子躁动、底噪可闻 | 治愈色板（"还没开始"）、过度明亮的区域 |
| CP1 | 0.25 | active 早期 | 雾开始变淡、粒子速度略降、第一缕暖色出现 | 变化太剧烈（跳跃感）、完全看不出变化（卡住了） |
| CP2 | 0.5 | active 中期 | 颜色明显偏移、雾降到一半、粒子速度明显减慢 | 任何参数在 0.5 处出现极值/尖峰/反向 |
| CP3 | 0.75 | active 后期 | 接近治愈色板、雾几乎散尽、粒子近乎静止 | 底噪仍明显、暗色残留过多 |
| CP4 | 1.0 | complete（治愈态） | 完整治愈色板、无雾、粒子安静漂移、底噪消失 | 任何残余的压抑态特征、突兀的颜色跳变 |

**通过标准**：
- 5 张快照形成肉眼可辨的渐进过渡——每张和前一张的区别"刚刚好能感觉到"
- 不存在某一张和下一张之间变化过大（跳跃）或过小（卡住）
- CP2（0.5）不出现任何参数的极值/尖峰——中间态应该是所有参数的中点，不是某个参数的峰值

**失败处理优先级**：
1. 某参数在中间态出现尖峰 → 检查映射公式——是否用了非单调函数
2. 某区间变化过大 → 增大该区间的 smoothstep 权重，或调整映射公式的斜率
3. 某区间变化过小 → smoothstep 本身在两端最缓——如果映射公式叠加了另一个缓动，会双重压扁
4. CP4 仍有压抑态残留 → 检查映射公式的终点值是否正确

---

### Step 3：viewport 扫掠

**目的**：验证跨屏幕尺寸的视觉一致性和交互可用性。桌面端完美的设计在移动端可能完全不可用。

**方法**：

```javascript
const VIEWPORTS = [
  { w: 375, h: 812, name: 'mobile-s' },    // iPhone SE
  { w: 414, h: 896, name: 'mobile-l' },    // iPhone 11
  { w: 768, h: 1024, name: 'tablet' },     // iPad
  { w: 1280, h: 800, name: 'desktop-s' },  // 设计基准
  { w: 1920, h: 1080, name: 'desktop-l' }, // 大屏
];

for (const vp of VIEWPORTS) {
  // 设置 viewport
  window.innerWidth = vp.w;
  window.innerHeight = vp.h;
  window.dispatchEvent(new Event('resize'));

  // 分别在 calm=0 和 calm=1 截图
  setCalmForValidation(0); render(); render();
  // captureFrame(`validation/${vp.name}_calm0.png`);
  setCalmForValidation(1); render(); render();
  // captureFrame(`validation/${vp.name}_calm1.png`);
}
```

**检查清单**：

| 检查项 | 方法 | 通过标准 |
|--------|------|---------|
| 主体可见性 | calm=1 时主体是否在所有 viewport 可见？ | 主体占画面 ≥ 10%（最小屏） |
| 交互热区 | 可交互区域是否 > 44×44px（Apple HIG 最小触摸目标）？ | iOS Safari 不缩放时 ≥ 44px |
| 光标尺寸 | 自定义光标是否 < 交互热区的 30%？ | 光标不阻挡主要交互区 |
| 文字可读 | 最小字号是否 ≥ 11px（所有 viewport）？ | 中文在 11px 以下不可读 |
| 粒子密度 | 移动端粒子是否做了密度适配？ | 移动端 ≤ 桌面端 40%，但不为零 |
| CSS 毛玻璃 | `backdrop-filter: blur()` 在 Safari 是否生效？ | Safari 需要 `-webkit-backdrop-filter` |
| canvas z-index | Canvas 是否在毛玻璃底板和外壳之间？ | Safari stacking context bug |

**失败处理优先级**：
1. 移动端文字不可读 → 增大 `clamp()` 最小值
2. 交互热区过小 → 增大触摸目标的 CSS 尺寸，不依赖视觉尺寸
3. 光标过大 → 移动端隐藏自定义光标（已有规则），或在移动端缩小光标
4. 粒子在最小屏为 0 → 移动端粒子数下限设为 500

---

### Step 4：calm 极值压力测试

**目的**：暴露参数映射公式在极端使用模式下的数值不稳定。正常使用是 calm 缓慢 0→1，但用户可能快速反复按压/松手 → calm 快速震荡。

**方法**：

```javascript
// 模拟 3 种极端使用模式
async function extremeCycleTest() {
  // 模式 A：快速 0→1→0→1 震荡（模拟反复按压/松手）
  for (let cycle = 0; cycle < 5; cycle++) {
    // 0 → 1 在 1 秒内
    for (let t = 0; t <= 1; t += 0.05) {
      setCalmForValidation(t);
      render();
      await sleep(50);  // 模拟 ~20fps
    }
    // 1 → 0 在 1 秒内
    for (let t = 1; t >= 0; t -= 0.05) {
      setCalmForValidation(t);
      render();
      await sleep(50);
    }
  }

  // 模式 B：长时间停留在极值
  setCalmForValidation(0);
  for (let i = 0; i < 300; i++) { render(); }  // 10 秒 @30fps

  setCalmForValidation(1);
  for (let i = 0; i < 300; i++) { render(); }

  // 模式 C：微小抖动（模拟手指微颤）
  for (let i = 0; i < 100; i++) {
    const jitter = 0.5 + (Math.random() - 0.5) * 0.02;
    setCalmForValidation(jitter);
    render();
  }
}
```

**检查清单**：

| 检查项 | 通过标准 | 失败现象 |
|--------|---------|---------|
| NaN / Infinity | 控制台无 NaN 或 Infinity 警告 | 某参数映射公式在极值处产生除零或负数开方 |
| 粒子爆炸 | 粒子不飞出画面边界 | STIFFNESS 在快速震荡时积累能量 → 粒子弹射 |
| FBO 漂移 | 流体颜色不持续变亮/变暗/偏移 | 扩散/衰减在极值处不守恒 → 密度漂移 |
| 音频爆音 | 无"砰"声或刺耳杂音 | gain 在快速变化时产生 discontinuities |
| 颜色越界 | RGB 值保持在 [0,255] 或 [0,1] | mix() 在极值处可能超出合法范围 |
| 光标闪烁 | 光标在抖动测试中不闪 | 光标 opacity 或 transform 在快速更新中产生闪烁 |
| dt 大跳 | calm=0 持续 10 秒后首次交互不产生 dt spike | 长时间 idle 后 `dt` 可能是数秒——必须被钳制 |

**失败处理**：极值测试暴露的问题通常是**映射公式本身有数学缺陷**。不应通过钳制（clamp）来遮盖——应修复公式。

---

### Step 5：时间稳定性

**目的**：验证长时间运行后系统不会退化。粒子耗尽、FBO 漂移、音频失步、内存泄漏——这些问题在首屏看不出来。

**方法**：

```javascript
// 30 秒模拟运行：calm 缓慢从 0→1，然后保持
async function temporalStabilityTest(durationSec = 30) {
  const startTime = performance.now();

  function loop(now) {
    const elapsed = (now - startTime) / 1000;
    if (elapsed > durationSec) return;

    // 前 15 秒：calm 从 0→1
    // 后 15 秒：保持 calm=1
    const targetCalm = Math.min(1, elapsed / 15);
    State.calmTarget = targetCalm;
    updateState(1/60);  // 模拟 60fps
    applyCalmState(1/60);
    render();

    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);
}
```

**检查清单**：

| 检查项 | 观察方法 | 通过标准 | 失败现象 |
|--------|---------|---------|---------|
| 粒子总数 | 每 5 秒记录粒子数组长度 | 变化 < 5% | 粒子逐渐耗尽（出生<死亡）或无限累积（出生>死亡） |
| 粒子分布 | 目测画面是否出现空洞或聚集 | 粒子覆盖均匀，无大范围空洞 | 所有粒子漂移到同一角落 |
| FBO 颜色漂移 | 目测流体颜色是否偏离初始色 | 颜色在 ±5% 范围内稳定 | 累积误差导致颜色持续变亮/暗 |
| 音频音高漂移 | 听底噪音高是否变化 | 无感知变化 | LFO/滤波频率累积偏移 |
| 内存 | Chrome DevTools Performance Monitor | JS heap size 不持续增长 | 每帧 new 对象未回收 |
| 帧率 | 目测或帧率计数器 | 不低于初始帧率的 80% | 粒子/节点累积导致性能退化 |
| calm=1 稳态 | calm=1 保持 10 秒后的视觉 | 与刚达到 calm=1 时一致 | 治愈态"回退"——某些参数在稳态下继续漂移 |

**失败处理优先级**：
1. 粒子耗尽 → 检查重生逻辑——出生率是否匹配死亡率
2. FBO 漂移 → 检查扩散/衰减在长时间运行下的守恒性
3. 内存增长 → 检查是否有每帧 `new` 对象 / 未清理的 `setTimeout`
4. 帧率下降 → 检查粒子/节点数是否随时间单调增长

---

### Step 6：预算记录

**目的**：建立性能基线，作为后续迭代的对比基准。**不能测量就不能管理。**

**方法**：

```javascript
function recordBudgets() {
  const budget = {
    // 几何/渲染
    particleCount: particles ? particles.length : 'N/A',
    fboResolution: fboSize || 'N/A',
    drawCalls: renderer ? renderer.info.render.calls : 'N/A',
    triangles: renderer ? renderer.info.render.triangles : 'N/A',

    // 内存（Chrome DevTools 手动记录）
    jsHeapSize: 'DevTools → Memory → Take snapshot',

    // 音频
    audioNodeCount: audioCtx ? countAudioNodes() : 'N/A',

    // 帧率（稳定态，calm=0.5）
    fpsAtCalm05: '目测或帧率计数器',

    // 首屏
    timeToInteractive: '从加载到首次可交互的秒数',
  };

  console.table(budget);
  return budget;
}

function countAudioNodes() {
  // 递归遍历 audioCtx 的节点图
  let count = 0;
  function traverse(node) {
    count++;
    if (node.numberOfOutputs) {
      for (let i = 0; i < node.numberOfOutputs; i++) {
        const dest = node.context.destination; // 简化——实际需遍历连接
      }
    }
  }
  return count; // 近似值——精确计数需维护节点注册表
}
```

**基线参考值（1280×800 桌面端）**：

| 指标 | 健康 | 警告 | 危险 |
|------|------|------|------|
| Three.js 粒子 | < 150K | 150-300K | > 300K |
| p5.js 粒子 | < 2000 | 2000-5000 | > 5000 |
| FBO 分辨率 | 1024² | 2048² | > 2048² |
| 音频节点 | < 20 | 20-50 | > 50 |
| 帧率（桌面） | 60fps | 45-60fps | < 45fps |
| 帧率（移动） | 50+fps | 30-50fps | < 30fps |
| 首屏可交互 | < 2s | 2-4s | > 4s |

---

### Step 7：回归集

**目的**：保留一组截图作为"正确性锚点"。下一次参数调整后，可以对比回归集判断是否产生了视觉退化。

**方法**：

```javascript
// 回归集：3 个 calm 状态 × 2 个 viewport = 6 张截图
const REGRESSION_SET = [
  { calm: 0,    vp: 'desktop', label: '压抑态-桌面' },
  { calm: 0.5,  vp: 'desktop', label: '过渡态-桌面' },
  { calm: 1,    vp: 'desktop', label: '治愈态-桌面' },
  { calm: 0,    vp: 'mobile',  label: '压抑态-移动' },
  { calm: 0.5,  vp: 'mobile',  label: '过渡态-移动' },
  { calm: 1,    vp: 'mobile',  label: '治愈态-移动' },
];
```

**回归集使用方式**：
1. 首次生成后运行完整 7 步验证，保留回归集截图
2. 每次参数调整后，重新运行 Step 2（calm 状态快照）+ Step 3（viewport 扫掠）
3. 肉眼对比新旧截图——判断是否产生了视觉退化
4. 如果回归集对比通不过 → 回退参数调整

---

## 三、与对抗式检查的分工边界

| 维度 | 对抗式检查（adversarial-review.md） | 视觉验证（本文件） |
|------|-------------------------------------|-------------------|
| **验证对象** | 代码文本（静态） | 运行时视觉输出（动态） |
| **验证方式** | 脚本扫描（正则/语法树） | 浏览器运行 + 目测 + 截图对比 |
| **发现的问题** | 语法错误、API 误用、纯黑纯白、smin、dt 未钳制 | 参数交互不当、数值不稳定、跨 viewport 失效、时间退化 |
| **执行工具** | Node.js 脚本 | 浏览器 + DevTools |
| **致命缺陷** | 代码崩溃、安全漏洞 | 视觉不可读、交互不可用、情绪弧线断裂 |
| **顺序** | 先执行 | 后执行（代码安全了才值得跑浏览器） |

**一个参数问题可能被两边同时发现，但角度不同**：
- 对抗式检查：`scale=0.16` → 实际像素 8px < 15px → WARN
- 视觉验证：在 viewport 扫掠中目测 → "这个风车看不见" → FAIL

两者互补——对抗式检查用规则抓已知模式，视觉验证用眼睛抓规则覆盖不到的新模式。

---

## 四、失败处理决策树

```
验证失败
  ├─ Step 0 失败（不可复现）
  │   └─ 添加 seeded random，固定 viewport，重新验证
  │
  ├─ Step 1 失败（无后处理基线不可读）
  │   └─ ⚠️ 回到 STEP 2（三幕剧）或 STEP 4（生成）——底层结构问题
  │
  ├─ Step 2 失败（calm 状态过渡不平滑）
  │   ├─ 跳跃 → 检查映射公式斜率
  │   ├─ 卡住 → 检查是否双重缓动压扁了变化
  │   └─ 尖峰 → 检查是否用了非单调函数
  │
  ├─ Step 3 失败（某 viewport 不可用）
  │   ├─ 移动端 → 启用品质层级（causal-field.md §六）
  │   └─ 大屏 → 检查是否有硬编码的像素值（应改用相对单位）
  │
  ├─ Step 4 失败（极值不稳定）
  │   └─ 修复映射公式的数学缺陷——不用 clamp 遮盖
  │
  ├─ Step 5 失败（时间不稳定）
  │   ├─ 粒子耗尽 → 修复重生逻辑
  │   ├─ 内存增长 → 排查每帧 new / 未清理 timer
  │   └─ FBO 漂移 → 检查扩散/衰减守恒性
  │
  └─ Step 6 失败（预算超标）
      ├─ 粒子过多 → 降低上限，启用移动端降级
      ├─ 帧率低 → 降低 FBO 分辨率 / 减少音频节点
      └─ 首屏慢 → 延迟初始化音频 / 减少初始化计算
```

---

## 五、自检清单（验证执行后）

- [ ] Step 0：同一配置下刷新 3 次，输出一致？
- [ ] Step 1：关闭所有后处理，底层结构可读？
- [ ] Step 2：5 张 calm 快照形成平滑渐进过渡？CP2（0.5）无尖峰？
- [ ] Step 3：5 个 viewport 下主体可见、交互区可用、文字可读？
- [ ] Step 4：快速震荡 5 周期无 NaN/爆炸/爆音/闪烁？
- [ ] Step 5：30 秒运行粒子不耗尽、FBO 不漂移、内存不增长？
- [ ] Step 6：所有预算指标在"健康"列？
- [ ] Step 7：回归集截图已保留？

全部 ✅ 才进入 STEP 5（质量自检）。
