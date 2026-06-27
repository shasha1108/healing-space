# Raymarching — SDF 液态 3D / 无 Mesh 构建空间

Raymarching（光线步进）+ SDF（有符号距离函数）：**无需任何 mesh，仅在 fragment shader 内构建完整 3D 世界**。
液态气泡、熔融形态、穿越雾墙——都能在一个 shader 里实现。

与 Three.js 集成：全屏正交相机 + PlaneGeometry，fragment shader 内完成整个 3D 渲染。

---

## ⛔ Healing 场景禁用组合——已验证触发 Body Horror

> **验证事件（2026-06-22）**：「多个 SDF 球体 + smin 融合 + 任何强度域扭曲」——无论颜色是暗棕金还是深海蓝，渲染结果都产生"肉球涌动/器官蠕动"的恐怖感。用户反馈"san值掉"。**这是结构性问题，无法通过调参修复。**

### 禁止组合（三个根因——不是参数问题，是结构性错误）

#### 根因一：多球 smin = 生物组织合并感

`smin()` 的数学本质是"平滑最小值"，渲染出的形态就是"两个体积合并时出现的颈部连接"——这完全同构于生物软组织合并（细胞分裂、器官融合、皮肤粘连）。人类视觉系统对此有强烈的生理反应，无论颜色如何。**这是结构性错误，调参无法修复。**

| 组合 | 判定 |
|------|------|
| 3+ 个 sdSphere + smin 融合 | ❌ 禁止。单球允许（无融合 = 无组织感）。替代方案：FBO 流体、粒子系统、p5.js |

#### 根因二：球体 + 域扭曲 = 皮肤/肌肉纹理

Domain warp 在球面上产生的凹陷和褶皱，与皮肤褶皱/肌肉纹理几何上完全相同。强度 > 0.15 时，结果让人联想到肿瘤/腐肉/蠕动的器官表面。

| 组合 | 判定 |
|------|------|
| sdSphere + domain warp（强度 > 0.15） | ❌ 禁止。域扭曲只能用于：全屏背景（无几何体）、抽象非球体 SDF（环、管道） |

#### 根因三：暗棕金配色 + Raymarching 精准光照 = 有机组织色

Raymarching 的逐像素法线计算产生非常真实的漫反射光照。暗棕金 `vec3(0.31,0.17,0.05)` + 琥珀 glow `vec3(0.50,0.26,0.05)` 在真实光照下的颜色特征与人类皮肤/脂肪/腐肉完全重叠。

| 组合 | 判定 |
|------|------|
| 暗棕金/暖橙色 + 任何 SDF 几何体 | ❌ 禁止。Healing Raymarching 只选：深海蓝、靛紫、冰蓝、珍珠白 |

### 允许用于 Healing 的 Raymarching 模式

| 模式 | 安全的原因 |
|------|---------|
| 单体大型 SDF（一个球、一个环、一个抽象管道） | 无融合 = 无生物组织联想 |
| 纯 Domain Warping 全屏背景（不含几何体） | 产生极光/云雾，不含有机形体 |
| sdTorus / sdCapsule（非球体） | 形状本身无生物联想 |
| Raymarching 仅用于雾/体积光（不渲染实体表面） | 无表面法线 = 无皮肤质感 |

**结论：Healing H5 中若隐喻是"流体/气泡/溶融"，优先选 FBO 流体（gpu-fluid.md）或粒子系统，而非 Raymarching SDF 几何体。**

---

## 目录

