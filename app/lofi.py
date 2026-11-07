"""Royalty-free lofi generator. make_lofi(seconds, out_wav, seed)"""
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100

def make_lofi(T, OUT, seed=7):
  rng = np.random.default_rng(seed)
  BPM = 78; beat = 60 / BPM; bar = beat * 4
  N = int((T + bar) * SR)
  def hz(n): return 440 * 2 ** ((n - 69) / 12)
  def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
  def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
  def add(buf, x, t):
      s = int(t * SR)
      if s >= len(buf): return
      e = min(len(buf), s + len(x)); buf[s:e] += x[:e - s]

  # chord progressions (jazzy 7ths), picked by seed
  progs = [
      [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]],   # Fmaj7 Em7 Dm7 Cmaj7
      [[57, 60, 64, 67], [50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59]],   # Am7 Dm7 G7 Cmaj7
      [[50, 53, 57, 60], [55, 59, 62, 65], [48, 52, 55, 59], [57, 60, 64, 67]],   # ii V I vi
  ]
  prog = progs[seed % len(progs)]

  def rhodes(f, dur):
      t = np.arange(int(dur * SR)) / SR
      env = np.exp(-t * 1.6) * (1 - np.exp(-t * 60))
      x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4) + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t * 6)
      x *= 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)            # tremolo
      return x * env

  def kick():
      t = np.arange(int(0.45 * SR)) / SR
      f = 50 + 70 * np.exp(-t * 30)
      return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)

  def snare():
      t = np.arange(int(0.3 * SR)) / SR
      n = hp(rng.normal(0, 1, len(t)), 1200) * np.exp(-t * 18)
      return lp(n, 5000) * 0.6 + 0.3 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)

  def hat():
      t = np.arange(int(0.08 * SR)) / SR
      return hp(rng.normal(0, 1, len(t)), 7000) * np.exp(-t * 60)

  keys = np.zeros(N); bass = np.zeros(N); drums = np.zeros(N)
  K, S, Hh = kick(), snare(), hat()
  nbars = int(np.ceil(T / bar)) + 1
  for b in range(nbars):
      t0 = b * bar; ch = prog[b % 4]
      # keys: chord strum on 1, light re-hit on the "and" of 3
      for i, n in enumerate(ch):
          jitter = i * 0.018 + rng.uniform(0, 0.01)
          add(keys, rhodes(hz(n), bar * 1.1) * 0.22, t0 + jitter)
          add(keys, rhodes(hz(n + 12), beat * 1.5) * 0.06, t0 + beat * 2.5 + jitter)
      # bass
      tb = np.arange(int(bar * SR)) / SR
      bn = np.sin(2 * np.pi * hz(ch[0] - 12) * tb) * np.exp(-tb * 0.9) * (1 - np.exp(-tb * 80))
      add(bass, bn * 0.45, t0)
      # drums (boom-bap with swing); start from bar 1 for a soft intro
      if b >= 1:
          sw = beat / 2 * 0.62
          for k in (0, 2.5): add(drums, K * 0.9, t0 + k * beat)
          for k in (1, 3): add(drums, S * 0.5, t0 + k * beat + 0.012)
          for k in range(4):
              add(drums, Hh * 0.18, t0 + k * beat)
              add(drums, Hh * 0.11, t0 + k * beat + sw)

  keys = lp(keys, 2600)
  drums = lp(drums, 6000)
  mix = keys + lp(bass, 400) + drums * 0.8
  # sidechain-ish pump from kick
  pump = np.ones(N)
  for b in range(1, nbars):
      for k in (0, 2.5):
          s = int((b * bar + k * beat) * SR); L = int(0.25 * SR)
          if s < N: pump[s:s + L] = np.minimum(pump[s:s + L], (0.65 + 0.35 * np.linspace(0, 1, L))[:len(pump[s:s + L])])
  mix *= pump
  # vinyl crackle + hiss
  crackle = np.zeros(N); idx = rng.integers(0, N, int(T * 25)); crackle[idx] = rng.uniform(-1, 1, len(idx))
  crackle = hp(lp(crackle, 4000), 800) * 0.5
  mix += crackle + hp(rng.normal(0, 0.006, N), 2000)
  # wow/flutter via tiny resample warp
  t = np.arange(N); warp = t + 18 * np.sin(2 * np.pi * 0.4 * t / SR)
  mix = np.interp(warp, t, mix)
  mix = np.tanh(mix * 1.4)   # tape saturation
  mix = mix[:int(T * SR)]
  f = int(1.5 * SR); mix[-f:] *= np.linspace(1, 0, f)
  mix /= np.abs(mix).max(); sf.write(OUT, (mix * 0.9).astype(np.float32), SR)
  return OUT

if __name__ == "__main__":
    make_lofi(float(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 7)
