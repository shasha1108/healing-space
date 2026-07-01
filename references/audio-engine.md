# Audio Engine — Web Audio 纯代码合成武器库

本文件是声音合成的真实可复用代码。**所有声音都用 Web Audio API 现场合成，零音频文件。** 照着改，不要从零发明。

设计原则：声音的物理量（频率、滤波、音量）必须能被**外部参数实时驱动**——这就是"视听联觉"的实现机制。

## 目录

- [一、音频上下文与 Autoplay 策略](#一音频上下文与-autoplay-策略)
- [二、白噪音 / 粉噪音](#二白噪音--粉噪音海浪风声雨声的基底)
- [三、颂钵 / 钟声](#三颂钵--钟声治愈系核心音色)（配方 A 432+216Hz [✓] / 配方 B 非整数泛音）
- [四、Drone：两种用法](#四drone两种相反的用法治愈底-vs-焦虑心跳)（A 焦虑心跳 [✓] / B 治愈底）
- [五、LFO 调制](#五lfo-调制呼吸感波动感)
- [六、双耳节拍](#六双耳节拍binaural-beats促发脑波)
- [七、完整引擎封装](#七完整的治愈系音频引擎封装验证版直接用) [✓]
- [速查：情绪 → 音色映射](#速查情绪--音色映射含验证配方)

> `[✓]` = 经 archetype 发布验证的配方，优先使用。

---

## 一、音频上下文与 Autoplay 策略

浏览器禁止页面加载就播放声音，**必须**在用户首次交互后 `resume()`：

```javascript
let audioCtx = null;
let masterGain = null;

function initAudio() {
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    masterGain = audioCtx.createGain();
    masterGain.gain.value = 0.0;        // 起始静音，避免爆音
    masterGain.connect(audioCtx.destination);
}

// 在首次 click / mousedown / touchstart 时调用
function resumeAudio() {
    if (!audioCtx) initAudio();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    // 淡入总音量，避免突兀
    masterGain.gain.cancelScheduledValues(audioCtx.currentTime);
    masterGain.gain.setValueAtTime(masterGain.gain.value, audioCtx.currentTime);
    masterGain.gain.linearRampToValueAtTime(0.6, audioCtx.currentTime + 2.0);
}

window.addEventListener('mousedown', resumeAudio, { once: false });
window.addEventListener('touchstart', resumeAudio, { once: false });
```

> **关键**：`masterGain.gain.value` 起始设 0，再 `linearRampToValueAtTime` 淡入。直接设成满音量会"砰"一声爆音。

---

## 二、白噪音 / 粉噪音（海浪、风声、雨声的基底）

Web Audio 没有内置噪音源，要用 `AudioBuffer` 自己生成一段再循环播放：

```javascript
function createNoiseBuffer(type = 'white') {
    // type: 'white' | 'pink' | 'brown'
    const bufferSize = audioCtx.sampleRate * 2;   // 2 秒循环
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);

    if (type === 'white') {
        for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1;
    } else if (type === 'pink') {
        // Paul Kellet 经典粉噪算法
        let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;
        for (let i = 0; i < bufferSize; i++) {
            const w = Math.random() * 2 - 1;
            b0 = 0.99886*b0 + w*0.0555179;
            b1 = 0.99332*b1 + w*0.0750759;
            b2 = 0.96900*b2 + w*0.1538520;
            b3 = 0.86650*b3 + w*0.3104856;
            b4 = 0.55000*b4 + w*0.5329522;
            b5 = -0.7616*b5 - w*0.0168980;
            data[i] = (b0+b1+b2+b3+b4+b5+b6+w*0.5362) * 0.11;
            b6 = w * 0.115926;
        }
    } else { // brown
        let last = 0;
        for (let i = 0; i < bufferSize; i++) {
            const w = Math.random() * 2 - 1;
            last = (last + 0.02 * w) / 1.02;
            data[i] = last * 3.5;
        }
    }
    return buffer;
}
```

**三种噪音的听感**：
- **白噪音**：刺耳、像电视雪花。慎用，除非做"尖锐焦虑"。
- **粉噪音**：像雨声、海浪、瀑布。**最常用**，治愈系基底首选。
- **棕噪音**：低沉轰鸣、像远雷、深海。适合"压抑、深渊"氛围。

把噪音接到一个**低通滤波器**就能变成风声、海浪：

```javascript
function createWindLayer() {
    const src = audioCtx.createBufferSource();
    src.buffer = createNoiseBuffer('pink');
    src.loop = true;

    const filter = audioCtx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 400;     // 滤掉高频 → 柔和的风
    filter.Q.value = 1;

    const gain = audioCtx.createGain();
    gain.gain.value = 0.15;

    src.connect(filter); filter.connect(gain); gain.connect(masterGain);
    src.start();

    return { filter, gain, src };   // 返回引用，以便交互时改 frequency / gain
}
```

---

## 三、颂钵 / 钟声（治愈系核心音色）

颂钵是治愈系网页的"灵魂音色"。有两种配方，**优先用简单的那种**——它已被 archetype《释·茧》实战验证有效：

### 配方 A（推荐，已验证）：432Hz + 216Hz 双八度纯正弦波

出乎意料地简单：两个纯正弦波，一个是基频 432Hz，一个是低八度 216Hz，初始静音，被敲击时快速起音 + 指数衰减。空灵感来自**衰减时长**（8s/12s），不来自复杂泛音：

```javascript
function createBowl() {
    const b1 = audioCtx.createOscillator(); b1.type = 'sine'; b1.frequency.value = 432;
    const b2 = audioCtx.createOscillator(); b2.type = 'sine'; b2.frequency.value = 216; // 低八度，更厚重
    const g1 = audioCtx.createGain(); g1.gain.value = 0;   // 初始静音，等被敲
    const g2 = audioCtx.createGain(); g2.gain.value = 0;
    b1.connect(g1).connect(masterGain);
    b2.connect(g2).connect(masterGain);
    b1.start(); b2.start();
    return { g1, g2 };
}

// 敲击：快速起音 + 指数衰减。intensity 0~1.5 控制力度
function strikeBowl(bowl, intensity) {
    const now = audioCtx.currentTime;
    bowl.g1.gain.cancelScheduledValues(now);
    bowl.g2.gain.cancelScheduledValues(now);
    bowl.g1.gain.setValueAtTime(bowl.g1.gain.value, now);
    bowl.g2.gain.setValueAtTime(bowl.g2.gain.value, now);
    // 起音：20ms 内冲到峰值
    bowl.g1.gain.linearRampToValueAtTime(0.5 * intensity, now + 0.05);
    bowl.g2.gain.linearRampToValueAtTime(0.35 * intensity, now + 0.1);
    // 指数衰减：泛音悠长（这就是"余音绕梁"的来源）
    bowl.g1.gain.exponentialRampToValueAtTime(0.0001, now + 8.0);
    bowl.g2.gain.exponentialRampToValueAtTime(0.0001, now + 12.0);
}
```

> **敲击时机很关键**（archetype 验证）：不要匀速敲。卡在叙事节点上——达成治愈瞬间强敲 `strikeBowl(bowl, 1.2)`；4-7-8 呼吸的吸气开始敲 `0.8`、呼气开始敲 `0.4`。颂钵成为呼吸/转化的"节拍器"。

### 配方 B（更逼真但更重）：非整数倍泛音叠加

如果想要更接近真实金属颂钵的泛音列，可以用非整数倍泛音。但**这个配方未被 archetype 采用**，理论值，酌情用：

```javascript
function createSingingBowl(baseFreq = 220) {
    // 颂钵的泛音不是整数倍，而是 1, 2.76, 5.4, 8.93 这种近似倍数
    const partials = [1, 2.76, 5.4, 8.93];
    const gains    = [1.0, 0.5, 0.25, 0.12];

    const oscs = [];
    const gain = audioCtx.createGain();
    gain.gain.value = 0;

    partials.forEach((mult, i) => {
        const osc = audioCtx.createOscillator();
        osc.type = 'sine';
        osc.frequency.value = baseFreq * mult;
        // 微微失谐，增加"活"的感觉
        osc.detune.value = (Math.random() - 0.5) * 8;

        const og = audioCtx.createGain();
        og.gain.value = gains[i] * 0.2;
        osc.connect(og); og.connect(gain);
        osc.start();
        oscs.push(osc);
    });

    gain.connect(masterGain);
    return { oscs, gain, baseFreq };
}

// 敲击一次（音量快速起、缓慢落）
function strikeBowl(bowl) {
    const t = audioCtx.currentTime;
    bowl.gain.gain.cancelScheduledValues(t);
    bowl.gain.gain.setValueAtTime(0, t);
    bowl.gain.gain.linearRampToValueAtTime(0.5, t + 0.02);   // 起音 20ms
    bowl.gain.gain.exponentialRampToValueAtTime(0.001, t + 6.0);  // 6 秒衰减
}
```

> **为什么用 `exponentialRampToValueAtTime` 衰减**：指数衰减听起来像真实的金属共鸣（开始快、尾巴长）。线性衰减会很"电子"。

---

## 四、Drone：两种相反的用法（治愈底 vs 焦虑心跳）

Drone（持续低音）在治愈网页里有两个**截然相反**的用途，千万别搞混：

### 用法 A：焦虑心跳（压抑阶段的核心音源，archetype 验证）

这是 archetype《释·茧》压抑阶段的灵魂音色——**锯齿波 45Hz，低通滤波到 150Hz**，产生一种胸口压迫感的低频轰鸣。听起来像焦虑时的心跳/耳鸣。它必须**随治愈进度衰减**：

```javascript
function createAnxietyDrone() {
    const osc = audioCtx.createOscillator();
    osc.type = 'sawtooth';            // 锯齿波，含丰富谐波 → 不安感
    osc.frequency.value = 45;         // 极低频，胸腔共振
    const filter = audioCtx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 150;     // 砍掉高频，只留闷响
    const gain = audioCtx.createGain();
    gain.gain.value = 0.4;            // 初始就响，因为初始就是压抑态
    osc.connect(filter).connect(gain).connect(masterGain);
    osc.start();
    return { gain };
}

// 每帧：随 calm 0→1，焦虑音量从 0.4 → 0
function updateAnxietyDrone(drone, calm) {
    drone.gain.setTargetAtTime(0.4 * (1.0 - calm), audioCtx.currentTime, 0.1);
}
```

> 这个配方是整个压抑阶段的"情绪地基"。没有它，初始态会显得太安静、太治愈，失去弧线张力。

### 用法 B：治愈底（冥想氛围，治愈阶段才浮现）

一个长持续的低频**正弦**波（不是锯齿），给治愈态托底。与用法 A 相反——它**随治愈进度升起**：

```javascript
function createHealingDrone(freq = 110) {
    const osc1 = audioCtx.createOscillator();
    osc1.type = 'sine';               // 正弦，纯净
    osc1.frequency.value = freq;
    const osc2 = audioCtx.createOscillator();
    osc2.type = 'sine';
    osc2.frequency.value = freq * 1.5;   // 完全五度，和谐
    const gain = audioCtx.createGain();
    gain.gain.value = 0;              // 初始静音，治愈态才升
    osc1.connect(gain); osc2.connect(gain); gain.connect(masterGain);
    osc1.start(); osc2.start();
    return { gain };
}
```

> **两种 drone 同时存在**：A 随 calm 衰减、B 随 calm 升起，一进一退，就是"焦虑被治愈取代"在声音上的具象化。这是视听联觉在结构层的体现。

---

## 五、LFO 调制（呼吸感、波动感）

低频振荡器（LFO）用一个低频（0.1~2Hz）信号去**调制**另一个参数，产生"呼吸"般的起伏：

```javascript
// 让某个 gainNode 按 4-7-8 呼吸节奏起伏
function attachBreathLFO(targetParam, periodSec = 11.0) {
    // periodSec=11 对应 4s 吸 + 7s 屏 + ... 简化版用周期即可
    const lfo = audioCtx.createOscillator();
    lfo.type = 'sine';
    lfo.frequency.value = 1 / periodSec;   // 一个完整呼吸周期

    const lfoGain = audioCtx.createGain();
    lfoGain.gain.value = 0.15;             // 调制深度

    lfo.connect(lfoGain);
    lfoGain.connect(targetParam);          // 连到 gainNode.gain（AudioParam）
    lfo.start();

    return { lfo, lfoGain };
}
```

> **核心技巧**：LFO 连到任何 `AudioParam`（`.gain.value`、`.frequency.value`、`.Q.value`）都能产生调制。把 LFO 接到颂钵频率上 → 音高微微晃动，像真钵被风吹；接到滤波器截止频率上 → 滤波器周期性开合，像潮汐。

---

## 六、双耳节拍（Binaural Beats，促发脑波）

左耳一个频率、右耳一个略不同的频率，大脑会"听到"两者的差频，对应不同脑波状态：

```javascript
function createBinauralBeat(baseFreq = 200, beatFreq = 8) {
    // beatFreq: 4-7=Theta(冥想) 8-12=Alpha(放松) 这两个最适合治愈
    const left = audioCtx.createOscillator();
    left.frequency.value = baseFreq;
    const right = audioCtx.createOscillator();
    right.frequency.value = baseFreq + beatFreq;

    const merger = audioCtx.createChannelMerger(2);
    const lg = audioCtx.createGain(); lg.gain.value = 0.1;
    const rg = audioCtx.createGain(); rg.gain.value = 0.1;

    left.connect(lg);  lg.connect(merger, 0, 0);
    right.connect(rg); rg.connect(merger, 0, 1);
    merger.connect(masterGain);
    left.start(); right.start();

    return { left, right, lg, rg };
}
```

> **必须戴耳机**才有双耳节拍效果，单扬声器无效。提示文案里要写一句"建议佩戴耳机"。

---

## 七、完整的治愈系音频引擎封装（验证版，直接用）

下面这个引擎融合了 archetype《释·茧》验证过的所有配方：焦虑心跳 drone + 双八度颂钵 + 棕噪海浪 + 4-7-8 呼吸联动。对外暴露 `update(calm, breathe)` 供主循环每帧调用，`strikeBowl(intensity)` 供状态机在叙事节点调用：

```javascript
const Audio = {
    ctx: null, master: null,
    drone: null,                    // 焦虑心跳（随 calm 衰减）
    noiseFilter: null, noiseGain: null,  // 海浪（随 calm 升起 + 呼吸开合）
    bowlGain: null, bowlGain2: null,     // 颂钵 432/216（被 strikeBowl 触发）
    inited: false,

    init() {
        if (this.inited) return;
        this.inited = true;
        this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        this.master = this.ctx.createGain();
        this.master.gain.value = 0;            // 起始静音，resume 时淡入
        this.master.connect(this.ctx.destination);

        // (1) 焦虑心跳：锯齿 45Hz 低通 150Hz
        const dOsc = this.ctx.createOscillator();
        dOsc.type = 'sawtooth'; dOsc.frequency.value = 45;
        const dFilter = this.ctx.createBiquadFilter();
        dFilter.type = 'lowpass'; dFilter.frequency.value = 150;
        const dGain = this.ctx.createGain(); dGain.gain.value = 0.4;
        dOsc.connect(dFilter).connect(dGain).connect(this.master);
        dOsc.start();
        this.drone = { gain: dGain };

        // (2) 颂钵：432Hz + 216Hz，初始静音
        const b1 = this.ctx.createOscillator(); b1.type='sine'; b1.frequency.value = 432;
        this.bowlGain = this.ctx.createGain(); this.bowlGain.gain.value = 0;
        b1.connect(this.bowlGain).connect(this.master); b1.start();
        const b2 = this.ctx.createOscillator(); b2.type='sine'; b2.frequency.value = 216;
        this.bowlGain2 = this.ctx.createGain(); this.bowlGain2.gain.value = 0;
        b2.connect(this.bowlGain2).connect(this.master); b2.start();

        // (3) 海浪底噪：棕噪 + 低通
        const buf = this._brownNoise();
        const nSrc = this.ctx.createBufferSource(); nSrc.buffer = buf; nSrc.loop = true;
        this.noiseFilter = this.ctx.createBiquadFilter();
        this.noiseFilter.type = 'lowpass'; this.noiseFilter.frequency.value = 100;
        this.noiseGain = this.ctx.createGain(); this.noiseGain.gain.value = 0;
        nSrc.connect(this.noiseFilter).connect(this.noiseGain).connect(this.master);
        nSrc.start();
    },

    resume() {
        this.init();
        if (this.ctx.state === 'suspended') this.ctx.resume();
        const t = this.ctx.currentTime;
        this.master.gain.cancelScheduledValues(t);
        this.master.gain.setValueAtTime(this.master.gain.value, t);
        this.master.gain.linearRampToValueAtTime(0.55, t + 2.5);   // 2.5s 淡入，避免爆音
    },

    // 颂钵敲击：快速起音 + 指数衰减。intensity 0.4~1.5
    strikeBowl(intensity) {
        if (!this.ctx) return;
        const now = this.ctx.currentTime;
        this.bowlGain.gain.cancelScheduledValues(now);
        this.bowlGain2.gain.cancelScheduledValues(now);
        this.bowlGain.gain.setValueAtTime(this.bowlGain.gain.value, now);
        this.bowlGain2.gain.setValueAtTime(this.bowlGain2.gain.value, now);
        this.bowlGain.gain.linearRampToValueAtTime(0.5 * intensity, now + 0.05);
        this.bowlGain2.gain.linearRampToValueAtTime(0.35 * intensity, now + 0.1);
        this.bowlGain.gain.exponentialRampToValueAtTime(0.0001, now + 8.0);
        this.bowlGain2.gain.exponentialRampToValueAtTime(0.0001, now + 12.0);
    },

    // 每帧调用。calm 0→1, breathe 0~1（来自 4-7-8 计算）
    update(calm, breathe) {
        if (!this.ctx) return;
        const t = this.ctx.currentTime;
        // 焦虑心跳衰减
        this.drone.gain.setTargetAtTime(0.4 * (1.0 - calm), t, 0.1);
        // 海浪：治愈才浮现，振幅+滤波器跟随呼吸开合
        this.noiseGain.gain.setTargetAtTime((0.05 + breathe * 0.25) * calm, t, 0.1);
        this.noiseFilter.frequency.setTargetAtTime(100 + calm * (150 + breathe * 350), t, 0.1);
    },

    _brownNoise() {
        const size = this.ctx.sampleRate * 2;
        const buf = this.ctx.createBuffer(1, size, this.ctx.sampleRate);
        const d = buf.getChannelData(0);
        let last = 0;
        for (let i = 0; i < size; i++) {
            const w = Math.random() * 2 - 1;
            last = (last + 0.02 * w) / 1.02;
            d[i] = last * 3.5;
        }
        return buf;
    }
};

// 首次交互激活音频（遵守 Autoplay 策略）
window.addEventListener('mousedown', () => { Audio.resume(); });
window.addEventListener('touchstart', () => { Audio.resume(); }, { passive: true });
```

> 接到状态机后，主循环只需两句：`Audio.update(State.calm, breathe)` 每帧；`Audio.strikeBowl(1.2)` 在治愈达成/呼吸转换点。

---

## 速查：情绪 → 音色映射（含验证配方）

| 情绪/阶段 | 噪音 | 主音色 | 验证状态 |
|----------|------|--------|---------|
| 焦虑/压抑（初始） | — | **锯齿 45Hz 低通 150Hz**（焦虑心跳） | ✅ archetype 验证 |
| 平静/治愈（终态） | **棕噪低通，跟随呼吸** | **颂钵 432+216Hz 双八度** | ✅ archetype 验证 |
| 愤怒/焦躁变体 | 白噪+棕噪 | 失真锯齿波，高通 800Hz | 理论配方 |
| 悲伤/沉重 | 棕噪 | 低频正弦 drone，低通 300Hz | 理论配方 |
| 专注/心流 | 几乎无 | 双耳节拍 8Hz | 理论配方 |

调参核心（视听联觉在音频侧）：**`calm` 0→1 时，焦虑 drone 衰减、治愈层升起、噪音滤波器跟随呼吸开合、颂钵在叙事节点敲击**。优先用标 ✅ 的配方，它们跑通过。

---

## 八、和弦环境垫（Ambient Chord Pad）

用多个正弦波组成一个和弦，持续发声，给治愈态提供一个"暖色声音地毯"。Fmaj7（F 大七）已验证效果最好——明亮但不刺耳、温暖但不浑浊：

```javascript
function createChordPad() {
    // Fmaj7 = F3 + A3 + C4 + E4
    const freqs = [261.63, 329.63, 392.00, 493.88];
    const padGain = audioCtx.createGain();
    padGain.gain.value = 0;  // 初始静音，随 calm 升起

    freqs.forEach(f => {
        const osc = audioCtx.createOscillator();
        osc.type = 'sine';
        osc.frequency.value = f;
        // 微失谐：每个音微微偏离 1~2Hz，产生自然的"拍频"厚度
        osc.detune.value = (Math.random() - 0.5) * 4;
        const g = audioCtx.createGain();
        g.gain.value = 0.08;  // 每个音很轻
        osc.connect(g).connect(padGain);
        osc.start();
    });

    padGain.connect(masterGain);
    return { gain: padGain };
}

// 主循环：和弦随 calm 淡入（治愈态才听得见）
function updateChordPad(pad, calm) {
    pad.gain.setTargetAtTime(calm * 0.25, audioCtx.currentTime, 0.5);
}
```

> **和弦选择**：Fmaj7 适合"释怀/温暖/平静"；Am7 (A3-C4-E4-G4) 适合"略带忧伤但温柔"；Cmaj7 (C4-E4-G4-B4) 适合"明亮/希望"。

---

## 九、滴答声合成（Tick/Tock）

短促的振荡器脉冲，用于时钟类主题或呼吸节拍器：

```javascript
function createTick(audioCtx, masterGain) {
    const osc = audioCtx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = 1000;  // 默认高频清脆
    const gain = audioCtx.createGain();
    gain.gain.value = 0;
    osc.connect(gain).connect(masterGain);
    osc.start();
    return { osc, gain };
}

function playTick(tick, isHeavy = false, speedMultiplier = 1) {
    const now = audioCtx.currentTime;
    const freq = isHeavy ? 700 : 1000 + speedMultiplier * 20;
    tick.osc.frequency.setValueAtTime(freq, now);
    tick.gain.gain.cancelScheduledValues(now);
    tick.gain.gain.setValueAtTime(0, now);
    // 50ms 脉冲：5ms 起音 + 45ms 指数衰减
    tick.gain.gain.linearRampToValueAtTime(isHeavy ? 0.3 : 0.15, now + 0.005);
    tick.gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.05);
}

// 每秒调用一次（在 requestAnimationFrame 中检查秒数变化）
let lastSecond = -1;
function loop() {
    const sec = Math.floor(performance.now() / 1000);
    if (sec !== lastSecond) {
        lastSecond = sec;
        playTick(tick, sec % 2 === 0);  // 偶数秒重拍、奇数秒轻拍
    }
}
```

---

## 十、手指速度驱动滤波器

将手指滑动速度映射到音频参数，让"抚摸"或"快速划过"产生不同声音反馈：

```javascript
let prevMouse = { x: 0, y: 0 };
let currentSpeed = 0;

function updateFingerSpeed(e) {
    const dx = e.clientX - prevMouse.x;
    const dy = e.clientY - prevMouse.y;
    currentSpeed = Math.min(Math.sqrt(dx*dx + dy*dy) * 0.02, 1.0);
    prevMouse = { x: e.clientX, y: e.clientY };
}

// 主循环：速度驱动滤波器截止频率
function updateAudioBySpeed(filterNode, speed) {
    const targetFreq = 80 + speed * 800;  // 慢=低频闷响，快=高频开扬
    filterNode.frequency.setTargetAtTime(targetFreq, audioCtx.currentTime, 0.05);
}
```

> 这个模式让"猛划"产生高频嘶嘶声（焦虑感），"轻抚"产生低频闷响（安静感），和画面的"斥力大小"自然绑定。

---

## 速查新增：和弦/节拍/速度映射

| 技法 | 适用场景 | 关键参数 |
|------|---------|---------|
| Fmaj7 和弦垫 | 温暖治愈终态 | `[261.63, 329.63, 392.00, 493.88]` |
| 滴答声合成 | 时钟/节拍器/呼吸计数 | 50ms 脉冲，`exponentialRampToValueAtTime` |
| 手指速度→滤波器 | 抚摸/刮擦/拖拽交互 | `targetFreq = 80 + speed * 800` |

---

## 十一、五声音阶动态声场（声音本身在讲故事）

单频率背景音 = 配乐。音阶系统 + 双态过渡 = 声音叙事。

### 432Hz 大调五声音阶（极其和谐治愈）

```javascript
const pentatonic = [432, 485, 544, 648, 727, 864]; // 432×1, 432×9/8, 432×5/4...
let noteIdx = 0;

function playPulse() {
    const f = pentatonic[noteIdx % pentatonic.length];
    noteIdx += floor(random(2)) + 1; // 随机走1~2步——有方向但不机械

    const osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = f;
    const gain = ctx.createGain(); gain.gain.value = 0;
    osc.connect(gain).connect(master); osc.start(t); osc.stop(t + 6);

    // 水滴入深潭：0.1s 起音 + 4.5s 指数衰减
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.12, t + 0.1);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 4.5);
}
```

> 每次 `playPulse()` 走音阶的下一个位置——连续按压时声音在"向上走"，本身就是一段旋律叙事。

### 双态声场：治愈底色 vs 紧张压迫

```javascript
// 治愈底色：108Hz + 216Hz 八度叠加，低通 350Hz → 深海般的包裹感
[108, 216].forEach(f => {
    const osc = ctx.createOscillator(); osc.type = 'sine'; osc.frequency.value = f;
    osc.connect(padFilter); osc.start();
});

// 紧张压迫：55Hz + 58Hz 三角波 → 3Hz 差频 = 微弱的"不安跳动"，代表边界被侵入
// ⚠️ 此处用双频差拍（非单频 drone）——SKILL.md 禁的是 55Hz 单频持续正弦波，双频差拍不产生稳态闷响
[55, 58].forEach(f => {
    const osc = ctx.createOscillator(); osc.type = 'triangle'; osc.frequency.value = f;
    osc.connect(tensionFilter); osc.start();
});

// 动态过渡：被侵入时 tensionGain 升起，被安抚时 tensionGain 消退
function updateDynamic(isInvading, sootheForce) {
    let tensionTarget = isInvading ? max(0, 0.4 - sootheForce * 0.5) : 0;
    tensionGain.gain.setTargetAtTime(tensionTarget, ctx.currentTime, 1.0);
    let padTarget = 0.3 + sootheForce * 0.3; // 安抚越强，底色越亮
    padGain.gain.setTargetAtTime(padTarget, ctx.currentTime, 0.5);
}
```

> 关键：**两种声场同时存在、此消彼长**——这就是"焦虑被治愈取代"在声音上的具象化。不是切换，是过渡。

---

## 十二、AudioWorklet 颂钵处理器 → audio-worklet.md

AudioWorklet 在独立线程运行 DSP，帧级精度（21μs @48kHz）——适合需要真实金属泛音列和精密余音控制的场景。

> **快速决策**：§三 配方 A（432+216Hz 双正弦）已覆盖 80% 场景，简单且经 archetype 验证。需要非整数泛音列 + calm 驱动余音长度 + 自发轻敲时，使用完整版：
> → **audio-worklet.md §一~§三**（基础架构 + HealingBellProcessor + calm 联动）

---

## 十三、ConvolverNode 空间混响 → audio-worklet.md

程序化生成脉冲响应（IR），零音频文件。为颂钵等声源添加寺庙/山洞/深海的空间包裹感。

> → **audio-worklet.md §四~§五**（完整 IR 生成 + 4 种房间预设 + `transitionReverb` calm 过渡）

---

## 速查新增：AudioWorklet + 空间混响

> 代码骨架已迁至 **audio-worklet.md**。以下为技法速查，完整实现见对应章节。

| 技法 | 适用场景 | 关键参数 | 见 |
|------|---------|---------|-----|
| AudioWorklet 颂钵 | 高质量余音 + 真实金属泛音感 | 泛音比 `[1, 2.756, 5.404, 8.933]`，余音 6~22s | audio-worklet.md §二 |
| ConvolverNode 寺庙 | 颂钵 / 治愈主题混响 | `duration:4.0, decay:1.5, roomType:'temple'` | audio-worklet.md §四~§五 |
| ConvolverNode 山洞 | 压抑初始态增加压迫感 | `duration:5.0, decay:1.2, roomType:'cave'` | audio-worklet.md §五 |
| calm 过渡混响 | 压抑→治愈 空间感渐变 | `transitionReverb()` | audio-worklet.md §四 |