- [一、核心算法骨架（最小50行）](#一核心算法骨架最小50行)
- [二、SDF 基础形状库](#二sdf-基础形状库)
- [三、smin() 光滑融合](#三smin-光滑融合)
- [四、法线计算（光照）](#四法线计算光照)
- [五、Domain Warping（域扭曲）](#五domain-warping域扭曲)
- [六、Glow 效果（距离场发光）](#六glow-效果距离场发光)
- [七、情绪场景模板：压抑→液态流动](#七情绪场景模板压抑液态流动)
- [八、与 Three.js 集成](#八与-threejs-集成)

---

## 一、核心算法骨架（最小50行）

```glsl
// id="ray-fs"（全屏正交，见 §八 集成方式）
precision highp float;
uniform float uTime;
uniform vec2  uResolution;
uniform float uCalm;
varying vec2  vUv;

// ==== SDF 场景 ====
float scene(vec3 p);  // 前向声明，在 §二 实现

// ==== Raymarching 主循环 ====
float rayMarch(vec3 ro, vec3 rd) {
    float t = 0.0;
    for (int i = 0; i < 80; i++) {
        float d = scene(ro + rd * t);
        if (d < 0.001) return t;
        if (t > 50.0)  return -1.0;
        t += d;
    }
    return -1.0;
}

// ==== 法线（数值微分）====
vec3 calcNormal(vec3 p) {
    const float e = 0.001;
    return normalize(vec3(
        scene(p+vec3(e,0,0)) - scene(p-vec3(e,0,0)),
        scene(p+vec3(0,e,0)) - scene(p-vec3(0,e,0)),
        scene(p+vec3(0,0,e)) - scene(p-vec3(0,0,e))
    ));
}

void main() {
    vec2 uv = (vUv - 0.5) * vec2(uResolution.x / uResolution.y, 1.0);
    vec3 ro = vec3(0.0, 0.0, 3.0);     // 相机位置
    vec3 rd = normalize(vec3(uv, -1.5)); // 光线方向（焦距 1.5）

    float t = rayMarch(ro, rd);

    if (t < 0.0) {
        // 背景：深色场景
        gl_FragColor = vec4(0.02, 0.03, 0.07, 1.0);
        return;
    }

    vec3 hit = ro + rd * t;
    vec3 N   = calcNormal(hit);
    vec3 L   = normalize(vec3(2.0, 4.0, 3.0));

    float diff = max(dot(N, L), 0.0);
    float spec = pow(max(dot(reflect(-L, N), -rd), 0.0), 32.0);

    vec3 col = vec3(0.3, 0.5, 1.0) * diff + spec * 0.5;
    gl_FragColor = vec4(col, 1.0);
}
```

---

## 二、SDF 基础形状库

```glsl
// 球体
float sdSphere(vec3 p, float r) { return length(p) - r; }

// 盒子（b = 半边长）
float sdBox(vec3 p, vec3 b) {
    vec3 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

// 胶囊体（丝带/水草/发丝质感）
float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a, ba = b - a;
    float h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
    return length(pa - ba * h) - r;
}

// 圆环（呼吸圈/水波纹）
float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

// 布尔运算
float opU(float a, float b) { return min(a, b); }   // 并集
float opI(float a, float b) { return max(a, b); }   // 交集
float opS(float a, float b) { return max(a, -b); }  // A 减去 B
```

---

## 三、smin() 光滑融合

`smin` 让两个形状有机融合而非生硬布尔并集。**液态水滴合并、气泡融合、有机组织**的核心函数：

```glsl
// 多项式 smooth minimum，k 控制融合半径
float smin(float a, float b, float k) {
    float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0);
    return mix(b, a, h) - k * h * (1.0 - h);
}
```

使用示例：

```glsl
float scene(vec3 p) {
    float t   = uTime;
    float s1  = sdSphere(p - vec3(sin(t*0.7)*0.6, cos(t*0.5)*0.4, 0.0), 0.5);
    float s2  = sdSphere(p - vec3(cos(t*0.5)*0.6, sin(t*0.4)*0.5, 0.2), 0.4);
    float s3  = sdSphere(p - vec3(0.0, sin(t*0.3)*0.4, cos(t*0.6)*0.4), 0.35);
    // 级联融合
    return smin(s1, smin(s2, s3, 0.4), 0.4);
}
```

> **k 调参**：k=0.0 → 生硬布尔；k=0.3~0.5 → 水滴感；k=0.8+ → 极软气泡融合。治愈类取 k=0.3~0.6。

---

## 四、法线计算（光照）

数值微分法——无需手动推导任何形状的法线，对任意 SDF 都适用：

```glsl
vec3 calcNormal(vec3 p) {
    const float e = 0.001;
    return normalize(vec3(
        scene(p+vec3(e,0,0)) - scene(p-vec3(e,0,0)),
        scene(p+vec3(0,e,0)) - scene(p-vec3(0,e,0)),
        scene(p+vec3(0,0,e)) - scene(p-vec3(0,0,e))
    ));
}

// Blinn-Phong + 环境光
vec3 shade(vec3 p, vec3 rd) {
    vec3 N    = calcNormal(p);
    vec3 L    = normalize(vec3(2.0, 4.0, 3.0));
    float amb = 0.12;
    float dif = max(dot(N, L), 0.0) * 0.7;
    float spc = pow(max(dot(reflect(-L,N), -rd), 0.0), 32.0) * 0.4;
    return vec3(amb + dif + spc);
}
```

---

## 五、Domain Warping（域扭曲）

用噪声扭曲坐标系，产生有机的云雾/岩浆/极光质感：

```glsl
// fBM（需要 snoise，见 shader-patterns.md §八）
float fbm(vec3 p) {
    float v = 0.0, amp = 0.5;
    for (int i = 0; i < 5; i++) {
        v += amp * snoise(p);
        p = p * 2.0 + vec3(1.7, 9.2, 5.3);
        amp *= 0.5;
    }
    return v;
}

// 双层域扭曲（关键：两次 fBM 叠加产生极光/岩浆层次感）
float domainWarp(vec3 p, float t) {
    vec3 q = vec3(
        fbm(p + t * 0.2),
        fbm(p + vec3(5.2, 1.3, 0.0) + t * 0.15),
        fbm(p + vec3(1.3, 8.7, 0.0) + t * 0.18)
    );
    vec3 r = vec3(
        fbm(p + 4.0*q + vec3(1.7, 9.2, 3.3)),
        fbm(p + 4.0*q + vec3(8.3, 2.8, 5.1)),
        fbm(p + 4.0*q + vec3(5.4, 6.8, 1.2))
    );
    return fbm(p + 4.0 * r);
}

// 在 SDF 中用域扭曲：压抑 → 有机流体
float scene(vec3 p) {
    float warpStrength = mix(0.8, 0.15, uCalm);  // calm↑ → 扭曲↓（趋于平静）
    float warp = domainWarp(p * 0.4, uTime * 0.05) * warpStrength;
    return smin(sdSphere(p, 1.0), sdTorus(p, vec2(1.5, 0.2)), 0.5) + warp * 0.3;
}
```

> **Domain Warping 调参**：空间频率 `p * 0.4`（越小越宏观）；流速 `uTime * 0.05`（治愈取 0.02~0.08）；扭曲幅度 `warp * 0.3`（0.2~0.6 是舒适区）。

---

## 六、Glow 效果（距离场发光）

无需额外 pass，在 rayMarch 循环中累积接近度实现发光：

```glsl
// 在 rayMarch 内累积
float glow = 0.0;
float t    = 0.0;
for (int i = 0; i < 80; i++) {
    float d = scene(ro + rd * t);
    glow += exp(-d * 12.0) * 0.04;  // 越近 glow 越强，指数衰减
    if (d < 0.001) break;
    t += d;
    if (t > 50.0) break;
}

// 叠加到最终颜色
vec3 glowColor = mix(vec3(0.2, 0.4, 1.0), vec3(0.9, 0.8, 0.6), uCalm);
vec3 finalColor = surfaceColor + glowColor * glow * 1.5;
```

---

## 七、情绪场景模板：压抑→液态流动

```glsl
// 完整场景：三个浮动液态球体 + 域扭曲
float scene(vec3 p) {
    float t  = uTime;
    float s1 = sdSphere(p - vec3(sin(t*0.5)*0.8, cos(t*0.3)*0.6, 0.0), 0.5);
    float s2 = sdSphere(p - vec3(cos(t*0.7)*0.6, sin(t*0.4)*0.8, 0.2), 0.4);
    float s3 = sdSphere(p - vec3(0.0, sin(t*0.2)*0.3, cos(t*0.6)*0.5), 0.35);
    float merged = smin(s1, smin(s2, s3, 0.4), 0.4);

    // 压抑态扭曲更强，治愈态趋于平滑
    float warpStr = mix(0.7, 0.1, uCalm);
    float warp = domainWarp(p * 0.5, t * 0.04) * warpStr;
    return merged + warp * 0.25;
}

// 颜色：压抑 = 暗棕金，治愈 = 冰蓝白
vec3 getSurfaceColor(vec3 p, vec3 N, vec3 rd) {
    vec3 suppressed = vec3(0.35, 0.22, 0.08);  // 暗棕金
    vec3 released   = vec3(0.45, 0.75, 1.0);   // 冰蓝白
    vec3 baseCol    = mix(suppressed, released, uCalm);
    float light     = 0.1 + max(dot(N, normalize(vec3(2,4,3))), 0.0) * 0.8;
    float rim       = 1.0 - max(dot(N, -rd), 0.0);  // 边缘光
    return baseCol * light + rim * rim * 0.3 * released;
}
```

---

## 八、与 Three.js 集成

```javascript
// 全屏正交 shader（同 gpu-fluid.md §一 模式）
const bgGeo = new THREE.PlaneGeometry(2, 2);
const bgMat = new THREE.ShaderMaterial({
    uniforms: {
        uTime:       { value: 0 },
        uResolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
        uCalm:       { value: 0 },
    },
    vertexShader:   `varying vec2 vUv; void main(){vUv=uv; gl_Position=vec4(position,1.);}`,
    fragmentShader: document.getElementById('ray-fs').textContent,
    depthWrite: false,
    depthTest:  false,
});
const bgScene  = new THREE.Scene();
const bgCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1);
bgScene.add(new THREE.Mesh(bgGeo, bgMat));

// 主循环：先渲染 Raymarching 背景，再叠加粒子前景
renderer.autoClear = false;
function animate(time) {
    requestAnimationFrame(animate);
    bgMat.uniforms.uTime.value = time * 0.001;
    bgMat.uniforms.uCalm.value = State.calm;
    renderer.clear();
    renderer.render(bgScene, bgCamera);   // 1. Raymarching 背景
    renderer.render(scene, camera);       // 2. Three.js 粒子前景（可选）
}

// 性能：移动端降步数（在 GLSL 里 #define MAX_STEPS 40）
// 或降渲染分辨率：renderer.setPixelRatio(0.5)
```

> **速查：SDF → smin → glow 三件套**适用于"溶融/气泡/液态包裹"类隐喻。Domain Warping 适用于"极光/岩浆/呼吸雾气"类背景。两者可以叠加。
