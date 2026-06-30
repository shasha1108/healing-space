# Clipmap LOD — 无限平面的视图相关细节层级

> 核心算法源自 FFTOCEAN 的 `ClipmapGeometry.js` + `oceanVertex.glsl`。适配到 healing-space：**视图相关 LOD 不绑定海洋——任何需要"看起来无限延伸"的平面（海洋/地形/草地）都能用。** vertex shader 内完成 LOD 分配、网格 snapping 和 morph 混合——JS 端零帧开销。
>
> 设计哲学：**LOD 不是"远处偷懒"的妥协——是"把算力花在看得见的地方"的最优资源分配。** 相机附近的顶点间距 = baseSpacing（最高细节），每翻倍距离顶点间距也翻倍——顶点总数固定，但远处置信度不变。
>
> **加载时机**：STEP 5 执行时选读。触发条件：场景含"飞越/滑翔/俯瞰/穿行 + 大海/山谷/草原"——相机需要大幅移动（> 200m）且场景含需要 vertex displacement 的大型平面。
>
> **不触发**：固定相机 / 小幅 orbit（< 100m 范围）/ 封闭容器 / Canvas2D / 纯粒子场。

---

## 一、核心问题

Gerstner ocean 的 80m × 80m × 256² 网格对固定相机足够。但如果用户想"从风暴海面飞到平静湖面"——60 秒连续滑翔，跨越 2000m——怎么办？

**方案A**：20× 网格 → 5M 顶点 → 移动端不可行  
**方案B**：Clipmap LOD → 同 256² 顶点数，覆盖 2000m

---

## 二、Clipmap 几何结构

### 2.1 同心环

```
         ┌─────────────────────────┐
         │  LOD=3  spacing=8       │  ← 外环（256²顶点 × 间距8 = 2048m 跨度）
         │   ┌─────────────────┐   │
         │   │ LOD=2  sp=4     │   │  ← 中环
         │   │  ┌─────────┐    │   │
         │   │  │LOD=1 sp=2│   │   │  ← 内环
         │   │  │ ┌───┐   │   │   │
         │   │  │ │LOD│   │   │   │  ← 中心块 (LOD=0, spacing=1)
         │   │  │ │=0 │   │   │   │
         │   │  │ └───┘   │   │   │
         │   │  └─────────┘   │   │
         │   └─────────────────┘   │
         └─────────────────────────┘
```

每一环的物理尺寸 = 上一环的 2×。顶点密度 = 上一环的 1/2。外环覆盖 8× 的范围、但顶点间距也是 8×——所以渲染负载恒定。

### 2.2 Chebyshev 距离分配 LOD

```glsl
// 用 Chebyshev 距离（max(|x|,|z|)）——方形环而非圆形环
// 简化计算，且与等间距网格自然对齐
float localDist = max(abs(position.x), abs(position.z));

// LOD 0 的内半径
float lod0Radius = (uResolution / 2.0) * uBaseVertexSpacing;

// LOD 级别：log2(localDist / lod0Radius)，向上取整
// -0.001 避免正好在边界上的顶点因浮点误差跳级
float lod = max(0.0, ceil(log2(localDist / lod0Radius) - 0.001));
```

**为什么 Chebyshev 不是 Euclidean**：Euclidean 距离 (`sqrt(x²+z²)`) 需要一次 sqrt + 两次乘法。Chebyshev 只需一次 max + 两次 abs。在 vertex shader 中被调用 65K 次/帧——sqrt 省下的成本是实质性的。

---

## 三、网格 Snapping 和 Morph

### 3.1 Camera-Relative Snapping

相机移动时，网格不是每帧连续跟随——以 gridSize 为单位离散跳动。这防止了顶点在屏幕上的"游泳"（sub-pixel jitter）。

```glsl
// 当前 LOD 的顶点间距
float gridSize = uBaseVertexSpacing * exp2(lod);

// 相机位置量化到 gridSize 的整数倍
vec2 snappedCamera = floor(uViewerPos.xz / gridSize) * gridSize;
vec2 worldXZ = position.xz + snappedCamera;
```

相机移动 < gridSize → snappedCamera 不变 → 顶点不抖。相机移动 ≥ gridSize → snappedCamera 跳一格 → 顶点一次位移正好 gridSize → 波函数在这些新位置上的采样值仍然是连续的——不会出现视觉跳动（只要是解析波，不是纹理采样）。

### 3.2 Morph 过渡（消除 LOD 硬切换）

