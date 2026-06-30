# 确定性种子系统 — 让迭代变成科学

> 设计哲学源自 Three.js Awesome Graphics 的 deterministic reproducibility 原则（同一 seed = 同一输出 = 回归对比）。适配到 healing-space：**不是让用户探索不同种子（那是 pixel-bloom 的 seeded-exploration），而是让开发者在迭代修改参数时，能对比"改之前"和"改之后"。**
>
> **加载时机**：STEP 4 生成代码时必读——在写第一行初始化代码之前确定种子策略。
>
> **触发条件**：所有含 `Math.random()` 初始化（粒子位置/颜色/噪声偏移）的场景。

---

## 一、为什么需要种子

healing-space 的主要使用模式是**迭代式创作**——用户不会一次满意，会反复说"风车太小了""粒子太密了""颜色不对"。

当前流程：
```
第 1 次生成 → Math.random() 产生世界 A
用户："粒子太密了"
第 2 次生成 → Math.random() 产生世界 B（粒子位置/颜色全变了）
用户："...好像密度好了一点，但颜色不如刚才了？"
第 3 次 → 无法回到世界 A 的颜色 + 世界 B 的密度 → 放弃精确迭代
```

加入种子后：
```
第 1 次生成 → seed=42 产生世界 A
用户："粒子太密了"
第 2 次生成 → seed=42，粒子数减半 → 同一个世界，粒子少了
对比：改之前的截图 vs 改之后的截图 → 一眼看出"密度变好了，其他没变"
```

**种子的本质**：分离"世界的随机"和"参数的随机"。世界的样子应该由 seed 决定（稳定），参数的调整应该独立生效（可控）。

---

## 二、最小实现

### 2.1 确定性随机函数

```javascript
// mulberry32 — 最轻量、最快的确定性 PRNG
// 替代 Math.random() 用于所有"世界的随机"
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// 全局种子和随机函数
let SEED = 42;
let rng = mulberry32(SEED);

// 封装：需要确定性随机时用 rng()，不需要时用 Math.random()
function seededRandom() {
  return rng();
}
```

### 2.2 种子来源

```javascript
// 优先级：URL hash > 默认值
function getSeed() {
  const hash = window.location.hash;
  if (hash && hash.startsWith('#seed=')) {
    const parsed = parseInt(hash.replace('#seed=', ''));
    if (!isNaN(parsed)) return parsed;
  }
  // 生成时：使用默认种子或随机种子
  // 迭代时：开发者手动设置 seed 参数
  return 42; // 默认种子
}

SEED = getSeed();
rng = mulberry32(SEED);
console.log(`[healing-space] seed=${SEED}`);
```

### 2.3 写入 URL（可选，方便分享/对比）

```javascript
// 如需让用户/开发者可复现当前世界
window.location.hash = `seed=${SEED}`;
```

---

## 三、种子使用规则：什么时候用它

**核心判断：这个随机值定义了"世界长什么样"还是"世界怎么动"？**

### ✅ 必须用种子（`rng()` 替代 `Math.random()`）

| 场景 | 原因 |
|------|------|
| 粒子初始位置 | 位置定义了世界的空间结构——必须可复现 |
| 粒子初始颜色（colFrom/colTo） | 颜色定义了世界的调性——必须可复现 |
| Perlin 噪声偏移量 | 每个粒子的噪声相位偏移——不同的偏移 = 不同的流动路径 |
| 几何体/物体的初始分布 | 风车位置、房子位置、野花位置——必须可复现 |
| 音效的初始随机参数 | 风铃音阶的起始偏移——必须可复现 |
| FBO 初始密度场（如有预填充） | 流体初始状态——必须可复现 |
| 颜色调色板的随机偏移 | 从色板中随机选色——不同选色 = 不同情绪 |

### ❌ 继续用 `Math.random()`（不需要种子）

| 场景 | 原因 |
|------|------|
| 每帧的微小抖动（如蝴蝶翅膀微颤） | 这是"活着的随机"——帧间抖动不需要可复现 |
| 用户交互触发的瞬态效果 | 每次点击产生的粒子爆发——天然不可复现（取决于用户行为） |
| 音频 LFO 的瞬时相位 | LFO 的连续变化——不可复现也不应该复现 |
| FSM 状态切换的随机延迟 | 蝴蝶转向的随机间隔——这是"生命的不确定性" |
| 粒子重生时的微小偏移 | 粒子流出画面后重生——已经脱离了初始条件 |

