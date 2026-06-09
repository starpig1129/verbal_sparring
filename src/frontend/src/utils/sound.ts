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

  // 1. 開始列隊 (Start matchmaking queue)
  playStartQueue() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.setValueAtTime(220, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.4)

    gain.gain.setValueAtTime(0.08, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.4)
  }

  // 2. 配對成功 (Match found)
  playMatchFound() {
    this.playTone(523.25, 'triangle', 0.25, 0.1, 0) // C5
    this.playTone(659.25, 'triangle', 0.35, 0.1, 0.1) // E5
  }

  // 3. 收到挑戰 (Match challenge)
  playMatchChallenge() {
    this.playTone(440, 'sawtooth', 0.15, 0.08, 0) // A4
    this.playTone(349.23, 'sawtooth', 0.25, 0.08, 0.12) // F4
    this.playTone(523.25, 'sawtooth', 0.45, 0.08, 0.24) // C5
  }

  // 4. 加入戰局 (Join arena)
  playJoinArena() {
    this.playTone(110, 'sine', 0.6, 0.15, 0)
    this.playTone(165, 'triangle', 0.8, 0.08, 0.02)
  }

  // 5. 發送訊息 (Send message)
  playSendMessage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.setValueAtTime(600, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(1200, ctx.currentTime + 0.08)

    gain.gain.setValueAtTime(0.06, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.08)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.08)
  }

  // 6. 收到訊息 (Receive message)
  playReceiveMessage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const osc = ctx.createOscillator()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.setValueAtTime(800, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.12)

    gain.gain.setValueAtTime(0.06, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.12)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.12)
  }

  // 7. 攻擊對手 / 造成傷害 (Deal damage)
  playDealDamage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(0.12, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.2)

    const osc = ctx.createOscillator()
    osc.type = 'sawtooth'
    osc.frequency.setValueAtTime(800, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.2)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.2)
  }

  // 8. 受到傷害 (Receive damage)
  playReceiveDamage() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(0.25, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.35)

    const osc = ctx.createOscillator()
    osc.type = 'sawtooth'
    osc.frequency.setValueAtTime(180, ctx.currentTime)
    osc.frequency.exponentialRampToValueAtTime(40, ctx.currentTime + 0.35)

    osc.connect(gain)
    gain.connect(ctx.destination)

    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.35)
  }

  // 9. 獲得勝利 (Victory)
  playVictory() {
    this.init()
    if (!this.ctx) return
    const ctx = this.ctx

    this.playTone(261.63, 'sine', 0.25, 0.06, 0) // C4
    this.playTone(329.63, 'sine', 0.25, 0.06, 0) // E4
    this.playTone(392.00, 'sine', 0.25, 0.06, 0) // G4

    this.playTone(349.23, 'sine', 0.25, 0.06, 0.2) // F4
    this.playTone(440.00, 'sine', 0.25, 0.06, 0.2) // A4
    this.playTone(523.25, 'sine', 0.25, 0.06, 0.2) // C5

    this.playTone(523.25, 'triangle', 0.6, 0.08, 0.4) // C5
    this.playTone(659.25, 'triangle', 0.6, 0.08, 0.4) // E5
    this.playTone(783.99, 'triangle', 0.6, 0.08, 0.4) // G5
    this.playTone(1046.50, 'triangle', 0.8, 0.08, 0.4) // C6
  }
}

export const sound = new SoundManager()