在当前 LOD 环的最外 2 个 cell 内，顶点同时在当前 LOD 和下一 LOD 的网格位置之间线性混合：

```glsl
// 下一 LOD 的网格间距（2× 当前）
float nextGridSize = gridSize * 2.0;

// 如果直接用 snappedCamera —— 相机在 2.0 的整数倍时
// 和 snappedCamera2 —— 相机在 4.0 的整数倍时
// 两者差距可达 2m。但 vertex shader 通过 mix() 混合
// 两个世界坐标——混合的不是"相机位置"，而是
// "顶点在这两个不同频度网格上的位置"。

// 顶点在当前 LOD 网格上的世界 XZ
vec2 worldXZ = position.xz + snappedCamera;

// 同一顶点在下一 LOD 网格上的世界 XZ：
// 先量化到下一 LOD 的 grid
vec2 snappedCamera2 = floor(uViewerPos.xz / nextGridSize) * nextGridSize;

// 把当前 LOD 的 position 按 2× 量化为下一 LOD 的顶点位置
vec2 coarsePos = floor(position.xz / nextGridSize) * nextGridSize;
vec2 worldXZ_next = coarsePos + snappedCamera2;

// morph 区间：当前 LOD 的最外 2 个 cell
float currentRadius = lod0Radius * exp2(lod);
float morphStart = currentRadius - 2.0 * gridSize;
float morphAlpha = clamp((localDist - morphStart) / (2.0 * gridSize), 0.0, 1.0);

// 混合：0 = 使用当前 LOD，1 = 完全过渡到下一 LOD
vec2 finalWorldXZ = mix(worldXZ, worldXZ_next, morphAlpha);
```

**2-cell 过渡区的关键**：不是"pop"——是"fade"。顶点在 2 个 cell 范围内从细网格平滑变形到粗网格。变形过程中顶点在屏幕上的位置连续移动——不会出现"啪"的瞬移。

---

## 四、ClipmapGeometry JS 构造

```javascript
// 每个 LOD 环 = (m+1)² 顶点 − 中心空洞
// m = 分辨率（如 64）
// LOD 0: 完整的 (m+1)² 网格（无空洞）
// LOD 1+: (m+1)² − (m/2 − 1)²（中心挖空——中心由内环覆盖）

class ClipmapGeometry extends THREE.BufferGeometry {
  /**
   * @param {number} resolution — 每环的单轴顶点数（m），推荐 64–128
   * @param {number} levels — 环的层数（含 LOD 0），推荐 4–6
   * @param {number} baseVertexSpacing — LOD 0 的顶点间距（世界空间单位），推荐 1.0
   */
  constructor(resolution = 64, levels = 5, baseVertexSpacing = 1.0) {
    super();

    const m = resolution; // 每个环的 grid 尺寸
    // LOD 0: (m+1)² 顶点 + (m²) 个 quad × 6 = m² × 6 索引
    // LOD k: (m+1)² − (m/2 − 1)² 顶点 + (m² − (m/2)²) × 6 索引
    const quarterM = m / 4;
    const threeQuarterM = (3 * m) / 4;

    // 预计算总数
    const vCountLOD0 = (m + 1) * (m + 1);
    const vCountLODk = (m + 1) * (m + 1) - (m/2 - 1) * (m/2 - 1);
    const totalVerts = vCountLOD0 + (levels - 1) * vCountLODk;

    const iCountLOD0 = m * m * 6; // m² 个 quad × 2 triangles × 3 vertices
    const holeQuads = (m/2) * (m/2);
    const iCountLODk = (m * m - holeQuads) * 6;
    const totalIndices = iCountLOD0 + (levels - 1) * iCountLODk;

    const positions = new Float32Array(totalVerts * 3);
    const indices   = [];

    // 3D 查找表：vMap[level][z][x] = vertexIndex
    const vMap = [];

    let vIdx = 0;

    // --- 构建每层 LOD ---
    for (let L = 0; L < levels; L++) {
      const step = baseVertexSpacing * Math.pow(2, L);
      const map = [];

      for (let z = 0; z <= m; z++) {
        map[z] = [];
        for (let x = 0; x <= m; x++) {

          // LOD > 0 — 挖空中心
          if (L > 0 && x > quarterM && x < threeQuarterM &&
                       z > quarterM && z < threeQuarterM) {
            map[z][x] = -1; // 空洞
            continue;
          }

          // 顶点位置——局部空间，XZ 平面（Y=0）
          // position.xz ∈ [-m*step/2, +m*step/2]
          const px = (x - m / 2) * step;
          const pz = (z - m / 2) * step;
          positions[vIdx * 3]     = px;
          positions[vIdx * 3 + 1] = 0.0; // Y=0（vertex shader 中置换）
          positions[vIdx * 3 + 2] = pz;

          map[z][x] = vIdx;
          vIdx++;
        }
      }
      vMap.push(map);

      // --- 构建索引——三角形（CCW）---
      for (let z = 0; z < m; z++) {
        for (let x = 0; x < m; x++) {
          const a = map[z][x];       // top-left
          const b = map[z+1][x];     // bottom-left
          const c = map[z][x+1];     // top-right
          const d = map[z+1][x+1];   // bottom-right

          // 跳过——任意一角是空洞的 quad
          if (a === -1 || b === -1 || c === -1 || d === -1) continue;

          // CCW: (a, b, c) (c, b, d)
          indices.push(a, b, c);
          indices.push(c, b, d);
        }
      }
    }

    this.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    this.setIndex(indices);
    this.computeBoundingSphere(); // frustum culling 用，但 useOceanLOD 会禁用它
  }
}
```