**一句话原则**：**初始化阶段**的随机 = 用种子。**运行时阶段**的随机 = 用 `Math.random()`。

---

## 四、迭代协议

### 协议 1：改参数不改种子 → 对比

```
种子不变 + 改参数 = 同一个世界，不同的表现
→ 截图对比：旧版 vs 新版
→ 判断：参数调整的方向对了吗？
```

```
示例：
  seed=42, PARTICLE_COUNT=150000  → 世界 A（截图保存）
  seed=42, PARTICLE_COUNT=100000  → 世界 A'（粒子少了，但分布格局一致）
  对比：密度降了吗？分布格局还好看吗？
```

### 协议 2：改种子不改参数 → 探索

```
参数不变 + 改种子 = 同一个配方，不同的世界
→ 截图对比：seed=42 vs seed=99
→ 判断：参数组合在这个种子下也好看吗？（鲁棒性检验）
```

```
示例：
  seed=42, PARTICLE_COUNT=100000  → 世界 A
  seed=99, PARTICLE_COUNT=100000  → 世界 B（不同的粒子分布）
  对比：种子 99 的分布有没有产生空洞或聚集？
```

### 协议 3：回归集 = 固定种子 + 固定参数

```
回归集（visual-validation.md Step 7）的基础：
  seed=42, calm=0   → 压抑态基准
  seed=42, calm=0.5 → 过渡态基准
  seed=42, calm=1   → 治愈态基准
下一次参数调整后，用同一个 seed 重新生成回归集 → 可对比
```

---

## 五、代码模板：初始化时注入种子

```javascript
// === 确定性种子系统 — 在生成代码最顶部注入 ===

// 1. 确定性 PRNG
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// 2. 种子初始化
const SEED = (() => {
  const hash = window.location.hash;
  if (hash && hash.startsWith('#seed=')) {
    const p = parseInt(hash.replace('#seed=', ''));
    if (!isNaN(p)) return p;
  }
  return 42; // 默认种子——生成时可改为 Date.now() 以保证每次不同
})();
const rng = mulberry32(SEED);
console.log(`[healing-space] seed=${SEED}`);

// 3. 在所有初始化代码中，用 rng() 替代 Math.random()
// 示例：粒子初始化
for (let i = 0; i < PARTICLE_COUNT; i++) {
  positions[i * 3]     = (rng() - 0.5) * SPREAD_X;  // ✅ rng()
  positions[i * 3 + 1] = (rng() - 0.5) * SPREAD_Y;
  positions[i * 3 + 2] = (rng() - 0.5) * SPREAD_Z;
  colFrom[i * 3]       = 0.8 + rng() * 0.2;         // 颜色微小变异
  noiseOffsets[i]      = rng() * Math.PI * 2;        // Perlin 相位偏移
}

// 4. 运行时随机继续用 Math.random()
// 示例：每帧的微颤
function updateButterflyWing(dt) {
  wingAngle += (Math.random() - 0.5) * 0.1 * dt;  // ✅ Math.random() — 活着的随机
}
```

---

## 六、与现有系统的关系

| 文件 | 关系 |
|------|------|
| `pixel-bloom/references/seeded-exploration.md` | 那是**用户面**的种子探索（Seed 导航面板 / 参数 slider / 可分享 URL）。本文件是**开发者面**的种子系统——最小、无 UI、仅为迭代可对比性 |
| `visual-validation.md` | 回归集（Step 7）依赖种子系统：同一 seed 生成回归集 → 参数调整后同 seed 再生成 → 可对比 |
| `causal-field.md` | 种子独立于 calm——种子决定"哪个世界"，calm 决定"这个世界的哪个状态" |
| `adversarial-review.md` | 对抗式检查不涉及种子——种子不影响代码安全性 |

---

## 七、自检清单

- [ ] 所有初始化阶段的 `Math.random()` 已替换为 `rng()`？
- [ ] 运行时阶段（帧循环内）的 `Math.random()` 保留了？
- [ ] seed 打印在 console 中？（方便调试时复制）
- [ ] 同 seed 刷新 3 次，粒子位置/颜色/噪声偏移完全一致？
- [ ] 改 seed 不改参数 → 生成不同的世界？（验证种子实际生效）
- [ ] 改参数不改 seed → 只有目标参数变化，其他不变？（验证迭代可对比性）
