"""Royalty-free upbeat 'explainer' music: marimba + pluck bass + claps + glockenspiel.
make_bright(seconds, out_wav, seed)"""
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
def hz(n): return 440 * 2 ** ((n - 69) / 12)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)


def make_bright(T, OUT, seed=7):
    rng = np.random.default_rng(seed)
    BPM = [112, 116, 120][seed % 3]; beat = 60 / BPM; e = beat / 2; bar = beat * 4
    key = [0, 2, 5, -3][(seed // 3) % 4]                       # C, D, F, A major
    progs = [[0, 7, 9, 5], [0, 5, 7, 5], [9, 5, 0, 7], [0, 9, 5, 7]]   # I V vi IV ...
    prog = progs[(seed // 12) % 4]
    N = int((T + bar * 2) * SR); out = {k: np.zeros(N) for k in ("mar", "bass", "drm", "glk")}

    def add(k, x, t):
        s = int(t * SR)
        if s < N: n = min(len(x), N - s); out[k][s:s + n] += x[:n]

    def tone(f, dur, decay, partials):
        t = np.arange(int(dur * SR)) / SR
        x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * decay * (1 + m * 0.6)) for m, a in partials)
        return x * (1 - np.exp(-t * 400))

    mar = lambda f: tone(f, 0.5, 9, [(1, 1), (4, 0.25), (10, 0.05)])
    glk = lambda f: tone(f, 0.9, 4, [(1, 1), (2.76, 0.3), (5.4, 0.1)])
    def bass(f):
        t = np.arange(int(e * 1.8 * SR)) / SR
        saw = 2 * ((f * t) % 1) - 1
        return lp(saw * np.exp(-t * 5), 900) * 0.9 + np.sin(2 * np.pi * f * t) * np.exp(-t * 4)
    tk = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-tk * 35)) / SR) * np.exp(-tk * 9)
    tc = np.arange(int(0.18 * SR)) / SR
    clap = sum(hp(rng.normal(0, 1, len(tc)), 1500) * np.exp(-(tc - d).clip(0) * 30) * (tc >= d) for d in (0, 0.01, 0.022))
    ts = np.arange(int(0.05 * SR)) / SR
    shk = hp(rng.normal(0, 1, len(ts)), 6000) * np.exp(-ts * 70)

    # a 2-bar melody motif from major pentatonic, reused with variation
    pent = [0, 2, 4, 7, 9, 12, 14, 16]
    motif = [rng.choice(pent) if rng.random() > 0.25 else None for _ in range(8)]

    nb = int(np.ceil(T / bar)) + 1
    for b in range(nb):
        t0 = b * bar; root = 60 + key + prog[b % 4]
        minor = prog[b % 4] == 9
        chord = [root, root + (3 if minor else 4), root + 7, root + 12]
        # marimba arpeggio, 8ths, bouncy pattern
        patt = [0, 2, 1, 3, 2, 1, 3, 2]
        for i, p in enumerate(patt):
            v = 0.5 if i % 2 == 0 else 0.33
            add("mar", mar(hz(chord[p])) * v, t0 + i * e + (0.012 if i % 2 else 0))
        if b == 0:
            for i in range(8): add("drm", shk * 0.12, t0 + i * e)
            continue
        # bass: root on 1, octave pop on the and-of-2, fifth on 3
        for k, (dt, n) in enumerate([(0, 0), (1.5, 12), (2, 7), (3.5, 0)]):
            add("bass", bass(hz(root - 24 + n)) * 0.5, t0 + dt * beat)
        # drums: kick 1 & 3 (+ pickup), claps 2 & 4, shaker 16ths
        for dt in (0, 2, 3.5): add("drm", kick * 0.85, t0 + dt * beat)
        for dt in (1, 3): add("drm", clap * 0.32, t0 + dt * beat)
        for i in range(16): add("drm", shk * (0.13 if i % 2 else 0.07), t0 + i * beat / 4)
        # glockenspiel melody from bar 2, every bar, lifts every 4th bar
        if b >= 2:
            off = 12 if (b // 4) % 2 else 0
            for i, m in enumerate(motif):
                if m is None or (b % 2 and i >= 6): continue
                add("glk", glk(hz(72 + key + m + off - (12 if off and m > 9 else 0))) * 0.22, t0 + i * e)

    mix = lp(out["mar"], 5000) * 0.9 + lp(out["bass"], 1200) + out["drm"] * 0.75 + hp(out["glk"], 300)
    # gentle pump on kicks for groove
    env = np.ones(N)
    for b in range(1, nb):
        for dt in (0, 2):
            s = int((b * bar + dt * beat) * SR); L = int(0.18 * SR)
            if s < N: seg = env[s:s + L]; env[s:s + L] = np.minimum(seg, 0.75 + 0.25 * np.linspace(0, 1, L)[:len(seg)])
    mix *= env
    mix = np.tanh(mix * 1.2)[:int(T * SR)]
    f = int(1.2 * SR); mix[-f:] *= np.linspace(1, 0, f)
    mix /= np.abs(mix).max() or 1
    sf.write(OUT, (mix * 0.9).astype(np.float32), SR)
    return OUT


if __name__ == "__main__":
    make_bright(float(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 7)
