"""Royalty-free upbeat 'explainer' music with many flavors.
Each seed picks: tempo, key, chord progression, rhythm instrument, arp pattern,
lead instrument, melody, drum kit.  make_bright(seconds, out_wav, seed) -> flavor dict"""
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
def hz(n): return 440 * 2 ** ((n - 69) / 12)
def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def _t(d): return np.arange(int(d * SR)) / SR
def _att(t, a=400): return 1 - np.exp(-t * a)

# ---------------- instruments ----------------
def marimba(f, d=0.5):
    t = _t(d); return (np.sin(2*np.pi*f*t)*np.exp(-t*9) + .25*np.sin(2*np.pi*4*f*t)*np.exp(-t*25)) * _att(t)
def kalimba(f, d=0.7):
    t = _t(d); return (np.sin(2*np.pi*f*t)*np.exp(-t*5) + .3*np.sin(2*np.pi*5.4*f*t)*np.exp(-t*30)) * _att(t, 800)
def ukulele(f, d=0.6):
    t = _t(d); saw = 2*((f*t) % 1)-1
    return lp(saw*np.exp(-t*7), min(4000, f*6)) * _att(t, 900) * 0.8
def pizz(f, d=0.35):
    t = _t(d); saw = 2*((f*t) % 1)-1
    return lp(saw*np.exp(-t*14), min(3000, f*5)) * _att(t, 600)
def epiano(f, d=0.8):
    t = _t(d); return (np.sin(2*np.pi*f*t) + .4*np.sin(2*np.pi*2*f*t)*np.exp(-t*6)) * np.exp(-t*3) * _att(t, 300) * .7
def glock(f, d=0.9):
    t = _t(d); return (np.sin(2*np.pi*f*t) + .3*np.sin(2*np.pi*2.76*f*t)*np.exp(-t*8)) * np.exp(-t*4) * _att(t)
def bell(f, d=1.0):
    t = _t(d); return (np.sin(2*np.pi*f*t) + .5*np.sin(2*np.pi*2.0*f*t)*np.exp(-t*3) + .2*np.sin(2*np.pi*3.01*f*t)*np.exp(-t*6)) * np.exp(-t*2.5) * _att(t) * .7
def whistle(f, d=0.4):
    t = _t(d); vib = 1 + 0.006*np.sin(2*np.pi*5.5*t)
    env = np.minimum(1, t/0.03) * np.exp(-np.maximum(0, t-d*0.6)*12)
    return np.sin(2*np.pi*f*np.cumsum(vib)/SR) * env * .6
def synthpluck(f, d=0.4):
    t = _t(d); sq = np.sign(np.sin(2*np.pi*f*t))
    return lp(sq*np.exp(-t*10), 2500) * _att(t, 800) * .5

RHYTHM = {"marimba": marimba, "ukulele": ukulele, "pizzicato": pizz, "kalimba": kalimba,
          "epiano": epiano, "synthpluck": synthpluck}
LEAD = {"glock": glock, "whistle": whistle, "bell": bell, "kalimba": kalimba, "marimba": marimba}

ARPS = {
    "bounce":  [(0, 0), (1, 2), (2, 1), (3, 3), (4, 2), (5, 1), (6, 3), (7, 2)],
    "updown":  [(0, 0), (1, 1), (2, 2), (3, 3), (4, 2), (5, 1), (6, 0), (7, 1)],
    "offbeat": [(1, -1), (3, -1), (5, -1), (7, -1)],          # -1 = full chord stab
    "strum":   [(0, -1), (3, -1), (4, -1), (6, -1)],
    "gallop":  [(0, 0), (1.5, 2), (2, 1), (3, 3), (4, 0), (5.5, 2), (6, 1), (7, 3)],
}
KITS = ["clap", "snap", "fourfloor", "halftime", "tambourine"]
PROGS = [[0, 7, 9, 5], [0, 5, 7, 5], [9, 5, 0, 7], [0, 9, 5, 7], [5, 7, 0, 0], [0, 4, 5, 7]]
KEYS = [0, 2, 5, 7, -3, -5, 3]   # C D F G A G(low) Eb


