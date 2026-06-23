# Physarum Transport Network — 粘菌网络 / 孤独→连接

Physarum Polycephalum（多头绒泡菌）是一种单细胞生物，能自发形成连接食物源的最优路径网络。
**孤独的个体粒子，在感知与跟随彼此信号素中，自发连成美丽网络**——这是"孤独→连接"情绪的完美物理同构。

**疗愈叙事**：散落的光粒子→互相感知→自发织成光网（"我们都在寻找彼此"）。

## 目录

- [一、粘菌算法原理](#一粘菌算法原理)
- [二、三纹理架构](#二三纹理架构)
- [三、粒子感知 + 移动 Shader](#三粒子感知--移动-shader)
- [四、Trail 扩散 + 衰减 Shader](#四trail-扩散--衰减-shader)
- [五、情绪叙事参数调优](#五情绪叙事参数调优)
- [六、渲染：将网络画成光轨](#六渲染将网络画成光轨)
- [七、完整主循环集成](#七完整主循环集成)

---

## 一、粘菌算法原理

每个"粒子"（粘菌细胞）有**位置** (x, y) 和**朝向** (angle)，每帧做：

1. **感知**：在前方 `senseAngle` 偏左、正前方、偏右 3 点采样 Trail 密度
2. **转向**：朝密度最高方向转 `rotateAngle` 度
3. **移动**：沿朝向走 `stepSize`
4. **沉积**：在当前位置留下信息素 Trail

Trail 本身每帧：扩散（与邻居 lerp）+ 衰减（× 衰减系数）

---

## 二、三纹理架构

```javascript
const W = 512, H = 512;
const AGENTS = 100000;

// Texture 1：Trail Map（信息素浓度图）—— R 通道存浓度
let rtTrailA = new THREE.WebGLRenderTarget(W, H, {
    format: THREE.RGBAFormat,
    type: THREE.HalfFloatType,
    minFilter: THREE.LinearFilter,  // Trail 可双线性（平滑扩散）
    magFilter: THREE.LinearFilter,
});
let rtTrailB = rtTrailA.clone();

// Texture 2：Particle State（粒子状态）—— (x, y, angle, _) per particle
// 每行是一个粒子，PTEX_W × PTEX_H 覆盖所有粒子
const PTEX_W = 1024;
const PTEX_H = Math.ceil(AGENTS / PTEX_W);
let rtParticleA = new THREE.WebGLRenderTarget(PTEX_W, PTEX_H, {
    format: THREE.RGBAFormat,
    type: THREE.FloatType,          // 粒子位置需要 32 位精度
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
});
let rtParticleB = rtParticleA.clone();
```

> **为什么用纹理存粒子状态**：CPU 数组无法并行读取；纹理可在 fragment shader 中并行索引，实现 10 万粒子 GPU 并行更新。

---

## 三、粒子感知 + 移动 Shader

```glsl
// id="physarum-agent-vs"
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position, 1.0); }
```

```glsl
// id="physarum-agent-fs"（更新每个粒子的位置和朝向）
uniform sampler2D tParticles;   // 当前粒子状态（x, y, angle, _）
uniform sampler2D tTrail;       // 当前 Trail 浓度图
uniform float uTime;
uniform float uSenseAngle;      // 感知偏角，默认 0.785（π/4 = 45°）
uniform float uSenseDist;       // 感知距离，默认 0.02
uniform float uRotateAngle;     // 转向角，默认 0.785
uniform float uStepSize;        // 步长，默认 0.001
varying vec2 vUv;

// 采样指定方向的 Trail 浓度
float sense(vec2 pos, float angle) {
    vec2 sp = pos + vec2(cos(angle), sin(angle)) * uSenseDist;
    return texture2D(tTrail, fract(sp)).r;
}

// 简单伪随机（per-fragment 随机，避免所有粒子同步）
float rand(vec2 uv, float t) {
    return fract(sin(dot(uv + t, vec2(12.9898, 78.233))) * 43758.5453);
}

void main() {
    vec4 p     = texture2D(tParticles, vUv);
    vec2 pos   = p.rg;
    float ang  = p.b;

    float fwd  = sense(pos, ang);
    float left = sense(pos, ang + uSenseAngle);
    float rgt  = sense(pos, ang - uSenseAngle);

    float newAng = ang;
    if (fwd >= left && fwd >= rgt) {
        // 直行
    } else if (fwd < left && fwd < rgt) {
        // 随机左右（打破对称性）
        newAng += (rand(vUv, uTime) < 0.5 ? 1.0 : -1.0) * uRotateAngle;
    } else if (left > rgt) {
        newAng += uRotateAngle;
    } else {
        newAng -= uRotateAngle;
    }

    vec2 newPos = fract(pos + vec2(cos(newAng), sin(newAng)) * uStepSize);

    gl_FragColor = vec4(newPos, newAng, 1.0);
}
```

---

## 四、Trail 扩散 + 衰减 Shader

```glsl
// id="physarum-trail-fs"（扩散 + 衰减，粒子沉积用 additive pass）
uniform sampler2D tTrail;
uniform vec2 uTexelSize;
uniform float uDecay;    // 衰减系数，默认 0.98
uniform float uDiffuse;  // 扩散权重，默认 0.15
varying vec2 vUv;

void main() {
    vec4 c  = texture2D(tTrail, vUv);
    vec4 up = texture2D(tTrail, vUv + vec2(0.0,  uTexelSize.y));
    vec4 dn = texture2D(tTrail, vUv - vec2(0.0,  uTexelSize.y));
    vec4 lt = texture2D(tTrail, vUv - vec2(uTexelSize.x, 0.0));
    vec4 rt = texture2D(tTrail, vUv + vec2(uTexelSize.x, 0.0));

    vec4 avg = (c + up + dn + lt + rt) / 5.0;
    gl_FragColor = mix(c, avg, uDiffuse) * uDecay;
}
```

**粒子沉积（JS 侧 additive blending pass）**：

```javascript
// 每帧：把粒子位置读出来（或用 GPU 点精灵），以 AdditiveBlending 叠加到 Trail
// 简化方案：用 Points（粒子云）在 rtTrail 上绘制白色点
const depositGeo = new THREE.BufferGeometry();
// 每帧从 rtParticle.texture 读位置（慢，适合 ≤ 5万粒子）
// 大粒子数推荐：在 physarum-agent-fs 中同时写出沉积坐标到另一通道，用 GPU 合并
const depositMat = new THREE.PointsMaterial({
    size: 1 / W,
    color: 0xffffff,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: false,
});
```

---

## 五、情绪叙事参数调优

| 参数 | 孤独感（初始） | 连接感（治愈态） |
|------|-------------|-------------|
| `AGENTS` | 20,000 | 100,000 |
| `senseAngle` | π/6（30°）| π/3（60°）|
| `senseDist` | 0.01 | 0.03 |
| `rotateAngle` | π/6 | π/4 |
| `stepSize` | 0.0005 | 0.001 |
| `decay` | 0.92（快速消散） | 0.98（持久网络）|

```javascript
const LONELY   = { senseAngle:0.524, senseDist:0.01, rotateAngle:0.524, stepSize:0.0005, decay:0.92 };
const CONNECT  = { senseAngle:1.047, senseDist:0.03, rotateAngle:0.785, stepSize:0.001,  decay:0.98 };

function updatePhysarum(calm) {
    const lerp = (a, b, t) => a + (b - a) * t;
    agentMat.uniforms.uSenseAngle.value  = lerp(LONELY.senseAngle,  CONNECT.senseAngle,  calm);
    agentMat.uniforms.uSenseDist.value   = lerp(LONELY.senseDist,   CONNECT.senseDist,   calm);
    agentMat.uniforms.uRotateAngle.value = lerp(LONELY.rotateAngle, CONNECT.rotateAngle, calm);
    agentMat.uniforms.uStepSize.value    = lerp(LONELY.stepSize,    CONNECT.stepSize,    calm);
    trailMat.uniforms.uDecay.value       = lerp(LONELY.decay,       CONNECT.decay,       calm);
}
```

---

## 六、渲染：将网络画成光轨

```glsl
// id="physarum-render-fs"
uniform sampler2D tTrail;
uniform float uCalm;
varying vec2 vUv;

void main() {
    float trail = texture2D(tTrail, vUv).r;

    // 孤独色板：冷暗蓝灰，细弱丝线
    vec3 lonely = mix(
        vec3(0.02, 0.03, 0.06),
        vec3(0.10, 0.20, 0.42),
        pow(trail, 2.0)
    );

    // 连接色板：温暖金白网络
    vec3 connected = mix(
        vec3(0.03, 0.04, 0.08),
        vec3(0.92, 0.82, 0.62),
        pow(trail, 1.2)
    );

    vec3 color = mix(lonely, connected, uCalm);

    // 高密度连接处发光
    float glow = smoothstep(0.3, 0.8, trail);
    color += vec3(1.0, 0.9, 0.7) * glow * 0.4 * uCalm;

    gl_FragColor = vec4(color, 1.0);
}
```

---

## 七、完整主循环集成

```javascript
function loopPhysarum() {
    requestAnimationFrame(loopPhysarum);

    const t = performance.now() / 1000;
    agentMat.uniforms.uTime.value = t;

    // Step 1：更新粒子（agent shader）
    agentMat.uniforms.tParticles.value = rtParticleA.texture;
    agentMat.uniforms.tTrail.value     = rtTrailA.texture;
    renderer.setRenderTarget(rtParticleB);
    renderer.render(agentScene, simCamera);

    // Step 2：Trail 扩散 + 衰减
    trailMat.uniforms.tTrail.value = rtTrailA.texture;
    renderer.setRenderTarget(rtTrailB);
    renderer.render(trailScene, simCamera);

    // Swap
    let tmp = rtParticleA; rtParticleA = rtParticleB; rtParticleB = tmp;
    tmp = rtTrailA; rtTrailA = rtTrailB; rtTrailB = tmp;

    // Step 3：渲染到屏幕
    renderer.setRenderTarget(null);
    renderMat.uniforms.tTrail.value = rtTrailA.texture;
    renderMat.uniforms.uCalm.value  = State.calm;
    renderer.render(renderScene, renderCamera);

    // 更新参数
    updatePhysarum(State.calm);
}
```

> **移动端优化**：将 `AGENTS` 降到 20,000，`W/H` 降到 256，`decay` 调高到 0.99（补偿分辨率降低导致的扩散不足）。
