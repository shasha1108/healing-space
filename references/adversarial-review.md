# 对抗式检查 SOP + 第一性原理创作流程

> 全场景通用。适用 Three.js / p5.js / WebGL / FBO / CSS 任一技术栈。
> 本文件是 `pixel-bloom/references/design-principles.md §十三~§十五` 的 healing-space 适配版。

---

## 一、屏幕像素锚定法则

**参数设计必须以屏幕像素为锚点，不是以数学比例为锚点。**

### 最小可见尺寸（1280×800 参考）

| 元素类型 | 最小可见像素 | 说明 |
|---------|------------|------|
| 3D 主体几何体（远） | ≥ 20px 投影高度 | 相机 z 轴距离换算 |
| 3D 主体几何体（近） | ≥ 80px 投影高度 | FogExp2 近端 |
| 尺度参照物 | ≥ 12px | 小建筑/人物/家具 |
| 粒子（单个） | ≥ 2px 直径 | AdditiveBlending 下可更小 |
| UI 文字 | ≥ 11px | 宋体 Light 可略小 |
| 光标 | ≥ 14px | Lerp 跟随 |

### 写完任何 scale/camera.z/size 参数立刻验证

```
3D: 投影尺寸 ≈ (几何体尺寸 × canvas高度) / (2 × camera.z × tan(fov/2))
2D: 实际像素 = 基准尺寸 × scale
```

**< 15px = 用户看不见。 < 8px = 连点都不是。**

---

## 二、对抗式检查 SOP（强制执行）

### 检查项

| # | 检查项 | 方法 | 级别 |
|---|--------|------|------|
| 1 | JS 语法 | `new Function(script)` | 致命 |
| 2 | API 兼容性 | 扫描 `fill(hex+'cc')` / `color+'cc'` 等字符串拼接 α → 替换为 `rgba()` 或 Three.js `setOpacity()` | 致命 |
| 3 | Raymarching SDF 安全 | 扫描多球 `smin()` / `opSmoothUnion` 调用 → 多球融合 = Body Horror，不可修复 | 致命 |
| 4 | 颜色铁律 | 扫描 `#000` / `#000000` / `#fff` / `#ffffff` → 替换为深灰/暖白 | 致命 |
| 5 | 跨浏览器兼容性 | 扫描 `rect(x,y,w,-h)` 等负尺寸 → 替换为正尺寸 | 警告 |
| 6 | 缩放可见性 | 提取所有 `scale` / `camera.position.z` 值，计算实际像素 | 警告 |
| 7 | FBO 移动端 | `HalfFloatType` 检查（移动端显存减半） | 警告 |
| 8 | dt 钳制 | 扫描 `dt` 使用处，确认有 `dt = Math.min(dt, 0.033)` | 警告 |
| 9 | 光标双显 | CSS `* { cursor: none }` + cursor div 初始 `opacity: 0` | 警告 |
| 10 | audioCtx 延迟 | 首次用户交互后才 `resume()` | 警告 |
| 11 | 调试代码残留 | 扫描 `DEBUG_LAYER` / `debugLayer` / `debugMode` 等调试变量 → 确认无调试入口暴露给用户 | 致命 |

### 执行纪律

- **第一轮**：代码写完立刻跑，修完所有致命项
- **第二轮**：浏览器实测前跑，修完所有警告
- **检查脚本不替代浏览器实测**

### 最小检查脚本骨架

```javascript
const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const sm = (html.match(/<script[^>]*>([\s\S]*?)<\/script>/) || [])[1] || '';
const issues = [];

// 1. JS 语法
try { new Function(sm); } catch (e) { issues.push('FATAL: JS - ' + e.message); }

// 2. hex + string 拼接 α
if (sm.includes("+ 'cc'") || sm.includes('+ "cc"')) {
  issues.push('FATAL: hex+string alpha — use rgba()');
}

// 3. 纯黑纯白
if (sm.includes('"#000"') || sm.includes("'#000'") || sm.includes('"#000000"'))
  issues.push('FATAL: pure black #000 — use deep gray');
if (sm.includes('"#fff"') || sm.includes("'#fff'") || sm.includes('"#ffffff"'))
  issues.push('FATAL: pure white #fff — use warm white');

// 4. 负尺寸 rect
const negRects = sm.match(/rect\([^)]*-\d+[^)]*\)/g) || [];
if (negRects.length) issues.push('WARN: rect with negative values');

// 5. 缩放可见性 (p5.js)
const scales = [...sm.matchAll(/scale\s*=\s*([\d.]+)/g)];
for (const s of scales) {
  const px = 50 * parseFloat(s[1]);
  if (px < 15) issues.push(`WARN: scale=${s[1]} → ${px.toFixed(0)}px < 15px`);
}

// 6. dt 钳制
if (sm.includes('dt') && !sm.includes('Math.min(dt') && !sm.includes('min(dt'))
  issues.push('WARN: dt used without clamp — add dt = Math.min(dt, 0.033)');

// 7. cursor none 全局
if (!html.includes('cursor: none') && !html.includes('cursor:none'))
  issues.push('WARN: missing cursor:none — custom cursor will double-show');

// 8. Raymarching SDF 多球
const sminCalls = (sm.match(/smin\(/g) || []).length;
if (sminCalls > 0) issues.push(`FATAL: ${sminCalls} smin() calls — multi-sphere = Body Horror`);

console.log(issues.length ? issues.join('\n') : 'All checks passed');
```

