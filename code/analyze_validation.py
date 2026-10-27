"""
Scorer validation against blind human judgments (docs/PROTOCOL.md section 14).

Inputs:  results/validation/sample_key.jsonl      scorer verdict, model, form, batch for each validation id
         results/validation/human_verdicts.jsonl  the validator's verdicts (correct / wrong / unsure), exported
                                                  from the annotation page
         results/validation/bundle_v1.json        what the validator saw
         results/scored/*.jsonl                   all scored answers (for corrected accuracies)
Output:  results/validation/validation_report.md
         results/validation/disagreements.csv

Main analysis: batches v1 + indic_models (340 answers); `unsure` verdicts are excluded, with a sensitivity
analysis counting them as wrong. The 48 repeats are used only for the validator's self-consistency.

Correction: the sample is stratified on the scorer's verdict, so it estimates, per form,
  FA = P(human wrong | scorer correct)   false-accept rate
  M  = P(human correct | scorer wrong)   missed-correct rate
and the corrected accuracy of a run is  acc * (1 - FA) + (1 - acc) * M.
"""

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "results" / "validation"
FORMS = ["en", "hi_dev", "hi_rom_std", "hi_rom_natural"]
FORM_NAME = {"en": "English", "hi_dev": "Devanagari", "hi_rom_std": "Rule-based Roman",
             "hi_rom_natural": "Natural Hinglish", "all": "All forms"}
