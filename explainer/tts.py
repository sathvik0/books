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
    "GMs": "dʒˌiːˈɛmz", "Dataiku": "dˈeɪɾəˌiːkuː", "KPIs": "kˌeɪpˌiːˈaɪz",
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
    1: ["Here's how the CE team builds its target lists, for HCPs and HCOs: who to engage, and where."],
    2: ["For HCPs, four standard analytics partners feed the Targeting Team, with strategy, segments, predictive models, and data.",
        "On top of these, each brand brings its own sources, so the mix varies by brand."],
    3: ["The Targeting Team builds HCP target lists that flow into Call Planning and Veeva, with US IPST and GMs reviewing as needed.",
        "Resource Optimization feeds Call Planning separately, using response curves to shape call plans."],
    4: ["First, we align with the CE team on brand goals, scope, and targeting criteria.",
        "Next, we collect data from the analytics partners and brand-specific sources.",
        "We ingest it into one pipeline, standardizing formats and HCP identifiers.",
        "We validate quality and completeness, flagging gaps and duplicates.",
        "Then we build Python scripts on the Databricks and Dataiku platforms."],
    5: ["We consolidate every source into a single view of each HCP.",
        "We select the HCPs that meet the eligibility rules, forming the HCP universe.",
        "Each HCP is tiered on multiple attributes, keeping rep workload in mind, so calls can be planned by tier.",
        "We exclude HCPs that are ineligible or out of scope.",
        "Finally, we summarize the list by tier and territory for review.",
        "The result is a highly refined, optimal target list."],
    6: ["For HCOs, we start from the HCP target list.",
        "All sites affiliated with the selected HCPs, plus additional key sites, are combined into the HCO universe, then prioritized into HCO target lists for Call Planning and Veeva."],
    7: ["One team, one pipeline: who to engage, and where.", "Maximizing field impact and commercial outcomes."],
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
