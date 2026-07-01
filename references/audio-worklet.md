# AudioWorklet + ConvolverNode — 精密音色与空间混响

> **前置依赖**：`state-machine.md`（需访问 `State.calm` 对象驱动余音长度和自发轻敲节奏）。

AudioWorklet 让声音 DSP 在独立线程运行，帧级精度（21μs @48kHz）。
ConvolverNode 用程序化生成的脉冲响应添加空间感——寺庙/山洞/深海，**零音频文件**。

**何时用 AudioWorklet**：audio-engine.md §三 的配方 A（432+216Hz 双正弦）已能覆盖 80% 场景；
AudioWorklet 的价值在于**更真实的金属泛音列 + calm 值驱动的余音长度**。

## 目录

- [一、AudioWorklet 基础架构](#一audioworklet-基础架构)
- [二、颂钵振铃处理器（HealingBellProcessor）](#二颂钵振铃处理器healingbellprocessor)
- [三、calm 值联动参数调制](#三calm-值联动参数调制)
- [四、ConvolverNode 空间混响](#四convolvernode-空间混响)
- [五、混响预设速查](#五混响预设速查)
- [六、完整集成模板](#六完整集成模板)

---

## 一、AudioWorklet 基础架构

AudioWorklet 处理器运行在独立线程，通过 `port.postMessage` 与主线程通信：

```javascript
// 主线程：注册 + 实例化（Blob URL，无需单独 .js 文件）
async function createBellWorklet(audioCtx) {
    const PROCESSOR_CODE = `/* 见 §二 */`;

    const blob = new Blob([PROCESSOR_CODE], { type: 'application/javascript' });
    const url  = URL.createObjectURL(blob);
    await audioCtx.audioWorklet.addModule(url);
    URL.revokeObjectURL(url);

    const node = new AudioWorkletNode(audioCtx, 'healing-bell', {
        numberOfInputs:  0,
        numberOfOutputs: 1,
        outputChannelCount: [2],  // 立体声
    });
    return node;
}

// 触发敲击（在状态机叙事节点调用）
function strikeWorkletBell(node, intensity = 1.0, calm = 0.5) {
    node.port.postMessage({ type: 'strike', intensity, calm });
}
```

> **Autoplay 策略**：`AudioWorkletNode` 同样受浏览器 Autoplay 限制——必须在首次用户交互后 `audioCtx.resume()` 才能发声。参考 audio-engine.md §一 的激活模式。

---

## 二、颂钵振铃处理器（HealingBellProcessor）

```javascript
// 这段代码放进 §一 的 PROCESSOR_CODE 字符串里
const PROCESSOR_CODE = `
class HealingBellProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.partials = [];
        this.autoTimer = 0;
        this.autoInterval = 6 * 48000;   // 自发敲击间隔（帧数）
        this.autoIntensity = 0.3;

        this.port.onmessage = (e) => {
            if (e.data.type === 'strike') this._strike(e.data.intensity, e.data.calm);
            if (e.data.type === 'param')  this._setParam(e.data);
        };
    }

    _strike(intensity = 1.0, calm = 0.5) {
        // 颂钵泛音列（非整数倍 = 真实金属共鸣感）
        const freqMults = [1.0, 2.756, 5.404, 8.933, 13.341];
        const ampMults  = [1.0, 0.45,  0.25,  0.12,  0.06];
        const base      = 432.0;

        this.partials = freqMults.map((m, i) => ({
            freq:      base * m,
            amp:       0.0,
            targetAmp: intensity * ampMults[i] * 0.4,
            phase:     0.0,
            // calm 越高 → 余音越悠长（6~22 秒）
            decayRate: 1.0 / ((6.0 + calm * 8.0) * (1.0 + i * 0.5) * 48000),
            detune:    (Math.random() - 0.5) * 4.0,  // ±2 cents 微失谐
        }));
    }

    _setParam({ autoInterval, autoIntensity }) {
        if (autoInterval  !== undefined) this.autoInterval  = autoInterval  * 48000;
        if (autoIntensity !== undefined) this.autoIntensity = autoIntensity;
    }

    process(inputs, outputs) {
        const out  = outputs[0];
        const len  = out[0].length;  // 通常 128 帧

        // 自发轻敲（calm 越高越频繁）
        this.autoTimer += len;
        if (this.autoTimer >= this.autoInterval) {
            this.autoTimer = 0;
            this._strike(this.autoIntensity, 0.8);
        }

        for (let i = 0; i < len; i++) {
            let sample = 0.0;
            for (const p of this.partials) {
                if (p.amp < p.targetAmp) p.amp = Math.min(p.amp + p.targetAmp / 240, p.targetAmp);
                p.amp *= (1.0 - p.decayRate);
                p.phase += ((p.freq + p.detune) / 48000) * Math.PI * 2.0;
                sample += Math.sin(p.phase) * p.amp;
            }
            out[0][i] = sample;
            if (out[1]) out[1][i] = sample * 0.97;  // 轻微相位差 = 空间感
        }
        return true;  // 保持处理器存活
    }
}
registerProcessor('healing-bell', HealingBellProcessor);
`;
```

> **为什么泛音用非整数倍**：真实金属颂钵因形状导致共鸣频率非整数比例。`[1, 2.756, 5.404...]` 来自对实测频谱的近似——比纯整数泛音更"金属"、更"有机"。

---

## 三、calm 值联动参数调制

```javascript
// 主循环每帧调用
function updateBellCalm(bellNode, calm) {
    bellNode.port.postMessage({
        type: 'param',
        autoInterval:   4.0 + calm * 8.0,    // 4~12 秒/次（calm↑ → 更频繁轻敲）
        autoIntensity:  0.15 + calm * 0.35,   // 0.15~0.5（calm↑ → 力度更轻柔）
    });
}

// 在三幕剧节点主动敲击
// 幕二开始（混沌 → 转化）：中等强度
strikeWorkletBell(bellNode, 0.8, State.calm);
// 幕三完成（达到高calm）：强烈敲击 + 混响叠加
strikeWorkletBell(bellNode, 1.3, State.calm);
```

---

## 四、ConvolverNode 空间混响

程序化生成脉冲响应（IR），无需任何音频文件：

```javascript
function createReverb(audioCtx, {
    duration  = 3.0,   // 混响时间（秒）
    decay     = 2.0,   // 衰减指数（越大尾巴越短）
    preDelay  = 0.02,  // 前延迟（0.01~0.05，造成空间距离感）
    roomType  = 'temple'
} = {}) {
    const sr  = audioCtx.sampleRate;
    const buf = audioCtx.createBuffer(2, sr * duration, sr);
    const preDelaySamples = Math.floor(preDelay * sr);

    for (let ch = 0; ch < 2; ch++) {
        const d    = buf.getChannelData(ch);
        const phaseOffset = ch * 47;  // 左右轻微相位差

        for (let i = 0; i < d.length; i++) {
            if (i < preDelaySamples) { d[i] = 0; continue; }
            const t        = (i - preDelaySamples) / sr;
            const envelope = Math.exp(-t * decay);
            d[i] = (Math.random() * 2 - 1) * envelope;

            // 房间特性
            if (roomType === 'cave'   && i < preDelaySamples + 1200) d[i] *= 2.2;
            if (roomType === 'temple' && t < 0.3) d[i] *= t / 0.3;   // 渐进涌现
        }
    }

    const conv = audioCtx.createConvolver();
    conv.buffer = buf;
    return conv;
}

// 接入音频图：干声 + 湿声并联
function addReverb(audioCtx, sourceNode, masterGain, roomType = 'temple') {
    const conv    = createReverb(audioCtx, { duration: 4.0, decay: 1.5, roomType });
    const wetGain = audioCtx.createGain();
    wetGain.gain.value = 0.35;

    sourceNode.connect(masterGain);                         // 干声
    sourceNode.connect(conv).connect(wetGain).connect(masterGain);  // 湿声
    return { conv, wetGain };
}
```

---

## 五、混响预设速查

| 预设 | duration | decay | preDelay | roomType | 适用场景 |
|------|---------|-------|---------|---------|---------|
| 寺庙（推荐） | 4.0s | 1.5 | 0.02 | temple | 颂钵 / 治愈主题 |
| 山洞 | 5.0s | 1.2 | 0.04 | cave | 压抑初始态 / 黑暗主题 |
| 深海 | 8.0s | 0.8 | 0.08 | hall | 孤独 / 极致包裹感 |
| 户外 | 2.0s | 3.0 | 0.01 | hall | 平静 / 自然轻盈 |

```javascript
// 随 calm 过渡混响（fade 处理避免切换时的喀哒声）
function transitionReverb(audioCtx, oldWetGain, sourceNode, masterGain, newRoomType, calm) {
    const t = audioCtx.currentTime;
    oldWetGain.gain.linearRampToValueAtTime(0, t + 0.8);  // 淡出旧混响
    setTimeout(() => {
        addReverb(audioCtx, sourceNode, masterGain, newRoomType);
    }, 800);
}
```

---

## 六、完整集成模板

```javascript
class HealingAudioSystem {
    async init() {
        this.ctx    = new (window.AudioContext || window.webkitAudioContext)();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0;
        this.master.connect(this.ctx.destination);

        // AudioWorklet 颂钵
        this.bell = await createBellWorklet(this.ctx);
        this.bell.connect(this.master);  // 干声

        // ConvolverNode 寺庙混响
        const { conv, wetGain } = addReverb(this.ctx, this.bell, this.master, 'temple');
        this.conv    = conv;
        this.wetGain = wetGain;
    }

    async resume() {
        if (!this.ctx) await this.init();
        if (this.ctx.state === 'suspended') await this.ctx.resume();
        const t = this.ctx.currentTime;
        this.master.gain.cancelScheduledValues(t);
        this.master.gain.setValueAtTime(this.master.gain.value, t);
        this.master.gain.linearRampToValueAtTime(0.6, t + 2.0);
    }

    // 状态机叙事节点调用
    strike(intensity = 1.0) {
        strikeWorkletBell(this.bell, intensity, State.calm);
    }

    // 主循环每帧调用
    update(calm) {
        updateBellCalm(this.bell, calm);
    }
}

const Audio = new HealingAudioSystem();
['mousedown','touchstart'].forEach(evt =>
    window.addEventListener(evt, () => Audio.resume(), { once: true, passive: true })
);
```