RUN_NAME = {
    "Qwen__Qwen2.5-7B-Instruct__fp16": "Qwen2.5-7B", "meta-llama__Llama-3.1-8B-Instruct__fp16": "Llama-3.1-8B",
    "CohereLabs__aya-expanse-8b__fp16": "Aya-Expanse-8B", "nvidia__Nemotron-4-Mini-Hindi-4B-Instruct__fp16": "Nemotron-Hindi-4B",
    "google__gemma-2-9b-it__nf4": "Gemma-2-9B (4-bit)", "ai4bharat__Airavata__fp16": "Airavata-7B",
    "BhabhaAI__Gajendra-v0.1__fp16": "Gajendra-7B", "Qwen__Qwen2.5-7B-Instruct__nf4": "Qwen2.5-7B (4-bit)",
    "meta-llama__Llama-3.1-8B-Instruct__nf4": "Llama-3.1-8B (4-bit)"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def kappa(pairs):
    """Cohen's kappa for a list of (a, b) booleans."""
    n = len(pairs)
    if n == 0:
        return float("nan")
    po = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def pct(x):
    return f"{100 * x:.1f}"


def rates(rows):
    """rows: list of (auto_correct, human_correct). Returns FA and M with Wilson CIs."""
    ac = [h for a, h in rows if a]
    aw = [h for a, h in rows if not a]
    fa = wilson(sum(not h for h in ac), len(ac))
    m = wilson(sum(h for h in aw), len(aw))
    return fa, m, len(ac), len(aw)


def main():
    key = {json.loads(l)["id"]: json.loads(l) for l in open(VAL / "sample_key.jsonl", encoding="utf-8")}
    hv = {json.loads(l)["id"]: json.loads(l) for l in open(VAL / "human_verdicts.jsonl", encoding="utf-8")}
    shown = {x["id"]: x for x in json.load(open(VAL / "bundle_v1.json", encoding="utf-8"))["items"]}
    missing = [i for i in key if i not in hv]
    assert not missing, f"no verdict for {missing[:5]}"

    main_ids = [i for i, k in key.items() if k["batch"] in ("v1", "indic_models")]
    out = ["# Scorer validation", "",
           f"Blind human judgments of {len(key)} answers: {len(main_ids)} for the scorer check "
           f"({sum(key[i]['batch'] == 'v1' for i in main_ids)} from five general models, "
           f"{sum(key[i]['batch'] == 'indic_models' for i in main_ids)} from Airavata and Gajendra) and "
           f"{sum(k['batch'] == 'repeat' for k in key.values())} repeats for the validator's self-consistency. "
           "One validator (the first author); the scorer's verdict and the model name were hidden.", ""]

    verdicts = Counter(hv[i]["verdict"] for i in main_ids)
    secs = sorted(hv[i]["seconds"] for i in key if isinstance(hv[i].get("seconds"), (int, float)))
    out += [f"Verdicts (main set): {dict(verdicts)}. Median time per judgment: {secs[len(secs) // 2]} s "
            f"(interquartile {secs[len(secs) // 4]}–{secs[3 * len(secs) // 4]} s).", ""]

    # ---- 1. agreement per form
    def table(unsure_as_wrong):
        by = defaultdict(list)
        for i in main_ids:
            v = hv[i]["verdict"]
            if v == "unsure" and not unsure_as_wrong:
                continue
            row = (key[i]["auto_correct"], v == "correct")
            by[key[i]["form"]].append(row)
            by["all"].append(row)
        return by

    res = {}
    for label, uw in (("main", False), ("unsure_as_wrong", True)):
        by = table(uw)
        res[label] = by
        title = ("## 1. Scorer vs human, per form" if label == "main"
                 else "### Sensitivity: `unsure` counted as wrong")
        out += [title, "",
                "| Form | n | Agreement % | Cohen's κ | False accepts (human wrong / scorer correct) | "
                "Missed correct (human correct / scorer wrong) |",
                "|---|---|---|---|---|---|"]
        for f in FORMS + ["all"]:
            rows = by[f]
            agree = sum(a == h for a, h in rows) / len(rows)
            fa, m, nac, naw = rates(rows)
            out.append(f"| {FORM_NAME[f]} | {len(rows)} | {pct(agree)} | {kappa(rows):.3f} | "
                       f"{round(fa[0] * nac)}/{nac} = {pct(fa[0])}% [{pct(fa[1])}–{pct(fa[2])}] | "
                       f"{round(m[0] * naw)}/{naw} = {pct(m[0])}% [{pct(m[1])}–{pct(m[2])}] |")
        out.append("")
    out += ["Brackets: 95% Wilson intervals. The sample is half scorer-correct and half scorer-wrong in each form, "
            "so raw agreement here is not the scorer's accuracy on the full data; that is estimated in section 3.", ""]

    # by batch
    out += ["### By model group (main set, unsure excluded)", "", "| Group | n | Agreement % | κ |", "|---|---|---|---|"]
    for b, name in (("v1", "Five general models"), ("indic_models", "Airavata + Gajendra")):
        rows = [(key[i]["auto_correct"], hv[i]["verdict"] == "correct") for i in main_ids
                if key[i]["batch"] == b and hv[i]["verdict"] != "unsure"]
        out.append(f"| {name} | {len(rows)} | {pct(sum(a == h for a, h in rows) / len(rows))} | {kappa(rows):.3f} |")
    out.append("")

    # ---- 2. self-consistency
    reps = [k for k in key.values() if k["batch"] == "repeat"]
    pairs_all = [(hv[k["repeat_of"]]["verdict"], hv[k["id"]]["verdict"]) for k in reps]
    pairs = [(a == "correct", b == "correct") for a, b in pairs_all if "unsure" not in (a, b)]
    same = sum(a == b for a, b in pairs_all)
    out += ["## 2. Validator self-consistency (48 repeated answers)", "",
            f"Same verdict both times: {same}/{len(pairs_all)} ({pct(same / len(pairs_all))}%), counting `unsure` as its own verdict. "
            f"Excluding pairs with an `unsure`: {sum(a == b for a, b in pairs)}/{len(pairs)}, κ = {kappa(pairs):.3f}. "
            "Each repeat was shown at least 90 positions (median ≈ 200) after the first showing.", ""]
    changed = [(k, hv[k["repeat_of"]]["verdict"], hv[k["id"]]["verdict"]) for k in reps
               if hv[k["repeat_of"]]["verdict"] != hv[k["id"]]["verdict"]]
    for k, a, b in changed:
        s = shown[k["id"]]
        out.append(f"- {k['repeat_of']} → {k['id']} ({FORM_NAME[k['form']]}): {a} → {b}. Gold: {s['gold']}. "
                   f"Answer: {s['response'][:100].replace(chr(10), ' ')}")
    out.append("")

    # ---- 3. corrected accuracies
    fa_m = {}
    for f in FORMS:
        fa, m, _, _ = rates(res["main"][f])
        fa_m[f] = (fa, m)
    acc = {}
    for run in RUN_NAME:
        p = ROOT / "results" / "scored" / f"{run}.jsonl"
        if not p.exists():
            continue
        by = defaultdict(list)
        for l in open(p, encoding="utf-8"):
            r = json.loads(l)
            by[r["form"]].append(bool(r["correct"]))
        acc[run] = {f: sum(v) / len(v) for f, v in by.items() if f in FORMS}

    def corr(a, f, mode="point"):
        fa, m = fa_m[f]
        if mode == "point":
            x, y = fa[0], m[0]
        elif mode == "low":      # lowest plausible true accuracy
            x, y = fa[2], m[1]
        else:                     # highest plausible true accuracy
            x, y = fa[1], m[2]
        return a * (1 - x) + (1 - a) * y

    out += ["## 3. Accuracies corrected for scorer error (%)", "",
            "corrected = scorer accuracy × (1 − false-accept rate) + (1 − scorer accuracy) × missed-correct rate, "
            "with the per-form rates from section 1. Rates are pooled over models.", "",
            "| Model | English | Devanagari | Rule-based Roman | Natural Hinglish |", "|---|---|---|---|---|"]
    for run, a in acc.items():
        out.append(f"| {RUN_NAME[run]} | " + " | ".join(f"{pct(a[f])} → **{pct(corr(a[f], f))}**" for f in FORMS) + " |")
    out += ["", "Estimated scorer accuracy on the full data (share of all scored answers where a human would agree), "
            "per form, averaged over the nine runs: " + ", ".join(
                f"{FORM_NAME[f]} {pct(sum(a[f] * (1 - fa_m[f][0][0]) + (1 - a[f]) * (1 - fa_m[f][1][0]) for a in acc.values()) / len(acc))}%"
                for f in FORMS) + ".", ""]

    out += ["## 4. Do the main gaps survive scorer error? (percentage points)", "",
            "Worst case: the form expected to be higher gets its lowest plausible accuracy and the other form its highest "
            "(ends of the 95% intervals of both error rates).", "",
            "| Model | Hinglish − Devanagari: scorer | corrected | worst case | Devanagari − rule-based Roman: scorer | corrected | worst case |",
            "|---|---|---|---|---|---|---|"]
    survive = Counter()
    for run, a in acc.items():
        cells = []
        for hi, lo in (("hi_rom_natural", "hi_dev"), ("hi_dev", "hi_rom_std")):
            raw = a[hi] - a[lo]
            c = corr(a[hi], hi) - corr(a[lo], lo)
            w = corr(a[hi], hi, "low") - corr(a[lo], lo, "high")
            survive[(hi, lo)] += w > 0
            cells += [f"{100 * raw:+.1f}", f"{100 * c:+.1f}", f"{100 * w:+.1f}"]
        out.append(f"| {RUN_NAME[run]} | " + " | ".join(cells) + " |")
    out += ["", f"Extreme bound: Hinglish > Devanagari holds for {survive[('hi_rom_natural', 'hi_dev')]}/{len(acc)} runs; "
            f"Devanagari > rule-based Roman for {survive[('hi_dev', 'hi_rom_std')]}/{len(acc)}. This bound puts both forms' error "
            "rates at opposite ends of their intervals at once, and a form with 0 observed errors in ~40 answers still gets "
            "an 8% error rate, so it is very conservative.", ""]

    # simulation: draw each form's FA and M from Beta(k+1, n-k+1) (uniform prior) and recompute the corrected gap
    import random
    rng = random.Random(2026)
    counts = {}
    for f in FORMS:
        rows = res["main"][f]
        ac = [h for a, h in rows if a]
        aw = [h for a, h in rows if not a]
        counts[f] = (sum(not h for h in ac), len(ac), sum(h for h in aw), len(aw))
    N = 20000
    draws = []
    for _ in range(N):
        d = {}
        for f, (kfa, nfa, km, nm) in counts.items():
            d[f] = (rng.betavariate(kfa + 1, nfa - kfa + 1), rng.betavariate(km + 1, nm - km + 1))
        draws.append(d)
    out += ["### Uncertainty in the scorer's error rates, propagated (20,000 simulations)", "",
            "Each simulation draws every form's two error rates from what the validation sample allows "
            "(Beta posterior, uniform prior) and recomputes the corrected gap. Shown: median gap, 95% range, "
            "and the share of simulations where the gap stays above zero.", "",
            "| Model | Hinglish − Devanagari | P(> 0) | Devanagari − rule-based Roman | P(> 0) |", "|---|---|---|---|---|"]
    for run, a in acc.items():
        cells = []
        for hi, lo in (("hi_rom_natural", "hi_dev"), ("hi_dev", "hi_rom_std")):
            g = sorted(100 * ((a[hi] * (1 - d[hi][0]) + (1 - a[hi]) * d[hi][1]) -
                              (a[lo] * (1 - d[lo][0]) + (1 - a[lo]) * d[lo][1])) for d in draws)
            cells += [f"{g[N // 2]:+.1f} [{g[int(.025 * N)]:+.1f}, {g[int(.975 * N)]:+.1f}]",
                      f"{sum(x > 0 for x in g) / N:.3f}"]
        out.append(f"| {RUN_NAME[run]} | " + " | ".join(cells) + " |")
    out += ["", "This covers uncertainty about the scorer only. Uncertainty from the choice of questions is in "
            "`results/analysis/summary.md` (bootstrap over questions).", ""]

    # ---- 5. disagreements
    dis = []
    for i in main_ids:
        v, k, s = hv[i]["verdict"], key[i], shown[i]
        if v == "unsure" or (v == "correct") != k["auto_correct"]:
            dis.append({"id": i, "form": k["form"], "model": k["model"], "scorer": "correct" if k["auto_correct"] else "wrong",
                        "human": v, "rule": k["match_rule"], "gold": s["gold"], "response": s["response"],
                        "note": hv[i].get("note", "")})
    with open(VAL / "disagreements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(dis[0]))
        w.writeheader()
        w.writerows(dis)
    out += ["## 5. Every disagreement and `unsure`", "", "| id | Form | Scorer | Human | Gold | Answer (start) |", "|---|---|---|---|---|---|"]
    for d in sorted(dis, key=lambda d: (d["human"] == "unsure", d["form"])):
        out.append(f"| {d['id']} | {FORM_NAME[d['form']]} | {d['scorer']} | {d['human']} | {d['gold']} | "
                   f"{d['response'][:80].replace(chr(10), ' ').replace('|', '/')} |")
    out.append("")
    (VAL / "validation_report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:60]))


if __name__ == "__main__":
    main()
