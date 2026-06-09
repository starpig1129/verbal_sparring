// src/frontend/src/utils/sound.ts

class SoundManager {
  private ctx: AudioContext | null = null

  private init() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume()
    }
  }

  // Generate a buffer of white noise for slashes, drops, and impacts
  private createNoiseBuffer(): AudioBuffer {
    this.init()
    const sampleRate = this.ctx!.sampleRate
    const bufferSize = sampleRate * 1.5 // 1.5 seconds of noise
    const noiseBuffer = this.ctx!.createBuffer(1, bufferSize, sampleRate)
    const output = noiseBuffer.getChannelData(0)
    for (let i = 0; i < bufferSize; i++) {
      output[i] = Math.random() * 2 - 1
    }
    return noiseBuffer
  }

  private playTone(freq: number, type: OscillatorType, duration: number, volume: number = 0.1, delay: number = 0) {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = type
    osc.frequency.setValueAtTime(freq, ctx.currentTime + delay)

    gain.gain.setValueAtTime(volume, ctx.currentTime + delay)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + delay + duration)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime + delay)
    osc.stop(ctx.currentTime + delay + duration)
  }

  // 1. 開始列隊 (Start matchmaking) - Sci-Fi Sonar scan with echo
  playStartQueue() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const playPing = (delay: number) => {
      const time = ctx.currentTime + delay
      const osc1 = ctx.createOscillator()
      const osc2 = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc1.type = 'sine'
      osc1.frequency.setValueAtTime(523.25, time) // C5
      osc2.type = 'triangle'
      osc2.frequency.setValueAtTime(783.99, time) // G5

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(1500, time)
      filter.frequency.exponentialRampToValueAtTime(200, time + 0.35)

      gain.gain.setValueAtTime(0.08, time)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.35)

      // Delay Node for Echo
      const delayNode = ctx.createDelay()
      delayNode.delayTime.setValueAtTime(0.12, time)
      const delayGain = ctx.createGain()
      delayGain.gain.setValueAtTime(0.3, time)

      osc1.connect(filter)
      osc2.connect(filter)
      filter.connect(gain)

      gain.connect(ctx.destination)
      gain.connect(delayNode)
      delayNode.connect(delayGain)
      delayGain.connect(ctx.destination)
      delayGain.connect(delayNode) // Feedback loop

      osc1.start(time)
      osc2.start(time)
      osc1.stop(time + 0.4)
      osc2.stop(time + 0.4)
    }

    playPing(0)
  }

  // 2. 配對成功 (Match found) - Glistening Cmaj7 arpeggio chime
  playMatchFound() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const freqs = [523.25, 659.25, 783.99, 987.77] // C5, E5, G5, B5 (Cmaj7)
    freqs.forEach((freq, index) => {
      const delay = index * 0.05 // fast roll arpeggio
      const time = ctx.currentTime + delay

      const osc = ctx.createOscillator()
      const subOsc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = 'triangle'
      osc.frequency.setValueAtTime(freq, time)

      subOsc.type = 'sine'
      subOsc.frequency.setValueAtTime(freq / 2, time) // sub octave warmth

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(2000, time)
      filter.frequency.exponentialRampToValueAtTime(500, time + 0.4)

      gain.gain.setValueAtTime(0.06, time)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.45)

      osc.connect(filter)
      subOsc.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.start(time)
      subOsc.start(time)
      osc.stop(time + 0.5)
      subOsc.stop(time + 0.5)
    })
  }

  // 3. 收到挑戰 (Match challenge) - Sword draw & warning chimes
  playMatchChallenge() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // 1. Sword friction (metallic swish) using noise
    const noise = ctx.createBufferSource()
    noise.buffer = this.createNoiseBuffer()
    const noiseFilter = ctx.createBiquadFilter()
    noiseFilter.type = 'bandpass'
    noiseFilter.frequency.setValueAtTime(800, time)
    noiseFilter.frequency.exponentialRampToValueAtTime(3000, time + 0.25)
    const noiseGain = ctx.createGain()
    noiseGain.gain.setValueAtTime(0.12, time)
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.25)

    noise.connect(noiseFilter)
    noiseFilter.connect(noiseGain)
    noiseGain.connect(ctx.destination)
    noise.start(time)
    noise.stop(time + 0.3)

    // 2. Dramatic warning notes
    const playWarning = (freq: number, startDelay: number, dur: number) => {
      const osc = ctx.createOscillator()
      const oscDetune = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(freq, time + startDelay)
      oscDetune.type = 'sawtooth'
      oscDetune.frequency.setValueAtTime(freq + 4, time + startDelay)

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(400, time + startDelay)
      filter.frequency.exponentialRampToValueAtTime(1000, time + startDelay + dur * 0.3)
      filter.frequency.exponentialRampToValueAtTime(200, time + startDelay + dur)

      gain.gain.setValueAtTime(0.05, time + startDelay)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + startDelay + dur)

      osc.connect(filter)
      oscDetune.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.start(time + startDelay)
      oscDetune.start(time + startDelay)
      osc.stop(time + startDelay + dur)
      oscDetune.stop(time + startDelay + dur)
    }

    playWarning(220, 0.1, 0.25) // A3
    playWarning(293.66, 0.2, 0.35) // D4
  }

  // 4. 加入戰局 (Join arena) - Deep cinematic sub-drop & gong swell
  playJoinArena() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // Low sub-bass drop
    const sub = ctx.createOscillator()
    const subGain = ctx.createGain()
    sub.type = 'sine'
    sub.frequency.setValueAtTime(100, time)
    sub.frequency.exponentialRampToValueAtTime(35, time + 0.6)
    subGain.gain.setValueAtTime(0.25, time)
    subGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.6)
    sub.connect(subGain)
    subGain.connect(ctx.destination)
    sub.start(time)
    sub.stop(time + 0.6)

    // Warm chord swell (G-Major gong vibe)
    const freqs = [196.00, 293.66, 392.00, 493.88] // G3, D4, G4, B4
    freqs.forEach(freq => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(freq, time)

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(200, time)
      filter.frequency.exponentialRampToValueAtTime(1200, time + 0.2)
      filter.frequency.exponentialRampToValueAtTime(150, time + 0.7)

      gain.gain.setValueAtTime(0.06, time)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.7)

      osc.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.start(time)
      osc.stop(time + 0.7)
    })
  }

  // 5. 發送訊息 (Send message) - Clean high-tech click & air pop
  playSendMessage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // High click chime
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(1200, time)
    osc.frequency.exponentialRampToValueAtTime(300, time + 0.05)

    gain.gain.setValueAtTime(0.05, time)
    gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.05)

    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start(time)
    osc.stop(time + 0.05)

    // Highpass noise tick
    const noise = ctx.createBufferSource()
    noise.buffer = this.createNoiseBuffer()
    const filter = ctx.createBiquadFilter()
    filter.type = 'highpass'
    filter.frequency.setValueAtTime(4000, time)
    const noiseGain = ctx.createGain()
    noiseGain.gain.setValueAtTime(0.03, time)
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.03)

    noise.connect(filter)
    filter.connect(noiseGain)
    noiseGain.connect(ctx.destination)
    noise.start(time)
    noise.stop(time + 0.03)
  }

  // 6. 收到訊息 (Receive message) - Elegant UI notification chime
  playReceiveMessage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    const playBeep = (freq: number, delay: number) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, time + delay)

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(1000, time + delay)

      gain.gain.setValueAtTime(0.06, time + delay)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + delay + 0.2)

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      osc.start(time + delay);
      osc.stop(time + delay + 0.2);
    }

    playBeep(880, 0) // A5
    playBeep(987.77, 0.06) // B5
  }

  // 7. 攻擊對手 / 造成傷害 (Deal damage) - Realistic metal sword slash
  playDealDamage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // 1. Noise Slash
    const noise = ctx.createBufferSource()
    noise.buffer = this.createNoiseBuffer()
    const filter = ctx.createBiquadFilter()
    filter.type = 'bandpass'
    filter.Q.setValueAtTime(4, time)
    filter.frequency.setValueAtTime(3000, time)
    filter.frequency.exponentialRampToValueAtTime(400, time + 0.2)

    const noiseGain = ctx.createGain()
    noiseGain.gain.setValueAtTime(0.18, time)
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.25)

    noise.connect(filter)
    filter.connect(noiseGain)
    noiseGain.connect(ctx.destination)
    noise.start(time)
    noise.stop(time + 0.25)

    // 2. High-pitch sword clang
    const playClang = (freq: number, detuneVal: number) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'triangle'
      osc.frequency.setValueAtTime(freq, time)
      osc.detune.setValueAtTime(detuneVal, time)

      gain.gain.setValueAtTime(0.08, time)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.22)

      osc.connect(gain)
      gain.connect(ctx.destination)

      osc.start(time)
      osc.stop(time + 0.25)
    }

    playClang(1046.50, 0)   // C6
    playClang(1046.50, 15)  // Detuned C6
    playClang(1318.51, -10) // E6
  }

  // 8. 受到傷害 (Receive damage) - Heavy cinematic rumble impact
  playReceiveDamage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // 1. Heavy low-frequency explosion rumble
    const noise = ctx.createBufferSource()
    noise.buffer = this.createNoiseBuffer()
    const noiseFilter = ctx.createBiquadFilter()
    noiseFilter.type = 'lowpass'
    noiseFilter.frequency.setValueAtTime(350, time)
    noiseFilter.frequency.exponentialRampToValueAtTime(20, time + 0.35)

    const noiseGain = ctx.createGain()
    noiseGain.gain.setValueAtTime(0.35, time)
    noiseGain.gain.exponentialRampToValueAtTime(0.0001, time + 0.4)

    noise.connect(noiseFilter)
    noiseFilter.connect(noiseGain)
    noiseGain.connect(ctx.destination)
    noise.start(time)
    noise.stop(time + 0.4)

    // 2. Detuned sub-impact oscillators
    const playSub = (freq: number) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc.type = 'sawtooth'
      osc.frequency.setValueAtTime(120, time)
      osc.frequency.exponentialRampToValueAtTime(30, time + 0.3)

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(150, time)

      gain.gain.setValueAtTime(0.2, time)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + 0.3)

      osc.connect(filter)
      filter.connect(gain)
      gain.connect(ctx.destination)

      osc.start(time)
      osc.stop(time + 0.3)
    }

    playSub(120)
    playSub(125)
  }

  // 9. 獲得勝利 (Victory) - Cinema brassy fanfare with cathedral reverb echo
  playVictory() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx
    const time = ctx.currentTime

    // Arpeggiated C-Major cinematic fanfare chord
    const notes = [
      { f: 261.63, d: 0 },    // C4
      { f: 392.00, d: 0.05 },  // G4
      { f: 523.25, d: 0.1 },   // C5
      { f: 659.25, d: 0.15 },  // E5
      { f: 783.99, d: 0.2 },   // G5
      { f: 1046.50, d: 0.25 }  // C6
    ]

    notes.forEach(note => {
      const osc1 = ctx.createOscillator()
      const osc2 = ctx.createOscillator()
      const gain = ctx.createGain()
      const filter = ctx.createBiquadFilter()

      osc1.type = 'sawtooth'
      osc1.frequency.setValueAtTime(note.f, time + note.d)

      osc2.type = 'triangle'
      osc2.frequency.setValueAtTime(note.f + 2, time + note.d) // detune

      filter.type = 'lowpass'
      filter.frequency.setValueAtTime(300, time + note.d)
      filter.frequency.exponentialRampToValueAtTime(2000, time + note.d + 0.25)
      filter.frequency.exponentialRampToValueAtTime(400, time + note.d + 0.7)

      gain.gain.setValueAtTime(0.05, time + note.d)
      gain.gain.exponentialRampToValueAtTime(0.0001, time + note.d + 0.85)

      // Delay Node for spacious cathedral reverb effect
      const delayNode = ctx.createDelay()
      delayNode.delayTime.setValueAtTime(0.18, time + note.d)
      const delayGain = ctx.createGain()
      delayGain.gain.setValueAtTime(0.25, time + note.d)

      osc1.connect(filter)
      osc2.connect(filter)
      filter.connect(gain)

      gain.connect(ctx.destination)
      gain.connect(delayNode)
      delayNode.connect(delayGain)
      delayGain.connect(ctx.destination)
      delayGain.connect(delayNode) // Feedback loop

      osc1.start(time + note.d)
      osc2.start(time + note.d)
      osc1.stop(time + note.d + 0.9)
      osc2.stop(time + note.d + 0.9)
    })
  }
}

export const sound = new SoundManager()
