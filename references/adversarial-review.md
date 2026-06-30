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
