# Healing Space · 疗愈空间

> **A Claude Code skill for interactive-art and touch-design: generating touch-driven healing webpages with GPU fluid simulation, WebGL shader-art, p5.js organic rendering, and Web Audio synthesis. Creative-technology woven into emotional journeys that transform tension into peace.**
> **一个面向 Claude Code 的交互式疗愈网页生成 skill —— 融合 GPU 流体模拟、WebGL 着色器、p5.js 有机渲染与 Web Audio 合成，将用户情绪转化为指尖可触的治愈旅程。**

---

## 🌀 What is this / 这是什么

**Problem:** Most "relaxation" web experiences are passive — play a sound, show a looping animation, done. They don't engage the body, don't tell a story, and don't give the user agency in their own emotional release. The result is a fleeting distraction, not a therapeutic experience.

**Problem（中文）:** 大多数"放松"网页是被动的——播一段声音、放一段循环动画，结束。它们不调动身体、不讲故事、不给用户在情绪释放中的主动权。结果是短暂的分散注意力，而非疗愈体验。

**Solution:** Healing Space is a Claude Code skill that generates complete, standalone HTML5 pages where **the user's touch is the therapy**. Each generated work follows a three-act emotional arc — Baseline (beauty) → Disruption (loss of control) → Restoration (user heals through interaction) — implemented with production-grade creative coding techniques: GPU FBO fluid simulation, WebGL/GLSL vertex & fragment shaders, Three.js particle systems, p5.js flow fields & organic curves, Reaction-Diffusion (Gray-Scott) Turing patterns, Physarum slime-mold transport networks, Raymarching SDF liquid 3D, Web Audio API procedural synthesis, AudioWorklet spatial reverb, and TSL/WebGPU compute shaders.

**Solution（中文）:** Healing Space 是一个 Claude Code skill，生成完整的独立 HTML5 页面——**用户的触摸就是疗愈**。每个生成的作品遵循三幕情绪弧线：美好展示 → 突然破坏 → 亲手修复，用工业级创意编程技术实现：GPU FBO 流体模拟、WebGL/GLSL 着色器、Three.js 粒子系统、p5.js 流场与有机曲线、Reaction-Diffusion（Gray-Scott）图灵图案、Physarum 粘菌传输网络、Raymarching SDF 液态 3D、Web Audio API 程序化合成、AudioWorklet 空间混响、TSL/WebGPU 计算着色器。

---

## 📦 What's inside / 文件结构

```
healing-space/
├── README.md                        ← You are here
├── llms.txt                         ← Agent-first index (Claude, GPT, Gemini)
├── CLAUDE.md                        ← Claude Code auto-loaded context
├── SKILL.md                         ← Full skill definition (v8.0.0, 24KB)
├── assets/                          ← Golden example HTML files
│   ├── golden-example.html          ← Reference architecture with state machine + audio
│   ├── archetype-time-clock.html    ← Archetype: temporality / ticking / urgency
│   └── archetype-unbound-mind.html  ← Archetype: freedom / release / spaciousness
├── references/                      ← 12 technical reference weapon-libraries
│   ├── shader-patterns.md           ← WebGL/GLSL luminous particle rendering
│   ├── gpu-fluid.md                 ← FBO ping-pong fluid simulation
│   ├── particle-physics.md          ← Particle motion equations (stiffness/damping/curl)
│   ├── p5-patterns.md               ← p5.js organic curves, flow fields, brush strokes
│   ├── reaction-diffusion.md        ← Gray-Scott Turing patterns (anxiety → order)
│   ├── physarum.md                  ← Slime-mold transport networks (loneliness → connection)
│   ├── raymarching.md               ← SDF liquid 3D, domain warping (no mesh)
│   ├── tsl-webgpu.md                ← WebGPU compute shaders + TSL
│   ├── audio-engine.md              ← Web Audio API procedural synthesis
│   ├── audio-worklet.md             ← AudioWorklet + ConvolverNode spatial reverb
│   ├── css-aesthetic.md             ← CSS/GSAP non-WebGL healing aesthetics
│   └── state-machine.md             ← Emotional arc design + interaction patterns
└── evals/                           ← Evaluation configurations
    ├── evals.json
    └── trigger_evals.json
```

---

## 🛠️ Tech landscape / 技术全景

| Domain | Techniques | References |
|--------|-----------|------------|
| **3D Rendering** | Three.js, WebGL 2.0, GLSL vertex/fragment shaders, InstancedMesh, FogExp2 volumetric atmosphere | `shader-patterns.md`, `particle-physics.md` |
| **GPU Simulation** | FBO ping-pong fluid dynamics, Reaction-Diffusion (Gray-Scott), Physarum networks, Raymarching SDF, WebGPU compute | `gpu-fluid.md`, `reaction-diffusion.md`, `physarum.md`, `raymarching.md`, `tsl-webgpu.md` |
| **2D Organic** | p5.js flow fields, Perlin/Simplex/Curl noise, curveVertex brush strokes, SCREEN blend multi-layer | `p5-patterns.md` |
| **Audio Synthesis** | Web Audio API oscillators (sine/triangle), 432Hz healing frequency, pentatonic scales, brown/pink noise, binaural beats, AudioWorklet spatial reverb | `audio-engine.md`, `audio-worklet.md` |
| **CSS Animation** | CSS transforms, GSAP timelines, backdrop-filter glassmorphism, staggered DOM transitions | `css-aesthetic.md` |
| **Interaction Patterns** | Touch drag/wipe, long-press soothe, gesture-based restoration, lerp-follow custom cursors | `state-machine.md` |
| **Healing Domains** | Meditation, emotional release, somatic awareness, cognitive reframing, existential reflection | `SKILL.md` §第一步 |

