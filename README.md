<a id="top"></a>

<div align="center">

<h1>Healing Space · 疗愈空间</h1>

<p><em>一个 Claude Code Skill，将用户情绪转化为指尖可触的交互式疗愈旅程——GPU 流体、WebGL 着色器、p5.js 有机渲染、Web Audio 合成，融合为一段从紧张走向平静的情绪弧线。</em></p>

<p>
  <a href="https://github.com/shasha1108/healing-space/stargazers"><img src="https://img.shields.io/github/stars/shasha1108/healing-space?style=for-the-badge&color=7C5CBF" alt="Stars"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="License"></a>
  <a href="https://github.com/shasha1108/healing-space"><img src="https://img.shields.io/badge/Claude%20Code-Skill-6C4AB6?style=for-the-badge&logo=anthropic&logoColor=white" alt="Claude Code Skill"></a>
  <a href="#"><img src="https://img.shields.io/badge/version-8.0.0-7C5CBF?style=for-the-badge" alt="v8.0.0"></a>
</p>

<p>
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-能力矩阵">能力矩阵</a> ·
  <a href="#-工作原理">工作原理</a> ·
  <a href="#-技术全景">技术全景</a> ·
  <a href="#-项目结构">项目结构</a>
</p>

</div>

---

<details open>
<summary><strong>📑 目录</strong></summary>

