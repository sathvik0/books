"""Generate the voiceover with Kokoro (af_heart) and emit per-sentence timings."""
import json, re, sys
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

MODEL_DIR = sys.argv[1]
OUT = sys.argv[2]
SPEED = 1.12
k = Kokoro(f"{MODEL_DIR}/kokoro-v1.0.onnx", f"{MODEL_DIR}/voices-v1.0.bin")

# Acronyms spelled letter by letter, given as explicit phonemes.
ACR = {
    "HCPs": "ˌeɪtʃsˌiːpˈiːz", "HCOs": "ˌeɪtʃsˌiːˈoʊz", "HCP": "ˌeɪtʃsˌiːpˈiː", "HCO": "ˌeɪtʃsˌiːˈoʊ",
    "CE": "sˌiːˈiː", "FIA": "ˌɛfˌaɪˈeɪ", "US": "jˌuːˈɛs", "IPST": "ˌaɪpˌiːˌɛsˈtiː",
    "GMs": "dʒˌiːˈɛmz", "KPIs": "kˌeɪpˌiːˈaɪz",
}
ACR_RE = re.compile(r"\b(" + "|".join(sorted(ACR, key=len, reverse=True)) + r")\b")

def phonemize(text):
    out, pos = [], 0
    def add(chunk):
        if not chunk.strip():
            out.append(" " if chunk else ""); return
        lead = " " if chunk[0].isspace() else ""
        trail = " " if chunk[-1].isspace() else ""
        out.append(lead + k.tokenizer.phonemize(chunk.strip(), "en-us") + trail)
    for m in ACR_RE.finditer(text):
        add(text[pos:m.start()])
        out.append(ACR[m.group(1)])
        pos = m.end()
    add(text[pos:])
    return re.sub(r"\s+", " ", "".join(out)).strip()

def word_weights(text):
    ws = text.split()
    wts = []
    for w in ws:
        core = re.sub(r"[^\w']", "", w)
        if core in ACR: n = len(ACR[core])
        else: n = len(k.tokenizer.phonemize(core, "en-us")) if core else 1
        n += 4 if re.search(r"[,:;]$", w) else 0   # brief pause after punctuation
        wts.append(max(n, 1))
    return ws, wts

def trim(a, sr, thr=0.008):
    idx = np.where(np.abs(a) > thr)[0]
    s, e = max(idx[0] - int(0.02 * sr), 0), min(idx[-1] + int(0.06 * sr), len(a))
    return a[s:e]

SENTENCES = {
    1: ["Here's how the CE team builds its target lists, for HCPs and HCOs."],
    2: ["For HCPs, five analytics partners feed the FIA Targeting Team, with strategy, segments, predictive models, and response curves."],
    3: ["FIA builds HCP target lists that flow into Call Planning and Veeva, with US IPST and GMs reviewing as needed."],
    4: ["First, align on brand goals and the HCP universe.", "Next, models rank HCPs by opportunity.",
        "Then, insights become target tiers.", "Finally, lists reach the field with clear guidance."],
    5: ["HCO targeting uses the same engine to prioritize sites of care."],
    6: ["Agree objectives and KPIs.", "Build and validate the account universe.",
        "Review changes with stakeholders.", "Then deploy aligned lists to the field."],
    7: ["One team, one pipeline: who to engage, and where."],
}

res = {}
for scene, sents in SENTENCES.items():
    res[scene] = []
    for i, s in enumerate(sents):
        ph = phonemize(s)
        audio, sr = k.create(ph, voice="af_heart", speed=SPEED, lang="en-us", is_phonemes=True)
        audio = trim(audio, sr)
        fn = f"vo_{scene}_{i}.wav"
        sf.write(f"{OUT}/{fn}", audio, sr)
        ws, wts = word_weights(s)
        # word start times proportional to phoneme length
        tot, acc, starts = sum(wts), 0, []
        dur = len(audio) / sr
        for w in wts:
            starts.append(round(acc / tot * dur, 3)); acc += w
        res[scene].append({"text": s, "file": fn, "dur": round(dur, 3), "words": ws, "wstart": starts})
        print(scene, i, round(dur, 2), ph)
json.dump(res, open(f"{OUT}/vo.json", "w"), indent=1)