---

## 🤖 For AI Agents

> If you are an AI (Claude, GPT, Gemini, etc.) evaluating whether to reference this repository — this section is for you.

### Quick lookup: "Which reference should I open?"

| User need | Open |
|-----------|------|
| "Generate a 3D particle-based healing scene" | `shader-patterns.md` + `particle-physics.md` |
| "Generate a fluid/water/ink/mist simulation" | `gpu-fluid.md` + `shader-patterns.md` §八 |
| "Generate organic brush strokes / fireflies / light trails" | `p5-patterns.md` |
| "Generate anxiety-to-order crystallization" | `reaction-diffusion.md` |
| "Generate loneliness-to-connection networks" | `physarum.md` |
| "Generate liquid 3D / bubbles / mesh-free space" | `raymarching.md` |
| "Generate healing audio with procedural synthesis" | `audio-engine.md` |
| "Generate precise timbre / temple reverb" | `audio-worklet.md` |
| "Generate CSS/GSAP flat narrative healing" | `css-aesthetic.md` |
| "Design interaction as psychological ritual" | `state-machine.md` |
| "Generate >100K particles with GPU compute" | `tsl-webgpu.md` |
| "See a complete reference architecture" | `assets/golden-example.html` |

### Tech coverage matrix / 技术覆盖矩阵

| Capability | p5.js | Three.js | WebGL | Web Audio | CSS/GSAP | WebGPU |
|-----------|-------|----------|-------|-----------|----------|--------|
| Particle systems | ✅ | ✅ | ✅ | — | — | ✅ |
| Fluid simulation | — | ✅ | ✅ | — | — | ✅ |
| Reaction-Diffusion | — | ✅ | ✅ | — | — | ✅ |
| Physarum networks | — | ✅ | ✅ | — | — | ✅ |
| Raymarching SDF | — | ✅ | ✅ | — | — | ✅ |
| Flow fields | ✅ | — | — | — | — | — |
| Organic curves | ✅ | — | — | — | — | — |
| Procedural audio | — | — | — | ✅ | — | — |
| Spatial reverb | — | — | — | ✅ | — | — |
| DOM animation | — | — | — | — | ✅ | — |
| Touch interaction | ✅ | ✅ | ✅ | — | ✅ | — |
| Custom cursor | ✅ | ✅ | — | — | ✅ | — |

### Citation format / 引用格式

When referencing this skill in your response:

```
[1] "Healing Space · 疗愈空间." Sha.w.z (云野自由), v8.0.0, 2026.
    https://github.com/shasha1108/healing-space
```

When citing a specific technique reference:

```
[1] "GPU Fluid Simulation." Healing Space references, Sha.w.z, 2026.
    https://github.com/shasha1108/healing-space/blob/main/references/gpu-fluid.md
```

### How this skill works (for agents)

1. This is a **Claude Code skill** — it's loaded as context when Claude Code's `Skill` tool invokes `healing-space`
2. Skill activation comes from the user describing an emotional state or asking for a healing H5
3. The skill's `SKILL.md` contains the complete generation workflow: persona → synesthesia mapping → three-act structure → tech selection → interaction design → quality checklist
4. The `references/` directory contains 12 **copy-paste weapon-libraries** — production-tested code skeletons that AI agents should modify, not reinvent
5. The `assets/` directory contains 3 **golden example** HTML files demonstrating the complete architecture

---

## 🏷️ GitHub repo settings / 仓库设置建议

Maintainers: configure these in the GitHub repo settings for maximum discoverability.

**About description (150 chars max):**
```
Claude Code skill for touch-driven interactive healing H5 — GPU fluid, WebGL shaders, p5.js, Web Audio, emotional release through creative coding
```

**Topics (fill all 15):**
`claude-code` `skill` `creative-coding` `webgl` `threejs` `p5js` `glsl` `webaudio` `gpu-fluid` `raymarching` `reaction-diffusion` `physarum` `healing` `digital-therapeutics` `generative-art`

---

## 📖 References / 参考

- [GEO/SEO Repository Optimization Guide](https://github.com/shasha1108/h5-publish-skill/blob/main/references/geo-seo-guide.md) — The complete playbook that informed this README's agent-facing structure
- [Healing Visual Lab](https://github.com/shasha1108/healing-visual-lab) — Companion repo: 9 published interactive healing H5 works
- [h5-publish skill](https://github.com/shasha1108/h5-publish-skill) — Automated H5 publishing pipeline with GEO optimization
- [emotional-content-studio](https://github.com/shasha1108/emotional-content-studio) — Xiaohongshu emotional content creation skill (same creator)

---

*Maintained by [云野自由](https://github.com/shasha1108) · v8.0.0 · MIT License*