> **补充验证（UI 侧）**：上述 JS 脚本检查代码层安全（语法/API/着色器）。完成后运行 `python3 scripts/validate.py <output.html>` 补充验证 UI 层质量信号——光标隐藏、字体族、letter-spacing、音频频率/gain 合规。两个检查器互补：JS 查代码安全，Python 查 UI 正确性。

---

## 三、第一性原理创作流程

### 决策链（从情绪到代码）

```
情绪词 + 受众画像（谁在什么状态下打开？→ §第一步）
  ↓
概念种子（这个情绪的本质困境是什么？→ 通感映射表）
  ↓
物理隐喻（什么自然现象承载这个感受？流体？剥落？结晶？→ §第二步）
  ↓
三幕剧结构（美好展示 → 突然破坏 → 亲手修复 → §第二步）
  ↓
技术路线（流体=FBO / 粒子=Three.js / 有机线条=p5.js / 平面=CSS → §第三步）
  ↓
交互即仪式（用户的动作在现实中对应什么？擦拭？长按安抚？→ §第四步）
  ↓
参数锚定（每个 scale/camera.z/size → 多少实际像素？→ 本文件 §一）
  ↓
对抗式检查（脚本跑一遍 → 本文件 §二）
  ↓
浏览器实测
```

### 五个铁律

1. **隐喻先于技术**：不要先决定"用 Three.js 做什么"，先决定"让人感受到什么"
2. **三幕剧不可跳过**：缺第一幕=观众没有失去感，不会想修复。缺第三幕=没有见证，疗愈不完整
3. **交互是仪式，不是操作**：用户的动作必须有现实对应（擦拭=清洁，长按=安抚），做完会觉得"我为自己做了一件事"
4. **参数必须锚定屏幕像素**：`camera.position.z = 200` 没有意义，换算投影尺寸才有意义
5. **对抗式检查是强制步骤**：人脑无法同时追踪 FBO 显存格式 + SDF 安全规则 + dt 钳制 + 光标双显修复 + API 兼容性

### 迭代优先级（效果不好时按顺序排查，不跳级）

| 优先级 | 检查项 | 投入产出比 |
|--------|--------|----------|
| 1 | 隐喻对了吗？三幕缺了吗？ | 最高 — 错了全盘皆输 |
| 2 | 技术路线对了吗？粒子≠流体，CSS≠3D | 高 |
| 3 | 交互是仪式吗？用户做完有"我为自己做了一件事"的感觉吗？ | 高 |
| 4 | 色差/颜色可见性 — 元素是否融入背景 | 中 |
| 5 | 生物细节/粒子运动 — 是 Perlin 漂移还是分段转向/FSM | 中 |
| 6 | 尺寸可见性 — scale × 基准 < 15px | 中 |
| 7 | 粒子参数微调（刚度/阻尼/颜色） | 低 — 最后 10%，不是前 90% |

---

## 四、开发时层可视化（"一个着色器，多种调试视图"）

> 设计哲学源自 stylized-scene 的 7 种调试模式——在同一个渲染管线中切换输出不同中间值，不写独立调试着色器。适配到 healing-space：**AI 在生成代码后、浏览器实测前，用临时调试输出逐层验证每个渲染阶段是否正确。**

### 4.1 为什么需要层可视化

Healing Space 的场景通常包含多个渲染层叠加：
- 粒子颜色 = 根色梯度 → 噪声补丁混合 → 地面投影着色 → 逐粒子亮度变异 → 宏观亮度场
- 流体密度 = FBO 平流 → 扩散 → 用户画笔注入 → 衰减
- 着色器 = 顶点位移 → 法线扰动 → 漫反射 → 环境光 → FogExp2

如果最终画面有问题，**无法从最终输出判断是哪个层出了问题**——颜色不对可能是梯度错了、噪声尺度不对、投影强度过大、或者亮度变异范围太窄。

**层可视化 = 逐个输出中间值，单独查看每个层。**

### 4.2 实现模式（最小侵入）

```javascript
// === 调试开关 —— 仅开发时存在，交付前删除 ===
const DEBUG_LAYER = null;  // null | 'gradient' | 'noise' | 'height' | 'worldXY'

// 在着色器/渲染逻辑中：
function getOutputColor(inputs) {
  // ... 正常的多层颜色计算 ...
  
  // 调试开关（交付前整个 if 块删除）
  if (DEBUG_LAYER === 'gradient')  return gradientColor;
  if (DEBUG_LAYER === 'noise')     return vec3(patchNoise);    // 灰度
  if (DEBUG_LAYER === 'height')    return vec3(heightT);       // 灰度
  if (DEBUG_LAYER === 'worldXY')   return vec3(worldX, 0, worldY);
  
  return finalColor;
}
```

