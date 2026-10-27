"""
ScriptConsist v1 analysis: accuracy, paired gaps with confidence intervals, and secondary analyses.

Unit of analysis = question. For each model x question x form, accuracy is the mean over the 3 prompt
wordings (0, 1/3, 2/3, 1). Confidence intervals: 95% percentile bootstrap over questions (10,000
resamples). Gap p-values: paired sign-flip permutation test over questions (10,000 permutations),
Holm-corrected within each family of comparisons.

Usage: python code/analyze.py            -> results/analysis/*.csv and results/analysis/summary.md
"""

import csv
import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "analysis"
RNG = np.random.default_rng(2026)
N_BOOT = 10000
FORMS = ["en", "hi_dev", "hi_rom_std", "hi_rom_natural", "hi_rom_second"]
FORM_LABEL = {"en": "English", "hi_dev": "Devanagari", "hi_rom_std": "Romanized (rule-based)",
              "hi_rom_natural": "Hinglish (natural)", "hi_rom_second": "Hinglish (2nd typist)"}
MAIN_RUNS = ["Qwen__Qwen2.5-7B-Instruct__fp16", "meta-llama__Llama-3.1-8B-Instruct__fp16",
             "CohereLabs__aya-expanse-8b__fp16", "nvidia__Nemotron-4-Mini-Hindi-4B-Instruct__fp16",
             "google__gemma-2-9b-it__nf4", "ai4bharat__Airavata__fp16", "BhabhaAI__Gajendra-v0.1__fp16"]
SHORT = {"Qwen__Qwen2.5-7B-Instruct__fp16": "Qwen2.5-7B", "meta-llama__Llama-3.1-8B-Instruct__fp16": "Llama-3.1-8B",
         "CohereLabs__aya-expanse-8b__fp16": "Aya-Expanse-8B", "nvidia__Nemotron-4-Mini-Hindi-4B-Instruct__fp16":
         "Nemotron-Hindi-4B", "google__gemma-2-9b-it__nf4": "Gemma-2-9B (4-bit)",
         "Qwen__Qwen2.5-7B-Instruct__nf4": "Qwen2.5-7B (4-bit)", "meta-llama__Llama-3.1-8B-Instruct__nf4":
         "Llama-3.1-8B (4-bit)", "ai4bharat__Airavata__fp16": "Airavata-7B", "BhabhaAI__Gajendra-v0.1__fp16": "Gajendra-7B"}
# (name, form A, form B): gap = A - B
GAPS = [("language gap (EN - Devanagari)", "en", "hi_dev"),
        ("script gap (Devanagari - rule-based Roman)", "hi_dev", "hi_rom_std"),
        ("code-mixing gain (natural Hinglish - rule-based Roman)", "hi_rom_natural", "hi_rom_std"),
        ("natural Hinglish - Devanagari", "hi_rom_natural", "hi_dev"),
        ("EN - natural Hinglish", "en", "hi_rom_natural")]


def load_items():
    return {json.loads(l)["id"]: json.loads(l) for l in open(ROOT / "data" / "scriptconsist_v1.jsonl", encoding="utf-8")}


def load_runs():
    runs = {}
    for f in sorted(glob.glob(str(ROOT / "results" / "scored" / "*.jsonl"))):
        name = Path(f).stem
        if "limit" in name:
            continue
        acc = defaultdict(lambda: defaultdict(list))   # acc[form][item] -> [0/1 per prompt]
        rows = []
        for l in open(f, encoding="utf-8"):
            r = json.loads(l)
            acc[r["form"]][r["item"]].append(int(r["correct"]))
            rows.append(r)
        runs[name] = {"acc": {fm: {i: float(np.mean(v)) for i, v in d.items()} for fm, d in acc.items()}, "rows": rows}
    return runs