- [概述](#-概述)
- [快速开始](#-快速开始)
- [疗愈领域](#-疗愈领域)
- [能力矩阵](#-能力矩阵)
- [设计哲学](#-设计哲学)
- [工作原理](#-工作原理)
- [质量门禁](#-质量门禁)
- [技术全景](#-技术全景)
- [项目结构](#-项目结构)
- [相关项目](#-相关项目)
- [参与贡献](#-参与贡献)
- [许可](#-许可)

</details>

---

## 📖 概述

**healing-space** 是一个 Claude Code Skill，生成完整的独立 HTML5 页面——**用户的触摸本身就是疗愈**。

大多数"放松"网页是被动的——播一段声音、放一段循环动画，结束。它们不调动身体、不讲故事、不给用户在情绪释放中的主动权。结果是短暂的分散注意力，而非疗愈体验。

Healing Space 的解法：每个生成的作品遵循**三幕情绪弧线**——美好展示 → 突然破坏 → 亲手修复——用工业级创意编程技术实现，让用户通过指尖的交互动作（擦拭、梳理、融化、重建）完成一次完整的情绪释放。

| 能力 | 说明 |
|------|------|
| 🧠 **情绪通感映射** | 焦虑是什么质地？愤怒是什么温度？将用户情绪翻译为物理现象和视觉隐喻 |
| 🎬 **三幕剧叙事** | 美好展示（Baseline）→ 突然破坏（Disruption）→ 亲手修复（Restoration），完整的情绪旅程 |
| 🖐️ **触觉疗愈仪式** | 触摸即疗愈——擦拭 = 清洁，梳理 = 整理，融化 = 释放，拖拽 = 掌控 |
| 🌊 **GPU 流体模拟** | FBO ping-pong 流体动力学、Reaction-Diffusion 图灵图案、Physarum 粘菌网络 |
| ✨ **WebGL 着色器艺术** | GLSL 顶点/片元着色器、Raymarching SDF 液态 3D、Three.js 粒子系统 |
| 🎨 **p5.js 有机渲染** | 流场、Perlin/Simplex/Curl 噪声、curveVertex 笔触、SCREEN 混合多层叠加 |
| 🔊 **Web Audio 代码合成** | 432Hz 疗愈频率、五声音阶、棕/粉噪声、双耳节拍、AudioWorklet 空间混响 |

> **设计哲学：你不是程序员，你是用代码做心理疗愈的艺术家。** 产出的不是"一个能跑的 H5 页面"，而是"一段能用指尖触碰的情绪旅程"。

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🚀 快速开始

### 前提

- 已安装 [Claude Code](https://claude.ai/code)
- healing-space skill 已在你的 skills 目录中

### 从情绪开始

在 Claude Code 中输入你的情绪状态，healing-space 会为你生成一个完整的交互式疗愈页面：

```
/healing-space 焦虑——像心里有一团乱麻，想梳理却越缠越紧
/healing-space 疲惫——身体像灌了铅，连呼吸都觉得重
/healing-space 难过——心里有一个洞，说不清也填不满
/healing-space 愤怒——胸口有一团火，想砸东西
/healing-space 失恋——整个人被抽空了，只剩下空壳
```

### 从场景开始

```
/healing-space 做一个禅意沙庭，手指划过沙子画出同心圆
/healing-space 做一个音浴体验，声音像水一样流过身体
/healing-space 做一个星空下的冥想空间，呼吸带动星光闪烁
```

> 💡 **情绪描述越具体，生成越精准。** 不只说情绪词——描述它的质地、温度、在身体里的位置。"焦虑"不如"心里像有一团打结的毛线"来得好。

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🏞️ 疗愈领域

| 领域 | 情绪入口 | 典型隐喻 | 交互仪式 |
|------|----------|----------|----------|
| 🧘 **冥想静观** | 焦虑、浮躁、注意力涣散 | 禅意沙庭、呼吸光晕、星空凝视 | 拖拽画圆、跟随呼吸节奏 |
| 💧 **情绪释放** | 难过、压抑、说不清的沉重 | 墨水扩散→擦拭、外壳剥落→露核 | 手指擦拭、点击剥落 |
| 🫀 **身体觉察** | 疲惫、紧绷、身体与情绪断连 | 肌肉纹理→梳理、冻结→融化 | 拖拽梳理、长按融化 |
| 🔄 **认知重构** | 自我怀疑、被困住、看不到出路 | 碎片→拼合、混沌→结晶 | 拖拽拼合、点击重组 |
| 🌌 **存在反思** | 孤独、意义感缺失、与世界的疏离 | 星尘→连接、孤岛→架桥 | Physarum 网络生长、粒子连接 |

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## ✨ 能力矩阵

| | 能力 | 说明 |
|---|------|------|
| 🧠 | **情绪通感映射（Synesthesia Mapping）** | 情绪 → 物理现象：焦虑是打结的毛线团？愤怒是沸腾的岩浆？用身体经验翻译情绪 |
| 🎬 | **三幕剧结构（Three-Act Arc）** | Baseline（美好展示）→ Disruption（突然破坏）→ Restoration（亲手修复），不可变 |
| 🖐️ | **触觉疗愈仪式（Touch Rituals）** | 交互动作本身有疗愈意义：擦拭 = 清洁，梳理 = 整理，融化 = 释放，拖拽 = 掌控 |
| 🌊 | **GPU 流体模拟** | FBO ping-pong 流体动力学、Reaction-Diffusion（Gray-Scott）图灵图案、Physarum 粘菌传输网络 |
| ✨ | **WebGL 着色器艺术** | GLSL 顶点/片元着色器、Raymarching SDF 液态 3D（无网格）、Three.js InstancedMesh 万级粒子 |
| 🎨 | **p5.js 有机渲染** | 流场、Perlin/Simplex/Curl 噪声、curveVertex 笔触、SCREEN 混合多层叠加 |
| 🔊 | **Web Audio 程序化合成** | 432Hz/216Hz 正弦波疗愈频率、五声音阶、棕/粉噪声、双耳节拍、AudioWorklet 空间混响 |
| 🌫️ | **影院级体积渲染** | FogExp2 体积雾、AdditiveBlending 多层叠加丁达尔光路、Vertex Displacement 有机形变 |
| 🎯 | **Fixed/Variable 框架** | 三幕剧、Lerp 运动、432Hz 频率等硬约束不变；隐喻、色板、交互仪式每次创作决定 |
| 📦 | **12 套武器库** | 每个 reference 文件是生产级代码骨架——AI 应该修改而非重写 |

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🎭 设计哲学

### 三个思维模型（每次创作必须同时加载）

| 思维模型 | 身份 | 负责 |
|----------|------|------|
| 🧠 **心理咨询师/疗愈师** | 深谙色彩心理学、视听疗愈 | 拆解痛点本质：这个情绪在身体里是什么质地？什么温度？受众看到什么会感到被理解？ |
| 🎬 **生成艺术导演/交互设计师** | 精通美学设计、隐喻构建 | 把情绪翻译成什么物理现象？画面从哪一幕开始？交互动作在现实中对应什么？ |
| ⚙️ **创意编程专家** | 精通 Three.js、WebGL、Shader、p5.js、Web Audio | 隐喻 → 数学公式 → 代码。流体、噪声、缓动、包络是颜料，API 是画笔 |

### 优先级本质

| 你在优化什么 | 实际价值 |
|-------------|---------|
| 这个交互动作本身有没有疗愈意义 | 前 20%——擦拭=清洁，梳理=整理，融化=释放 |
| 这个故事是不是一段完整的情绪旅程 | 前 30%——好隐喻 + 烂叙事 = 用户还是不懂 |
| 隐喻本身对不对 | 前 50%——隐喻错了全盘皆输 |
| 粒子参数（刚度/阻尼/颜色）| 最后 10%——有用，但不是现在 |

> **当效果不好时，不要改参数。先问三个问题：隐喻对了吗？技术路线对了吗？人物找对了吗？三个对了再调参数。**

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## ⚙️ 工作原理

### 创作管线

```
STEP 1              STEP 2              STEP 3              STEP 4              STEP 5
情绪解析            通感映射            三幕剧设计           技术选型            交互设计
────────→          ────────→          ────────→          ────────→          ────────→
用户情绪词          情绪→物理现象        Baseline →          从12套武器库中      擦拭/梳理/
受众画像            质地/温度/颜色      Disruption →         选择技术路线        融化/拖拽/
                   视觉隐喻            Restoration         匹配代码骨架        拼合/连接

STEP 6              STEP 7
代码生成            质量检查
────────→          ────────→
从golden example    14项检查清单
骨架出发            全部 ✅ 才交付
融合选定技术
```

### 不变项 vs 可变项

**不可变（Fixed · 每次照做）：**

| 不变项 | 规则 |
|--------|------|
| 三幕剧结构 | 美好展示 → 突然破坏 → 亲手修复，永远不变 |
| 光标 | 自定义视觉锚点 + Lerp 跟随 + `cursor: none` |
| 运动质感 | Lerp 缓动，禁用线性赋值 |
| 音效频率 | 432Hz/216Hz 正弦波，gain ≤ 0.08，禁用 55Hz 持续低频 |
| 入场动画 | Dolly Zoom 或 Orbit + 分层错开入场 |
| 质量检查 | 全部 14 项 ✅ 才交付 |

**可变（Variable · 每次创作决定）：**

| 可变项 | 范围 |
|--------|------|
| 隐喻 | 墨水扩散→擦拭？外壳剥落→露核？沙子梳理→同心圆？|
| 物理过程 | 流体？粒子？CSS？Raymarching？p5.js？|
| 情绪词 + 受众 | 焦虑/疲惫/难过/愤怒/失恋 + 为谁而做 |
| 音效包络 | 底噪类型 / 治愈音色 / 高潮触发时机 |
| 色板 | 从 5 个情绪色板中选 1 个——不是颜色规则，是人格方向 |
| 字体系 | 宋体（默认）/ 等宽（机械感）/ 手写（脆弱）/ 粗衬线（力量） |

### 四大维度执行法则

1. **创意编程 — 影院级渲染**：FogExp2 体积雾、AdditiveBlending 丁达尔光路、Vertex Displacement 有机形变——空气有厚度
2. **交互设计 — 仪式感**：交互映射到真实疗愈动作（擦拭、梳理、融化），而非"点击按钮"——每一次触摸都有心理意义
3. **音效设计 — 情绪温度**：432Hz/216Hz 正弦波温暖基底、噪声颜色匹配情绪（棕=安定/粉=柔和）——声音是情绪的质地
4. **叙事设计 — 完整旅程**：入场 Dolly Zoom → 三幕情绪弧线 → 结束时画面回归平静——用户经历了"一件事"

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🔬 质量门禁

14 项检查清单，全部通过才交付：

| # | 检查项 | 类别 |
|---|--------|------|
| 1 | 元数据头完整（Title / Summary / Tech / Keywords / Render / Audio / Touch / Repo） | 结构 |
| 2 | 三幕剧结构完整（Baseline → Disruption → Restoration） | 叙事 |
| 3 | 自定义光标 + Lerp 跟随 + `cursor: none` + 初始 opacity:0 | 交互 |
| 4 | 运动全部使用 Lerp 缓动，无线性赋值 | 运动 |
| 5 | 音效 432Hz/216Hz 正弦波，gain ≤ 0.08，无 55Hz 持续低频 | 音频 |
| 6 | 入场动画：Dolly Zoom 或 Orbit + 分层错开 | 视觉 |
| 7 | FogExp2 体积雾（Three.js 场景）或画布透明度叠加（p5.js 场景） | 渲染 |
| 8 | 交互有即时视觉 + 听觉反馈 | 交互 |
| 9 | 移动端 touch 不触发默认页面滚动 | 移动端 |
| 10 | AudioContext 在首次交互后恢复 | 音频 |
| 11 | 色板匹配情绪人格，无暗黑模式、无高饱和原色 | 色彩 |
| 12 | 文案每阶段 1-2 句，不说教、不开处方 | 文案 |
| 13 | 单文件 HTML，CDN 只载 p5.js / Three.js，其余全部内联 | 结构 |
| 14 | 14 项全部 ✅ | 交付 |

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🛠️ 技术全景

<div align="center">

| 领域 | 技术 | 参考文件 |
|------|------|----------|
| 🎨 **3D 渲染** | Three.js、WebGL 2.0、GLSL 着色器、InstancedMesh、FogExp2 | `shader-patterns.md` |
| 🌊 **GPU 模拟** | FBO 流体、Reaction-Diffusion、Physarum、Raymarching SDF、WebGPU Compute | `gpu-fluid.md`、`reaction-diffusion.md`、`physarum.md`、`raymarching.md`、`tsl-webgpu.md` |
| 🖌️ **2D 有机** | p5.js 流场、Perlin/Simplex/Curl 噪声、curveVertex、SCREEN 混合 | `p5-patterns.md` |
| 🔊 **音频合成** | Web Audio API、432Hz 疗愈频率、五声音阶、AudioWorklet 空间混响 | `audio-engine.md`、`audio-worklet.md` |
| 🎯 **CSS 动画** | CSS Transform、GSAP Timeline、backdrop-filter 毛玻璃、DOM 错开过渡 | `css-aesthetic.md` |
| 🖐️ **交互模式** | 触摸拖拽/擦拭、长按安抚、手势恢复、Lerp 跟随光标 | `state-machine.md` |

</div>

### 技术覆盖矩阵

| 能力 | p5.js | Three.js | WebGL | Web Audio | CSS/GSAP | WebGPU |
|------|-------|----------|-------|-----------|----------|--------|
| 粒子系统 | ✅ | ✅ | ✅ | — | — | ✅ |
| 流体模拟 | — | ✅ | ✅ | — | — | ✅ |
| Reaction-Diffusion | — | ✅ | ✅ | — | — | ✅ |
| Physarum 网络 | — | ✅ | ✅ | — | — | ✅ |
| Raymarching SDF | — | ✅ | ✅ | — | — | ✅ |
| 流场 | ✅ | — | — | — | — | — |
| 有机曲线 | ✅ | — | — | — | — | — |
| 程序化音频 | — | — | — | ✅ | — | — |
| 空间混响 | — | — | — | ✅ | — | — |
| DOM 动画 | — | — | — | — | ✅ | — |
| 触摸交互 | ✅ | ✅ | ✅ | — | ✅ | — |

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 📁 项目结构

```
healing-space/
├── SKILL.md                          # 完整 skill 定义（v8.0.0，硬上限 510 行）
├── README.md                         # ← 你在看这里
├── CLAUDE.md                         # Git 工作流 + 多设备防冲突规范
├── LICENSE                           # MIT
├── .gitignore
│
├── references/                       # 技术武器库（生产级代码骨架）
│   ├── causal-field.md               # calm 总线：单一真相源 + 全参数映射表
│   ├── state-machine.md              # 情感弧线状态机 + 交互模式
│   ├── adversarial-review.md         # 对抗式检查 SOP + 第一性原理决策链
│   ├── visual-validation.md          # 7 步视觉验证协议（运行时正确性）
│   ├── seeded-reproducibility.md     # 确定性种子系统（mulberry32 PRNG）
│   ├── code-snippets.md              # 通用代码骨架（光标/字体/入场/Lerp/路径流）
│   ├── color-palettes.md             # 5 套情绪色板（人格 + 色值 + 适用场景）
│   ├── shader-patterns.md            # WebGL/GLSL 发光粒子渲染
│   ├── particle-physics.md           # 粒子运动方程（刚度/阻尼/Curl Noise）
│   ├── gpu-fluid.md                  # FBO ping-pong 流体模拟
│   ├── p5-patterns.md                # p5.js 有机曲线、流场、笔触
│   ├── reaction-diffusion.md         # Gray-Scott 图灵图案（焦虑→结晶）
│   ├── physarum.md                   # 粘菌传输网络（孤独→连接）
│   ├── raymarching.md                # SDF 液态 3D + 禁用区（Body Horror 防御）
│   ├── ocean-waves.md                # Gerstner 波水面（vertex displacement）
│   ├── underwater-post.md            # 水下后处理（Beer-Lambert 体积吸收）
│   ├── wind-system.md                # 四组分风模型（阵风/碎浪/微风/颤振）
│   ├── clipmap-lod.md                # Clipmap 无限平面 LOD（飞越/滑翔）
│   ├── css-aesthetic.md              # CSS/GSAP 非 WebGL 疗愈美学
│   ├── audio-engine.md               # Web Audio API 程序化合成（432Hz 五声音阶）
│   ├── audio-worklet.md              # AudioWorklet 精密音色 + ConvolverNode 混响
│   └── tsl-webgpu.md                 # WebGPU Compute Shader + TSL 着色语言
│
├── scripts/                          # 验证工具
│   └── validate.py                   # 输出质量自动检测（光标/字体/音频/过渡）
│
└── evals/                            # 评估配置
    ├── evals.json                     # 3 个 E2E 生成用例（预期输出标准）
    └── trigger_evals.json             # 20 个触发条件测试（正例 + 负例）
```

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🔗 相关项目

| 仓库 | 做什么 |
|------|--------|
| [**healing-visual-lab**](https://github.com/shasha1108/healing-visual-lab) | 交互式数字疗愈作品集——15 件 Three.js / WebGL 交互实验 |
| [**pixel-bloom**](https://github.com/shasha1108/pixel-bloom) | 像素艺术 × 毛玻璃美学——赛博养宠、电子水族箱、像素盆栽 |
| [**inner-voice**](https://github.com/shasha1108/inner-voice) | 小红书情绪内容创作——隐喻挖掘、场景写作、视觉叙事 |
| [**h5-publish-skill**](https://github.com/shasha1108/h5-publish-skill) | 一键发布 H5 到 GitHub Pages——拖入文件夹即上线 |

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>

---

## 🤝 参与贡献

1. 🍴 **Fork** 本仓库
2. 🌿 **创建分支**（`feature/你的想法`）
3. ✍️ **提交**清晰的 commit message
4. 📤 **Push** 并打开 **Pull Request**

**特别欢迎以下方向的贡献：**
- 新的技术武器库（WebGPU、Rust/WASM 方向）
- 音效合成新配方
- 色板体系扩展

> 本仓库使用的 Git 工作流规范见 [CLAUDE.md](CLAUDE.md)。

---

## 📄 许可

MIT © 2026 [@shasha1108](https://github.com/shasha1108) —— 详见 [LICENSE](LICENSE)。

<br>

<div align="center">

<sub>用指尖触碰情绪，让每一次交互都成为疗愈。 Touch-driven healing — where every gesture transforms tension into peace.</sub>

</div>

<p align="right"><sub><a href="#top">↑ 回到顶部</a></sub></p>