### 4.1 使用示例

```javascript
const oceanGeo = new ClipmapGeometry(64, 5, 1.0);
// resolution=64  → 每环约 4225 顶点
// levels=5       → LOD0=4225 + LOD1-4 × 3841 = ~19,589 顶点总
// baseSpacing=1  → LOD0 覆盖 64m × 64m，最外环覆盖 1024m × 1024m
// 对比：固定 256² = 65,536 顶点覆盖 80m × 80m
// Clipmap 用 30% 的顶点覆盖了 12× 的范围
```

---

## 五、Vertex Shader LOD 计算（与 §三 对应）

完整 vertex shader 在 FFTOCEAN 中验证。适配 healing-space 时：FFT displacement 纹理替换为 Gerstner 解析计算。

```glsl
// === 顶点着色器 LOD 部分（嵌入 ocean.vert 或 terrain.vert）===
// uniform
uniform float uResolution;          // 每环的 m 值（如 64）
uniform float uBaseVertexSpacing;   // LOD 0 间距（如 1.0）
uniform vec2  uViewerPos;           // 相机世界 XZ（每帧更新）

void main() {
  vec3 pos = position;

  // 1. LOD 分配（Chebyshev 距离 + log2 取整）
  float localDist = max(abs(pos.x), abs(pos.z));
  float lod0Radius = (uResolution / 2.0) * uBaseVertexSpacing;
  float lod = max(0.0, ceil(log2(localDist / lod0Radius) - 0.001));

  // 2. 当前 LOD 的网格间距
  float gridSize = uBaseVertexSpacing * exp2(lod);

  // 3. 相机 snapping
  vec2 snappedCamera = floor(uViewerPos / gridSize) * gridSize;
  vec2 worldXZ = pos.xz + snappedCamera;

  // 4. 下一 LOD 的网格间距和 snapping（用于 morph）
  float nextGridSize = gridSize * 2.0;
  vec2 snappedCamera2 = floor(uViewerPos / nextGridSize) * nextGridSize;
  vec2 coarsePos = floor(pos.xz / nextGridSize) * nextGridSize;
  vec2 worldXZ_next = coarsePos + snappedCamera2;

  // 5. Morph 混合 alpha
  float currentRadius = lod0Radius * exp2(lod);
  float morphStart = currentRadius - 2.0 * gridSize;
  float morphAlpha = clamp((localDist - morphStart) / (2.0 * gridSize), 0.0, 1.0);

  // 6. 最终世界 XZ
  vec2 finalWorldXZ = mix(worldXZ, worldXZ_next, morphAlpha);

  // 7. Gerstner / 地形位移（基于 finalWorldXZ）
  // ... 原有位移逻辑，用 finalWorldXZ 代替 pos.xz ...

  vec3 displaced = vec3(finalWorldXZ.x, 0.0, finalWorldXZ.y);
  // ... 加 Gerstner displacement ...
}
```

---

## 六、useOceanLOD Hook（JS 端轻量驱动）

```javascript
// 每帧只做两件事：更新 uViewerPos、禁用 frustumCulled
import { useFrame } from '@react-three/fiber'; // 如果用 R3F
// 或直接 useFrame callback

function setupClipmapLOD(mesh, material) {
  // 1. 必须禁用 frustum culling
  //    因为 clipmap 的 bounding box 是中心块的 —— 外环在 bounding box 之外
  //    不关 culling：外环在相机看向地平线时被裁剪 → 海洋"消失"
  mesh.frustumCulled = false;

  // 2. 每帧更新相机位置
  function update(camera) {
    material.uniforms.uViewerPos.value.set(camera.position.x, camera.position.z);
  }

  return { update };
}
```

