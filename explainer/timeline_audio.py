"""Lay out scene/sentence timing from vo.json and mix VO + ambient pad (ducked)."""
import json, sys
import numpy as np, soundfile as sf
B = sys.argv[1]
vo = json.load(open(f"{B}/vo.json"))
SR = 24000
# scene: (duration, first VO offset, tail kept after last sentence)
PLAN = {1: (8.5, 0.9), 2: (16.5, 0.7), 3: (13.0, 0.8), 4: (11.5, 0.7), 5: (18.5, 0.9),
        6: (10.5, 0.7), 7: (13.0, 0.9), 8: (8.5, 0.8)}
TAIL = 0.9
scenes, t = [], 0.0
for sid in sorted(PLAN, key=int):
    dur, lead = PLAN[sid]
    sents = vo[str(sid)]
    speech = sum(s["dur"] for s in sents)
    n = len(sents)
    gap = 0 if n == 1 else max(0.45, (dur - lead - TAIL - speech) / (n - 1))
    dur = max(dur, lead + speech + gap * (n - 1) + TAIL)
    cur, out = lead, []
    for s in sents:
        out.append(dict(s, at=round(cur, 3)))
        cur += s["dur"] + gap
    scenes.append({"id": sid, "start": round(t, 3), "dur": round(dur, 3), "sents": out})
    t += dur
total = round(t, 3)
json.dump({"total": total, "scenes": scenes}, open(f"{B}/timeline.json", "w"), indent=1)
print("total", total, [(s["id"], s["start"], s["dur"]) for s in scenes])

# ---- voice track
N = int(total * SR) + SR
voice = np.zeros(N)
for sc in scenes:
    for s in sc["sents"]:
        a, sr = sf.read(f"{B}/{s['file']}"); assert sr == SR
        i = int((sc["start"] + s["at"]) * SR); voice[i:i + len(a)] += a
voice *= 0.95 / max(1e-6, np.abs(voice).max())

# ---- ambient pad: slow-evolving detuned chord, soft low-pass
tt = np.arange(N) / SR
rng = np.random.default_rng(7)
def note(f, amp):
    sig = np.zeros(N)
    for det in (-0.35, 0.0, 0.4):            # gentle chorus via detune
        ph = rng.uniform(0, 2 * np.pi)
        ff = f * 2 ** (det / 1200 * 10)
        sig += np.sin(2 * np.pi * ff * tt + ph) + 0.18 * np.sin(4 * np.pi * ff * tt + ph)
    return amp * sig / 3
# two alternating voicings (Dmaj9 / Bm11-ish), cross-faded every 8 s
chordA = [(73.42, .55), (146.83, .35), (220.0, .28), (277.18, .2), (329.63, .16), (440.0, .08)]
chordB = [(61.74, .55), (123.47, .35), (185.0, .28), (220.0, .2), (293.66, .16), (369.99, .08)]
A = sum(note(f, a) for f, a in chordA); Bc = sum(note(f, a) for f, a in chordB)
mixw = 0.5 - 0.5 * np.cos(2 * np.pi * tt / 16.0)
pad = A * (1 - mixw) + Bc * mixw
pad *= 0.85 + 0.15 * np.sin(2 * np.pi * tt / 5.3)      # slow swell
# one-pole low-pass for softness
alpha = np.exp(-2 * np.pi * 900 / SR)
from scipy.signal import lfilter
pad = lfilter([1 - alpha], [1, -alpha], pad)
pad /= np.abs(pad).max()

# ducking: smoothed VO envelope -> pad gain 1.0 (no voice) .. 0.45 (voice)
env = np.abs(voice)
win = int(0.25 * SR)
env = np.convolve(env, np.ones(win) / win, mode="same")
env = np.clip(env / (env.max() * 0.35), 0, 1)
att = np.exp(-1 / (0.12 * SR)); rel = np.exp(-1 / (0.6 * SR))
sm = lfilter([1 - rel], [1, -rel], env)  # smooth release
duck = 1.0 - 0.55 * np.clip(np.maximum(sm, env * 0.0), 0, 1)
fade = np.clip(tt / 2.5, 0, 1) * np.clip((total - tt) / 3.0, 0, 1)
pad_level = 10 ** (-17 / 20)   # pad sits well under the voice
mix = voice + pad * duck * fade * pad_level
mix = mix[: int(total * SR)]
mix *= 0.89 / np.abs(mix).max()
sf.write(f"{B}/mix.wav", mix.astype(np.float32), SR, subtype="PCM_16")
print("audio ok", len(mix) / SR)