**关键纪律**：
1. `DEBUG_LAYER` 是代码常量——不是 UI 开关、不是键盘快捷键
2. AI 在视觉验证阶段（STEP 8）手动修改 `DEBUG_LAYER` 的值，逐层截图对比
3. 全部验证通过后，**整个调试 if-else 块删除**——不给最终用户任何调试入口
4. 不在 p5.js 的 `draw()` 循环中放调试逻辑——调试期间的性能下降可接受，但交付时不允许残留

### 4.3 每种技术路线的推荐调试视图

| 技术路线 | 推荐调试视图 | 验证什么 |
|---------|------------|---------|
| **Three.js 粒子** | `gradient`（纯色梯度，关闭投影/亮度变异）<br>`noise`（噪声场灰度图）<br>`height`（逐粒子高度因子） | 梯度平滑性、噪声无重复、高度加权正确 |
| **FBO 流体** | `density`（密度场灰度图）<br>`velocity`（速度场方向箭头）<br>`divergence`（散度场热力图） | 密度不截断、速度场无死区、散度收敛 |
| **Reaction-Diffusion** | `uField`（U 浓度场）<br>`vField`（V 浓度场）<br>`feedKill`（F/K 覆盖图） | U/V 在合理范围内、F/K 参数产生期望的图案类型 |
| **p5.js 有机线条** | `flowfield`（流场方向箭头）<br>`noiseOnly`（纯噪声灰度图）<br>`curveVertices`（曲线顶点叠加） | 流场无死区、噪声频率匹配笔触尺度、顶点密度均匀 |
| **Raymarching SDF** | `steps`（步进次数热力图）<br>`normals`（法线方向 RGB 图）<br>`distance`（距离场灰度图） | 步进不超限、法线方向连续、距离场无奇点 |
| **Gerstner 波** | `height`（高度场灰度图）<br>`foam`（泡沫遮罩）<br>`jacobian`（Jacobian 行列式） | 波高范围合理、泡沫在波峰正确出现、无折叠 |

### 4.4 p5.js 2D 场景的调试适配

p5.js 没有着色器的中间值输出——但可以在画布上临时覆盖半透明调试层：

```javascript
// === p5.js 调试覆盖层 ===
function drawDebugOverlay(debugLayer) {
  if (!debugLayer) return;
  
  push();
  // 半透明覆盖——可以看到下面的正常内容
  drawingContext.globalAlpha = 0.6;
  
  if (debugLayer === 'noise') {
    // 逐像素绘制噪声场灰度图
    loadPixels();
    for (let y = 0; y < CH; y += PX) {
      for (let x = 0; x < CW; x += PX) {
        const n = noise(x * 0.03, y * 0.03);
        const c = Math.round(n * 255);
        for (let dy = 0; dy < PX; dy++)
          for (let dx = 0; dx < PX; dx++)
            setPixel(x + dx, y + dy, [c, c, c, 200]);
      }
    }
    updatePixels();
  }
  
  if (debugLayer === 'wind') {
    // 绘制每棵植物位置的风强颜色图
    // 红色=高风强，蓝色=低风强
    for (const plant of plants) {
      const i = windIntensity(plant.x, plant.idx, millis() * 0.001, WIND);
      const r = Math.round(i * 255);
      const b = Math.round((1 - i) * 255);
      fill(r, 0, b, 180);
      circle(plant.x, plant.y, 8);
    }
  }
  
  pop();
}
```

**⚠️ p5.js 调试覆盖层的性能注意事项**：
- `loadPixels()`/`updatePixels()` 在每帧调用会显著降帧（~30%）
- 调试覆盖层仅在 STEP 8 视觉验证时开启——验证完关闭
- 像素遍历（`for x / for y`）在调试噪声场时使用——这是验证步骤，不要求 60fps

### 4.5 调试验证 SOP（STEP 8 的一部分）

在视觉验证 7 步序列之前，先用调试视图逐层验证：

```
0. 层验证（调试 SOP — 视情况执行）：
  0.1 设置 DEBUG_LAYER = 第一个中间值 → 截图
  0.2 目测：该层的值范围是否正确？图案是否符合预期？有无截断/死区/奇点？
  0.3 切换到下一个 DEBUG_LAYER → 重复
  0.4 全部层验证通过后，设置 DEBUG_LAYER = null
  0.5 删除整个调试 if-else 块（或 p5.js 的 debugOverlay 调用）
```

**如果某个层有问题**——这是"根本问题"，不要跳到参数微调。回到该层的实现代码，修正后重新验证该层。

### 4.6 自检（调试相关，追加到对抗式检查清单）

- [ ] 调试 switch/if-else 块是否在交付代码中**完全删除**（不是注释掉、不是 flag=false）？
- [ ] 是否有面向用户的调试入口（键盘快捷键、隐藏按钮、URL 参数）？—— **禁止**
- [ ] p5.js 场景是否移除了所有 `drawDebugOverlay()` 调用？
- [ ] 视觉验证截图是否覆盖了所有关键中间层？
