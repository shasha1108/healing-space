# Reaction-Diffusion — Turing 图案 / 焦虑→结晶

Gray-Scott 反应扩散模型：两种化学物质在空间中扩散和反应，产生斑点、条纹、珊瑚等 Turing 图案。
**混沌中自发涌现的秩序**——天然就是"焦虑→结晶"的视觉隐喻。

**疗愈叙事**：随机噪声（情绪混乱）→ 用户手指注入化学物质（主动参与）→ 图案从混沌涌现（秩序来自内在）。

## 目录

- [一、Gray-Scott 模型原理](#一gray-scott-模型原理)
- [二、WebGL FBO 实现骨架](#二webgl-fbo-实现骨架)
- [三、模拟 Shader（反应扩散核心）](#三模拟-shader反应扩散核心)
- [四、渲染 Shader（浓度 → 色彩映射）](#四渲染-shader浓度--色彩映射)
- [五、情绪场景参数配方](#五情绪场景参数配方)
- [六、交互：手指注入化学物质](#六交互手指注入化学物质)
- [七、初始化状态与种子](#七初始化状态与种子)

---

## 一、Gray-Scott 模型原理

两种化学物质 U（基底）和 V（催化剂）在空间中扩散和反应：

```
dU/dt = Du·∇²U  −  U·V²  +  F·(1−U)
dV/dt = Dv·∇²V  +  U·V²  −  (F+k)·V
```

- `Du`, `Dv`：扩散系数（U 扩散快，V 扩散慢）
- `F`（Feed）：U 的注入速率
- `k`（Kill）：V 的消亡速率
- `∇²`：拉普拉斯算子（邻近像素的加权平均与中心的差）

**F 和 k 决定图案类型**：

| F | k | 图案 | 情绪隐喻 |
|---|---|------|---------|
| 0.035 | 0.065 | 珊瑚状斑点 | 焦虑→边界感 |
| 0.060 | 0.062 | 迷宫条纹 | 压抑→呼吸通道 |
| 0.025 | 0.060 | 气泡升腾 | 窒息→呼吸 |
| 0.012 | 0.050 | 超慢结晶 | 冻结感→融化 |
| 0.037 | 0.060 | 虫状纹路 | 纠缠→梳理 |

---

## 二、WebGL FBO 实现骨架

```javascript
const W = 512, H = 512;

// ⚠️ 反应扩散用 NearestFilter（避免插值污染化学浓度）
const fboConfig = {
    format: THREE.RGBAFormat,
    type: THREE.HalfFloatType,
    minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter,
};
let rtA = new THREE.WebGLRenderTarget(W, H, fboConfig);
let rtB = new THREE.WebGLRenderTarget(W, H, fboConfig);

// 模拟 Shader 场景（正交 + 全屏四边形，同 gpu-fluid.md §一）
const simMat = new THREE.ShaderMaterial({
    uniforms: {
        tUV:         { value: null },
        uF:          { value: 0.035 },
        uK:          { value: 0.065 },
        uDu:         { value: 0.16 },
        uDv:         { value: 0.08 },
        udt:         { value: 1.0 },
        uMouse:      { value: new THREE.Vector2(-1, -1) },
        uBrush:      { value: 0.0 },
        uTexelSize:  { value: new THREE.Vector2(1/W, 1/H) },
    },
    vertexShader:   document.getElementById('ortho-vs').textContent,
    fragmentShader: document.getElementById('rd-sim-fs').textContent,
});
simScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), simMat));

// 每帧跑 8 步（单步变化太微小，8 步/帧是疗愈速度的甜点）
function stepRD() {
    for (let i = 0; i < 8; i++) {
        simMat.uniforms.tUV.value = rtA.texture;
        renderer.setRenderTarget(rtB);
        renderer.render(simScene, simCamera);
        const tmp = rtA; rtA = rtB; rtB = tmp;
    }
    renderer.setRenderTarget(null);
}
```

---

## 三、模拟 Shader（反应扩散核心）

```glsl
// id="ortho-vs"
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position, 1.0); }
```

```glsl
// id="rd-sim-fs"
uniform sampler2D tUV;
uniform float uF, uK, uDu, uDv, udt;
uniform vec2 uTexelSize;
uniform vec2 uMouse;
uniform float uBrush;
varying vec2 vUv;

void main() {
    vec2 uv = vUv;
    vec4 center = texture2D(tUV, uv);
    float u = center.r;
    float v = center.g;

    // 9点拉普拉斯卷积（比4点更稳定）
    vec4 up = texture2D(tUV, uv + vec2(0.0,  uTexelSize.y));
    vec4 dn = texture2D(tUV, uv - vec2(0.0,  uTexelSize.y));
    vec4 lt = texture2D(tUV, uv - vec2(uTexelSize.x, 0.0));
    vec4 rt = texture2D(tUV, uv + vec2(uTexelSize.x, 0.0));
    vec4 ul = texture2D(tUV, uv + vec2(-uTexelSize.x,  uTexelSize.y));
    vec4 ur = texture2D(tUV, uv + vec2( uTexelSize.x,  uTexelSize.y));
    vec4 dl = texture2D(tUV, uv + vec2(-uTexelSize.x, -uTexelSize.y));
    vec4 dr = texture2D(tUV, uv + vec2( uTexelSize.x, -uTexelSize.y));

    float lapU = -u
        + 0.20*(up.r+dn.r+lt.r+rt.r)
        + 0.05*(ul.r+ur.r+dl.r+dr.r);
    float lapV = -v
        + 0.20*(up.g+dn.g+lt.g+rt.g)
        + 0.05*(ul.g+ur.g+dl.g+dr.g);

    // Gray-Scott 反应方程
    float uvv  = u * v * v;
    float newU = u + (uDu * lapU - uvv + uF * (1.0 - u)) * udt;
    float newV = v + (uDv * lapV + uvv - (uF + uK) * v) * udt;

    // 用户手指注入 V（触发图案在手指处生长）
    float dist   = length(vUv - uMouse);
    float inject = smoothstep(0.04, 0.01, dist) * uBrush;
    newV += inject * 0.5;

    gl_FragColor = vec4(clamp(newU,0.,1.), clamp(newV,0.,1.), 0.0, 1.0);
}
```

---

## 四、渲染 Shader（浓度 → 色彩映射）

```glsl
// id="rd-render-fs"
uniform sampler2D tUV;
uniform float uCalm;
varying vec2 vUv;

void main() {
    float v = texture2D(tUV, vUv).g;  // V 的浓度（0~1）

    // 焦虑调色板（冷灰蓝）
    vec3 anxious = mix(
        vec3(0.04, 0.06, 0.12),   // 低浓度：深蓝黑
        vec3(0.18, 0.38, 0.75),   // 高浓度：焦虑蓝
        v
    );

    // 治愈调色板（温暖珍珠金）
    vec3 healing = mix(
        vec3(0.06, 0.10, 0.16),   // 低浓度：深靛蓝
        vec3(0.92, 0.88, 0.72),   // 高浓度：珍珠金
        pow(v, 0.7)
    );

    vec3 color = mix(anxious, healing, uCalm);

    // 图案边缘发光（微分检测轮廓）
    float edge = abs(dFdx(v)) + abs(dFdy(v));
    color += vec3(0.5, 0.8, 1.0) * edge * 8.0 * uCalm;

    gl_FragColor = vec4(color, 1.0);
}
```

---

## 五、情绪场景参数配方

```javascript
const RECIPES = {
    anxiety_coral:      { F: 0.035, k: 0.065, Du: 0.16, Dv: 0.08 },  // 焦虑→珊瑚（推荐入门）
    suppression_maze:   { F: 0.060, k: 0.062, Du: 0.14, Dv: 0.06 },  // 压抑→迷宫通道
    suffocation_bubbles:{ F: 0.025, k: 0.060, Du: 0.16, Dv: 0.08 },  // 窒息→气泡升腾
    frozen_thaw:        { F: 0.012, k: 0.050, Du: 0.20, Dv: 0.10 },  // 冻结→超慢融化
};

// 用 calm 驱动参数过渡（禁止瞬间跳变，会让图案崩掉）
function applyRecipe(mat, recipe, calm) {
    const from = RECIPES.anxiety_coral;
    const to   = RECIPES.suffocation_bubbles;  // 目标配方由隐喻决定
    const t    = calm;
    mat.uniforms.uF.value  = from.F  + (to.F  - from.F)  * t;
    mat.uniforms.uK.value  = from.k  + (to.k  - from.k)  * t;
    mat.uniforms.uDu.value = from.Du + (to.Du - from.Du) * t;
    mat.uniforms.uDv.value = from.Dv + (to.Dv - from.Dv) * t;
}
```

---

## 六、交互：手指注入化学物质

```javascript
let mouseUV = new THREE.Vector2(-1, -1);

canvas.addEventListener('mousemove', (e) => {
    mouseUV.set(
        e.clientX / window.innerWidth,
        1.0 - e.clientY / window.innerHeight  // WebGL y 轴反转
    );
    simMat.uniforms.uMouse.value.copy(mouseUV);
});

canvas.addEventListener('mousedown', () => { simMat.uniforms.uBrush.value = 1.0; });
canvas.addEventListener('mouseup',   () => { simMat.uniforms.uBrush.value = 0.0; });
canvas.addEventListener('touchmove', (e) => {
    e.preventDefault();
    const t = e.touches[0];
    mouseUV.set(t.clientX/window.innerWidth, 1.0 - t.clientY/window.innerHeight);
    simMat.uniforms.uMouse.value.copy(mouseUV);
    simMat.uniforms.uBrush.value = 1.0;
}, { passive: false });
canvas.addEventListener('touchend', () => { simMat.uniforms.uBrush.value = 0.0; });
```

> **疗愈叙事落地**：页面开场 = 中心种子注入 + 图案开始向外扩散（"你的感受开始发酵"）；用户手指划过 = 注入新化学物质催化更多图案（"你的触碰在改变它"）；calm > 0.7 时调色板渐变到 healing 配色（"秩序从混沌中涌现"）。

---

## 七、初始化状态与种子

```javascript
function initRD(renderer, rt, W, H) {
    // DataTexture 预填：U=1, V=0（空白基底）
    const data = new Float16Array(W * H * 4);
    for (let i = 0; i < W * H; i++) {
        data[i*4+0] = 1.0;  // U = 1（充足基底）
        data[i*4+1] = 0.0;  // V = 0（无催化剂）
        data[i*4+3] = 1.0;
    }
    // 中心 10×10 种子：V=1（触发图案生长）
    const cx = Math.floor(W/2), cy = Math.floor(H/2);
    for (let y = cy-5; y < cy+5; y++) {
        for (let x = cx-5; x < cx+5; x++) {
            data[(y*W+x)*4+1] = 1.0;
        }
    }
    const tex = new THREE.DataTexture(data, W, H, THREE.RGBAFormat, THREE.HalfFloatType);
    tex.needsUpdate = true;

    // 通过 copy pass 写入 rtA
    const copyMat = new THREE.MeshBasicMaterial({ map: tex });
    const copyMesh = new THREE.Mesh(new THREE.PlaneGeometry(2,2), copyMat);
    const tmpScene = new THREE.Scene(); tmpScene.add(copyMesh);
    renderer.setRenderTarget(rt);
    renderer.render(tmpScene, simCamera);
    renderer.setRenderTarget(null);
    copyMat.dispose(); copyMesh.geometry.dispose();
}
```