def boot_ci(vals):
    vals = np.asarray(vals, float)
    idx = RNG.integers(0, len(vals), size=(N_BOOT, len(vals)))
    means = vals[idx].mean(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def paired(a, b):
    """Mean difference a-b over questions, bootstrap CI, two-sided sign-flip permutation p."""
    d = np.asarray(a, float) - np.asarray(b, float)
    lo, hi = boot_ci(d)
    signs = RNG.choice([-1.0, 1.0], size=(N_BOOT, len(d)))
    null = (signs * d).mean(1)
    p = float((np.abs(null) >= abs(d.mean()) - 1e-12).mean())
    return float(d.mean()), lo, hi, max(p, 1 / N_BOOT)


def holm(ps):
    order = np.argsort(ps)
    adj = np.empty(len(ps))
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (len(ps) - rank) * ps[i])
        adj[i] = min(1.0, running)
    return adj.tolist()


def pct(x):
    return f"{100 * x:.1f}"


def write_csv(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    items = load_items()
    runs = load_runs()
    md = ["# ScriptConsist v1: results", "",
          f"Questions: {len(items)} (each asked with 3 prompt wordings). Accuracy is averaged over wordings per question;",
          "95% CIs are bootstrap over questions; p-values are paired permutation tests, Holm-corrected per table.", ""]

    # 1. accuracy table
    acc_rows = []
    for run, R in runs.items():
        for fm in FORMS:
            if fm not in R["acc"]:
                continue
            v = list(R["acc"][fm].values())
            lo, hi = boot_ci(v)
            acc_rows.append({"run": run, "model": SHORT.get(run, run), "form": fm, "n_questions": len(v),
                             "accuracy": round(float(np.mean(v)), 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4)})
    write_csv("accuracy.csv", acc_rows)
    md += ["## 1. Accuracy by model and question form (%)", "",
           "| Model | " + " | ".join(FORM_LABEL[f] for f in FORMS) + " |", "|---|" + "---|" * len(FORMS)]
    for run in MAIN_RUNS + [r for r in runs if r not in MAIN_RUNS]:
        if run not in runs:
            continue
        cells = []
        for fm in FORMS:
            a = next((x for x in acc_rows if x["run"] == run and x["form"] == fm), None)
            cells.append(f"{pct(a['accuracy'])} [{pct(a['ci_low'])}–{pct(a['ci_high'])}]" if a else "–")
        md.append(f"| {SHORT.get(run, run)} | " + " | ".join(cells) + " |")
    md.append("")

    # 2. paired gaps (main runs)
    gap_rows = []
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        A = runs[run]["acc"]
        for name, fa, fb in GAPS:
            common = sorted(set(A[fa]) & set(A[fb]))
            m, lo, hi, p = paired([A[fa][i] for i in common], [A[fb][i] for i in common])
            gap_rows.append({"model": SHORT[run], "gap": name, "n": len(common), "diff": round(m, 4),
                             "ci_low": round(lo, 4), "ci_high": round(hi, 4), "p": p})
    adj = holm([r["p"] for r in gap_rows])
    for r, a in zip(gap_rows, adj):
        r["p_holm"] = a
    write_csv("gaps.csv", gap_rows)
    md += ["## 2. Paired gaps (percentage points, A − B)", "",
           "| Model | " + " | ".join(g[0] for g in GAPS) + " |", "|---|" + "---|" * len(GAPS)]
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        cells = []
        for g in GAPS:
            r = next(x for x in gap_rows if x["model"] == SHORT[run] and x["gap"] == g[0])
            star = "*" if r["p_holm"] < 0.05 else ""
            cells.append(f"{100 * r['diff']:+.1f}{star} [{100 * r['ci_low']:+.1f}, {100 * r['ci_high']:+.1f}]")
        md.append(f"| {SHORT[run]} | " + " | ".join(cells) + " |")
    md += ["", "\\* Holm-adjusted p < 0.05.", ""]

    # 3. locality: India-specific vs global
    loc_rows = []
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        A = runs[run]["acc"]
        for loc in ("india", "global"):
            ids = [i for i, it in items.items() if it["locality"] == loc]
            row = {"model": SHORT[run], "locality": loc, "n": len(ids)}
            for fm in ["en", "hi_dev", "hi_rom_std", "hi_rom_natural"]:
                row[fm] = round(float(np.mean([A[fm][i] for i in ids])), 4)
            row["en_minus_natural"] = round(row["en"] - row["hi_rom_natural"], 4)
            row["en_minus_dev"] = round(row["en"] - row["hi_dev"], 4)
            loc_rows.append(row)
    write_csv("locality.csv", loc_rows)
    md += ["## 3. India-specific vs global questions (%)", "",
           "| Model | Locality | n | English | Devanagari | Rule-based Roman | Natural Hinglish | EN − Hinglish | EN − Devanagari |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in loc_rows:
        md.append(f"| {r['model']} | {r['locality']} | {r['n']} | {pct(r['en'])} | {pct(r['hi_dev'])} | "
                  f"{pct(r['hi_rom_std'])} | {pct(r['hi_rom_natural'])} | {100 * r['en_minus_natural']:+.1f} | "
                  f"{100 * r['en_minus_dev']:+.1f} |")
    md.append("")

    # 4. quantization: fp16 vs nf4, and whether 4-bit hurts Hindi forms more than English
    q_rows = []
    for base in ["Qwen__Qwen2.5-7B-Instruct", "meta-llama__Llama-3.1-8B-Instruct"]:
        f16, n4 = runs.get(base + "__fp16"), runs.get(base + "__nf4")
        if not (f16 and n4):
            continue
        for fm in ["en", "hi_dev", "hi_rom_std", "hi_rom_natural"]:
            ids = sorted(f16["acc"][fm])
            m, lo, hi, p = paired([f16["acc"][fm][i] for i in ids], [n4["acc"][fm][i] for i in ids])
            q_rows.append({"model": base.split("__")[1], "form": fm, "fp16_minus_nf4": round(m, 4),
                           "ci_low": round(lo, 4), "ci_high": round(hi, 4), "p": p})
        for fm in ["hi_dev", "hi_rom_natural"]:
            ids = sorted(f16["acc"][fm])
            dd = [(f16["acc"][fm][i] - n4["acc"][fm][i]) - (f16["acc"]["en"][i] - n4["acc"]["en"][i]) for i in ids]
            m, lo, hi, p = paired(dd, [0.0] * len(dd))
            q_rows.append({"model": base.split("__")[1], "form": f"extra loss vs EN: {fm}", "fp16_minus_nf4": round(m, 4),
                           "ci_low": round(lo, 4), "ci_high": round(hi, 4), "p": p})
    if q_rows:
        adj = holm([r["p"] for r in q_rows])
        for r, a in zip(q_rows, adj):
            r["p_holm"] = a
        write_csv("quantization.csv", q_rows)
        md += ["## 4. Quantization (fp16 − 4-bit NF4, percentage points)", "",
               "| Model | Form / contrast | fp16 − nf4 | 95% CI | Holm p |", "|---|---|---|---|---|"]
        for r in q_rows:
            md.append(f"| {r['model']} | {r['form']} | {100 * r['fp16_minus_nf4']:+.1f} | "
                      f"[{100 * r['ci_low']:+.1f}, {100 * r['ci_high']:+.1f}] | {r['p_holm']:.3g} |")
        md.append("")

    # 5. typist effect on the 73 doubly-typed questions
    t_rows = []
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        A = runs[run]["acc"]
        ids = sorted(set(A.get("hi_rom_second", {})) & set(A["hi_rom_natural"]))
        if not ids:
            continue
        m, lo, hi, p = paired([A["hi_rom_natural"][i] for i in ids], [A["hi_rom_second"][i] for i in ids])
        flip = float(np.mean([abs(A["hi_rom_natural"][i] - A["hi_rom_second"][i]) for i in ids]))
        t_rows.append({"model": SHORT[run], "n": len(ids), "first_author": round(float(np.mean([A["hi_rom_natural"][i] for i in ids])), 4),
                       "second_typist": round(float(np.mean([A["hi_rom_second"][i] for i in ids])), 4),
                       "diff": round(m, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4), "p": p,
                       "mean_abs_item_change": round(flip, 4)})
    if t_rows:
        adj = holm([r["p"] for r in t_rows])
        for r, a in zip(t_rows, adj):
            r["p_holm"] = a
        write_csv("typist.csv", t_rows)
        md += ["## 5. Same questions, two typists (n = 73)", "",
               "| Model | First author | Second typist | Diff | 95% CI | Holm p | Mean per-question change |",
               "|---|---|---|---|---|---|---|"]
        for r in t_rows:
            md.append(f"| {r['model']} | {pct(r['first_author'])} | {pct(r['second_typist'])} | {100 * r['diff']:+.1f} | "
                      f"[{100 * r['ci_low']:+.1f}, {100 * r['ci_high']:+.1f}] | {r['p_holm']:.3g} | {pct(r['mean_abs_item_change'])} |")
        md.append("")

    # 6. prompt sensitivity
    p_rows = []
    for run, R in runs.items():
        for fm in FORMS:
            by_p = defaultdict(list)
            for r in R["rows"]:
                if r["form"] == fm:
                    by_p[r["prompt_id"]].append(int(r["correct"]))
            if by_p:
                accs = [float(np.mean(by_p[k])) for k in sorted(by_p)]
                p_rows.append({"model": SHORT.get(run, run), "form": fm, **{f"prompt_{k}": round(a, 4) for k, a in zip(sorted(by_p), accs)},
                               "range": round(max(accs) - min(accs), 4)})
    write_csv("prompt_sensitivity.csv", p_rows)
    md += ["## 6. Prompt-wording sensitivity (range of accuracy across the 3 wordings, points)", "",
           "| Model | " + " | ".join(FORM_LABEL[f] for f in FORMS) + " |", "|---|" + "---|" * len(FORMS)]
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        cells = [next((f"{100 * x['range']:.1f}" for x in p_rows if x["model"] == SHORT[run] and x["form"] == fm), "–") for fm in FORMS]
        md.append(f"| {SHORT[run]} | " + " | ".join(cells) + " |")
    md.append("")

    # 7. answer script: what script does the model answer in?
    DEV, CJK, LAT = re.compile(r"[ऀ-ॿ]"), re.compile(r"[぀-ヿ一-鿿]"), re.compile(r"[A-Za-z]")
    PLACEHOLDER = re.compile(r"(नाम|name|naam)\s*_\s*\d", re.I)   # anonymised-name token, e.g. "नाम _ 1"
    s_rows = []
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        for fm in ["en", "hi_dev", "hi_rom_std", "hi_rom_natural"]:
            rs = [r["response"] for r in runs[run]["rows"] if r["form"] == fm]
            s_rows.append({"model": SHORT[run], "form": fm,
                           "devanagari": round(np.mean([bool(DEV.search(x)) for x in rs]), 4),
                           "latin_only": round(np.mean([bool(LAT.search(x)) and not DEV.search(x) and not CJK.search(x) for x in rs]), 4),
                           "cjk": round(np.mean([bool(CJK.search(x)) for x in rs]), 4),
                           "name_placeholder": round(np.mean([bool(PLACEHOLDER.search(x)) for x in rs]), 4)})
    write_csv("answer_script.csv", s_rows)
    md += ["## 7. Script of the model's answer (% of answers containing it)", "",
           "| Model | Question form | Devanagari | Latin only | Chinese/Japanese | Name placeholder (NAME_1) |", "|---|---|---|---|---|---|"]
    for r in s_rows:
        md.append(f"| {r['model']} | {FORM_LABEL[r['form']]} | {pct(r['devanagari'])} | {pct(r['latin_only'])} | {pct(r['cjk'])} | {pct(r['name_placeholder'])} |")
    md.append("")

    # 8. code-mixing: share of English words in the natural Hinglish question vs accuracy gain
    tok = lambda s: re.findall(r"[a-z0-9']+", s.lower())
    eng_share = {}
    for i, it in items.items():
        en = set(tok(it["en"]))
        h = tok(it["hi_rom_natural"])
        eng_share[i] = sum(t in en for t in h) / max(1, len(h))
    from scipy.stats import spearmanr  # noqa: E402
    c_rows = []
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        A = runs[run]["acc"]
        ids = sorted(eng_share)
        x = [eng_share[i] for i in ids]
        gain = [A["hi_rom_natural"][i] - A["hi_rom_std"][i] for i in ids]
        rho, p = spearmanr(x, gain)
        acc_rho, acc_p = spearmanr(x, [A["hi_rom_natural"][i] for i in ids])
        c_rows.append({"model": SHORT[run], "rho_share_vs_gain": round(float(rho), 3), "p_gain": float(p),
                       "rho_share_vs_natural_acc": round(float(acc_rho), 3), "p_acc": float(acc_p)})
    write_csv("codemixing.csv", c_rows)
    md += ["## 8. Code-mixing", "",
           f"Mean share of words in the natural Hinglish question taken from the English question: "
           f"{100 * np.mean(list(eng_share.values())):.1f}% (median {100 * np.median(list(eng_share.values())):.1f}%).", "",
           "| Model | Spearman ρ: English share vs (Hinglish − rule-based) gain | p | ρ: English share vs Hinglish accuracy | p |",
           "|---|---|---|---|---|"]
    for r in c_rows:
        md.append(f"| {r['model']} | {r['rho_share_vs_gain']:+.3f} | {r['p_gain']:.3g} | {r['rho_share_vs_natural_acc']:+.3f} | {r['p_acc']:.3g} |")
    md.append("")

    # 9. names in English spelling: share of the English question's capitalised words (names, titles) that the
    #    natural Hinglish question keeps verbatim. Exploratory; Holm-corrected over models x 2 outcomes.
    STOPW = {"What", "Which", "Who", "When", "Where", "How", "In", "The", "Of", "A", "An", "During", "Out", "To", "Is",
             "Was", "On", "For", "And", "By", "At", "From", "Did", "Does", "Name"}
    name_cov = {}
    for i, it in items.items():
        names = [t.lower().strip(".'") for t in re.findall(r"[A-Za-z][A-Za-z'.-]+", it["en"])
                 if t[0].isupper() and t not in STOPW and len(t) >= 3]
        if names:
            kept = set(tok(it["hi_rom_natural"]))
            name_cov[i] = sum(t in kept for t in names) / len(names)
    n_rows = []
    ids = sorted(name_cov)
    for run in MAIN_RUNS:
        if run not in runs:
            continue
        A = runs[run]["acc"]
        for outcome, fb in (("natural - rule-based Roman", "hi_rom_std"), ("natural - Devanagari", "hi_dev")):
            g = [A["hi_rom_natural"][i] - A[fb][i] for i in ids]
            rho, p = spearmanr([name_cov[i] for i in ids], g)
            allk = [A["hi_rom_natural"][i] - A[fb][i] for i in ids if name_cov[i] == 1]
            part = [A["hi_rom_natural"][i] - A[fb][i] for i in ids if name_cov[i] < 1]
            n_rows.append({"model": SHORT[run], "outcome": outcome, "gain_all_names_kept": round(float(np.mean(allk)), 4),
                           "gain_some_names_changed": round(float(np.mean(part)), 4), "rho": round(float(rho), 3), "p": float(p)})
    adj = holm([r["p"] for r in n_rows])
    for r, a in zip(n_rows, adj):
        r["p_holm"] = a
    write_csv("name_spelling.csv", n_rows)
    n_all = sum(v == 1 for v in name_cov.values())
    md += ["## 9. Names kept in English spelling (exploratory)", "",
           f"{len(name_cov)} questions contain capitalised names or titles; the natural Hinglish keeps all of them in English "
           f"spelling in {n_all} ({100 * n_all / len(name_cov):.0f}%), some in {len(name_cov) - n_all}.", "",
           "| Model | Outcome | Gain, all names kept | Gain, some changed | Spearman ρ (share kept vs gain) | Holm p |",
           "|---|---|---|---|---|---|"]
    for r in n_rows:
        md.append(f"| {r['model']} | {r['outcome']} | {100 * r['gain_all_names_kept']:+.1f} | {100 * r['gain_some_names_changed']:+.1f} | "
                  f"{r['rho']:+.3f} | {r['p_holm']:.3g} |")
    md.append("")

    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