**为什么必须 `frustumCulled = false`**：clipmap 的外环 vertices 的物理位置（世界 XZ）在 vertex shader 中才计算。Three.js 的 frustum culling 只看到这些顶点在局部空间的位置（在 bounding sphere 内）——它不知道 vertex shader 会把它们挪到远处。

---

## 七、calm 参数映射

LOD 半径不只是"相机距离"驱动——也被 calm 调节：

```javascript
function applyClipmapCalmState(calm, material) {
  const ts = calm * calm * (3 - 2 * calm); // smoothstep

  const u = material.uniforms;

  // LOD 细节保留距离——calm 高时看得更远、更放松
  // lod0Radius = baseRadius × (1.0 + 0.5 × ts)
  // 焦虑：lod0Radius = 32m → 高细节区域更小 → "视野压缩"
  // 治愈：lod0Radius = 48m → 高细节区域更大 → "看得更远"
  u.uLodScale.value = 1.0 + 0.5 * ts;
}
```

shader 中乘以 uLodScale：
```glsl
float lod0Radius = (uResolution / 2.0) * uBaseVertexSpacing * uLodScale;
```

---

## 八、何时使用 / 何时不使用

| 条件 | 使用 Clipmap？ | 理由 |
|------|---------------|------|
| 固定相机 / 小幅 orbit（< 50m 移动） | ❌ | 固定网格 128²+ 足够——clipmap 复杂性不值得 |
| 飞越/滑翔/穿行（> 200m 移动）| ✅ | 固定网格覆盖不足——要么 500K 顶点要么 clipmap |
| 像素场景 / Canvas2D | ❌ | 不适用 |
| 纯粒子场 | ❌ | 粒子 LOD 用 instancing + distance culling |
| Terrain heightfield | ✅ | 完美匹配——地形是 clipmap 的原始用途 |
| 海面 × 水下双层 | ✅ | 海面 + 海底各一个 clipmap |

---

## 九、与 ocean-waves.md 的协作

ocean-waves.md 的 Gerstner shader 用 `position.xz` 作为世界 XZ 坐标：

```glsl
float dotP = dirX * pos.x + dirZ * pos.z;
```

改为使用 clipmap 的 `finalWorldXZ`：

```glsl
float dotP = dirX * finalWorldXZ.x + dirZ * finalWorldXZ.y;
```

其余（Gerstner displacement、法线、Jacobian、Fresnel、SSS）**全部不变**。Clipmap 只改变"顶点在世界空间的位置如何决定"——不碰 displacement 和 shading。

---

## 十、反模式

| # | 反模式 | 级别 | 表现 | 修复 |
|---|--------|------|------|------|
| 1 | frustumCulled 未禁用 | **致命** | 外环不渲染——海洋在地平线处"截断" | `mesh.frustumCulled = false` |
| 2 | morph 区太窄（< 1 cell）| 警告 | LOD 环形边界可见——密度变化的明确分界线 | morphAlpha 覆盖 ≥ 2 个 cell |
| 3 | levels > 6 | 警告 | 外环顶点间距 = baseSpacing × 64 → 远处波浪细节全部丢失 | levels ≤ 5，外环步长 ≤ baseSpacing × 32 |
| 4 | 固定相机用 clipmap | 警告 | 多余的 vertex shader 指令——每帧 65K 次 log2/exp2 白白浪费 | 固定相机用固定网格 |
| 5 | 忘记传 uViewerPos | **致命** | 顶点全部塌到 local space → 看不到任何 displacement | 每帧 `uViewerPos.value.set(camera.position.x, camera.position.z)` |

---

## 十一、自检清单

- [ ] `mesh.frustumCulled = false` 已设置？
- [ ] `uViewerPos` 每帧更新了 camera.position.xz？
- [ ] levels ≤ 5（外环步长 ≤ baseSpacing × 32）？
- [ ] morphAlpha 覆盖 ≥ 2 个 cell 吗？
- [ ] Gerstner displacement 基于 `finalWorldXZ`（不是 `position.xz`）？
- [ ] calm 映射了 uLodScale（高细节保留距离）？
- [ ] 移动端：levels 降为 4、resolution 降为 48？
