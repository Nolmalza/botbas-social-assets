# Procedural lo-fi background loop (original, royalty-free). usage: python3 music.py out.wav seconds [seed]
import sys, wave, numpy as np
out, dur = sys.argv[1], float(sys.argv[2])
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
rng = np.random.default_rng(seed)
SR, BPM = 44100, 88
beat = 60 / BPM
n = int(SR * dur)
t = np.arange(n) / SR
mix = np.zeros(n)

def note(f):  # midi -> Hz
    return 440 * 2 ** ((f - 69) / 12)

progs = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]]  # Am7 Fmaj7 Cmaj7 G7
if seed % 2: progs = progs[1:] + progs[:1]
bar = beat * 4

def env(length, a, r):
    e = np.ones(length)
    ai, ri = int(a * SR), int(r * SR)
    e[:ai] = np.linspace(0, 1, ai); e[-ri:] = np.linspace(1, 0, ri)
    return e

# warm pad (detuned triangle-ish)
for i in range(int(dur / bar) + 1):
    s = int(i * bar * SR); L = min(int(bar * SR), n - s)
    if L <= 0: break
    tt = np.arange(L) / SR; seg = np.zeros(L)
    for m in progs[i % 4]:
        for d in (-0.08, 0.08):
            f = note(m) * 2 ** (d / 12)
            seg += (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * f * tt))
    seg *= env(L, 0.25, 0.35)[:L] * 0.035
    mix[s:s + L] += seg
    # bass root
    fb = note(progs[i % 4][0] - 12)
    mix[s:s + L] += np.sin(2 * np.pi * fb * tt) * env(L, 0.02, 0.3)[:L] * 0.10

# soft keys arpeggio (eighths)
step = beat / 2
for k in range(int(dur / step)):
    s = int(k * step * SR); L = min(int(step * 1.6 * SR), n - s)
    if L <= 0: break
    chord = progs[int(k * step / bar) % 4]
    m = chord[[0, 2, 1, 3, 2, 1, 3, 2][k % 8]] + 12
    tt = np.arange(L) / SR
    tone = np.sin(2 * np.pi * note(m) * tt) + 0.3 * np.sin(4 * np.pi * note(m) * tt)
    mix[s:s + L] += tone * np.exp(-tt * 6) * 0.05

# drums: kick 1 & 3, snare-ish 2 & 4, hats eighths
for k in range(int(dur / beat)):
    s = int(k * beat * SR)
    L = min(int(0.35 * SR), n - s)
    if L <= 0: break
    tt = np.arange(L) / SR
    if k % 2 == 0:
        f = 110 * np.exp(-tt * 25) + 45
        mix[s:s + L] += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * 0.32
    else:
        nz = rng.standard_normal(L)
        mix[s:s + L] += np.convolve(nz, np.ones(6) / 6, 'same') * np.exp(-tt * 18) * 0.07
    for h in (0, 0.5):
        hs = s + int(h * beat * SR); HL = min(int(0.05 * SR), n - hs)
        if HL > 0:
            hn = rng.standard_normal(HL); hn = hn - np.convolve(hn, np.ones(3) / 3, 'same')
            mix[hs:hs + HL] += hn * np.exp(-np.arange(HL) / SR * 80) * 0.035

# vinyl-ish noise bed + lowpass-ish smoothing
mix += np.convolve(rng.standard_normal(n), np.ones(30) / 30, 'same') * 0.004
fade = int(1.5 * SR); mix[-fade:] *= np.linspace(1, 0, fade); mix[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.8
st = np.stack([mix, np.roll(mix, int(0.012 * SR))], 1)
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