def flavor_from_seed(seed):
    r = np.random.default_rng(seed + 1000)
    rn = list(RHYTHM); ln = list(LEAD)
    rhythm = rn[r.integers(len(rn))]
    lead = ln[r.integers(len(ln))]
    if lead == rhythm: lead = "glock" if rhythm != "glock" else "whistle"
    arp = list(ARPS)[r.integers(len(ARPS))]
    if rhythm in ("ukulele", "epiano") and r.random() < 0.6: arp = r.choice(["strum", "offbeat"])
    return dict(seed=int(seed), bpm=int(r.integers(100, 129)), key=int(r.choice(KEYS)),
                prog=int(r.integers(len(PROGS))), rhythm=rhythm, lead=lead, arp=str(arp),
                kit=KITS[r.integers(len(KITS))])


def make_bright(T, OUT, seed=7, flavor=None):
    fl = flavor or flavor_from_seed(seed)
    rng = np.random.default_rng(seed)
    beat = 60 / fl["bpm"]; e = beat / 2; bar = beat * 4
    key = fl["key"]; prog = PROGS[fl["prog"]]
    R = RHYTHM[fl["rhythm"]]; L = LEAD[fl["lead"]]; arp = ARPS[fl["arp"]]; kit = fl["kit"]
    N = int((T + bar * 2) * SR); tr = {k: np.zeros(N) for k in ("rhy", "bass", "drm", "lead")}
    cache = {}

    def add(k, x, t):
        s = int(t * SR)
        if s < N: n = min(len(x), N - s); tr[k][s:s + n] += x[:n]
    def note(fn, n):
        k = (fn.__name__, n)
        if k not in cache: cache[k] = fn(hz(n))
        return cache[k]

    tk = _t(0.3); kick = np.sin(2*np.pi*np.cumsum(55 + 90*np.exp(-tk*35))/SR) * np.exp(-tk*9)
    tc = _t(0.18)
    clap = sum(hp(rng.normal(0, 1, len(tc)), 1500) * np.exp(-(tc-d).clip(0)*30) * (tc >= d) for d in (0, .01, .022))
    ts = _t(0.05); shk = hp(rng.normal(0, 1, len(ts)), 6000) * np.exp(-ts*70)
    tn = _t(0.08); snap = hp(rng.normal(0, 1, len(tn)), 2500) * np.exp(-tn*80) + 0.4*np.sin(2*np.pi*1800*tn)*np.exp(-tn*90)
    tt = _t(0.2); tamb = hp(rng.normal(0, 1, len(tt)), 7000) * np.exp(-tt*18) * (1 + 0.5*np.sin(2*np.pi*40*tt))
    th = _t(0.06); hat = hp(rng.normal(0, 1, len(th)), 8000) * np.exp(-th*60)
    tsn = _t(0.2); snare = hp(rng.normal(0, 1, len(tsn)), 1800)*np.exp(-tsn*20)*.7 + .3*np.sin(2*np.pi*200*tsn)*np.exp(-tsn*30)

    def bassnote(f):
        t = _t(e * 1.8); saw = 2*((f*t) % 1)-1
        return lp(saw*np.exp(-t*5), 900)*.9 + np.sin(2*np.pi*f*t)*np.exp(-t*4)
    bass_pats = [[(0, 0), (1.5, 12), (2, 7), (3.5, 0)], [(0, 0), (1, 0), (2, 7), (3, 12)],
                 [(0, 0), (0.5, 0), (2, 0), (2.5, 7), (3.5, 5)]]
    bpat = bass_pats[seed % 3]

    pent = [0, 2, 4, 7, 9, 12, 14, 16]
    motif_len = 8 if fl["lead"] != "whistle" else 6
    motif = [rng.choice(pent) if rng.random() > 0.28 else None for _ in range(motif_len)]
    answer = [None if m is None else pent[(pent.index(m) + rng.integers(-2, 3)) % len(pent)] for m in motif]

    nb = int(np.ceil(T / bar)) + 1
    lead_start = 2 if rng.random() < 0.7 else 4
    for b in range(nb):
        t0 = b * bar; deg = prog[b % 4]; root = 60 + key + deg
        minor = deg in (9, 4)
        chord = [root, root + (3 if minor else 4), root + 7, root + 12]
        for (pos, idx) in arp:
            tt0 = t0 + pos * e + (0.01 if int(pos) % 2 else 0)
            if idx < 0:
                for j, n in enumerate(chord[:3]): add("rhy", note(R, n) * 0.28, tt0 + j * 0.012)
            else:
                add("rhy", note(R, chord[idx]) * (0.5 if int(pos) % 2 == 0 else 0.34), tt0)
        if b == 0:
            for i in range(8): add("drm", shk * 0.12, t0 + i * e)
            continue
        for dt, n in bpat: add("bass", bassnote(hz(root - 24 + n)) * 0.5, t0 + dt * beat)
        # drum kits
        if kit == "clap":
            for dt in (0, 2, 3.5): add("drm", kick*.85, t0+dt*beat)
            for dt in (1, 3): add("drm", clap*.32, t0+dt*beat)
            for i in range(16): add("drm", shk*(.13 if i % 2 else .07), t0+i*beat/4)
        elif kit == "snap":
            for dt in (0, 2.5): add("drm", kick*.8, t0+dt*beat)
            for dt in (1, 3): add("drm", snap*.45, t0+dt*beat)
            for i in range(8): add("drm", shk*.1, t0+i*e+e/2)
        elif kit == "fourfloor":
            for dt in range(4): add("drm", kick*.8, t0+dt*beat)
            for dt in range(4): add("drm", hat*.22, t0+dt*beat+e)
            for dt in (1, 3): add("drm", clap*.25, t0+dt*beat)
        elif kit == "halftime":
            add("drm", kick*.9, t0); add("drm", kick*.6, t0+1.5*beat)
            add("drm", snare*.4, t0+2*beat)
            for i in range(8): add("drm", hat*(.16 if i % 2 == 0 else .09), t0+i*e)
        else:  # tambourine
            for dt in (0, 2): add("drm", kick*.8, t0+dt*beat)
            for dt in (1, 3): add("drm", tamb*.3, t0+dt*beat)
            for i in range(8): add("drm", tamb*.08, t0+i*e+e/2)
        # lead: call (motif) / answer, octave lift every 4 bars
        if b >= lead_start:
            mel = motif if (b // 2) % 2 == 0 else answer
            lift = 12 if (b // 4) % 2 and fl["lead"] != "whistle" else 0
            step = e if motif_len == 8 else e * 8 / 6
            for i, m in enumerate(mel):
                if m is None or (b % 2 and i >= motif_len - 2): continue
                add("lead", note(L, 72 + key + m + lift - (12 if lift and m > 9 else 0)) * 0.22, t0 + i * step)

    mix = lp(tr["rhy"], 5500)*.9 + lp(tr["bass"], 1200) + tr["drm"]*.75 + hp(tr["lead"], 300)
    env = np.ones(N)
    for b in range(1, nb):
        for dt in (0, 2):
            s = int((b*bar + dt*beat)*SR); Ln = int(0.18*SR)
            if s < N: seg = env[s:s+Ln]; env[s:s+Ln] = np.minimum(seg, 0.75 + 0.25*np.linspace(0, 1, Ln)[:len(seg)])
    mix = np.tanh(mix * env * 1.2)[:int(T * SR)]
    f = int(1.2 * SR); mix[-f:] *= np.linspace(1, 0, f)
    mix /= np.abs(mix).max() or 1
    sf.write(OUT, (mix * 0.9).astype(np.float32), SR)
    return fl


def pick_seed(history, avoid_last=6, rng=None):
    """Choose a seed whose (rhythm, lead, kit) differs from the recent ones, and whose
    rhythm and kit both differ from the very last clip."""
    rng = rng or np.random.default_rng()
    recent = history[-avoid_last:]
    combos = {(h["rhythm"], h["lead"], h["kit"]) for h in recent}
    last = recent[-1] if recent else None
    for _ in range(500):
        s = int(rng.integers(0, 10_000_000)); f = flavor_from_seed(s)
        if (f["rhythm"], f["lead"], f["kit"]) in combos: continue
        if last and (f["rhythm"] == last["rhythm"] or f["kit"] == last["kit"]): continue
        return s
    return int(rng.integers(0, 10_000_000))


if __name__ == "__main__":
    print(make_bright(float(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 7))
