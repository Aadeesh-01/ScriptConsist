"""
ScriptConsist Demo — Cross-Script Factual Consistency Explorer

A Gradio app that lets users:
1. Browse benchmark questions in three scripts
2. Query LLMs and compare answers across English / Hindi Devanagari / Romanized Hindi
3. See per-model factual consistency scores and script gap analysis
"""

import json
import os
import random
from pathlib import Path
from dataclasses import dataclass, field

import gradio as gr

# ── Paths ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
BENCHMARK = ROOT / "archive" / "data" / "scriptconsist_v0_draft.json"  # TODO: switch to ScriptConsist-IQ once annotated

# ── Load benchmark ─────────────────────────────────────────────────
with open(BENCHMARK, encoding="utf-8") as f:
    bench = json.load(f)

QUESTIONS = bench["questions"]
DOMAINS = sorted(set(q["domain"] for q in QUESTIONS))
DOMAIN_QUESTIONS = {d: [q for q in QUESTIONS if q["domain"] == d] for d in DOMAINS}

# ── Simulated model responses (for demo without API keys) ──────────
# In production, these would call real model APIs

MODELS = [
    "GPT-4o",
    "Gemma 2 9B",
    "Llama 3.1 8B",
    "Qwen 2.5 7B Instruct",
    "Nemotron-Mini-Hindi-4B",
]

# Simulated accuracy profiles per model (EN, HI_DEV, HI_ROM)
MODEL_PROFILES = {
    "GPT-4o":                {"en": 0.92, "hi_dev": 0.85, "hi_rom": 0.78},
    "Gemma 2 9B":            {"en": 0.84, "hi_dev": 0.72, "hi_rom": 0.64},
    "Llama 3.1 8B":          {"en": 0.82, "hi_dev": 0.68, "hi_rom": 0.60},
    "Qwen 2.5 7B Instruct":  {"en": 0.86, "hi_dev": 0.76, "hi_rom": 0.70},
    "Nemotron-Mini-Hindi-4B": {"en": 0.70, "hi_dev": 0.80, "hi_rom": 0.72},
}


def simulate_response(question: dict, model: str, script: str) -> dict:
    """Simulate a model response based on its accuracy profile."""
    profile = MODEL_PROFILES[model]
    prob_correct = profile[script]

    # Deterministic seeding for reproducibility
    seed = hash(f"{question['id']}_{model}_{script}") % 10000
    rng = random.Random(seed)

    correct = rng.random() < prob_correct
    gold = question["gold_answer"]

    if correct:
        # Return the correct answer, possibly in a variant form
        variants = question.get("gold_variants", [gold])
        response = rng.choice(variants) if variants else gold
    else:
        # Return a plausible but wrong answer
        wrong_answers = {
            "entity": ["Unknown", "N/A", "This information is not available"],
            "numeric": ["0", "Unknown", "N/A"],
            "date": ["Unknown year", "N/A"],
            "boolean": ["Yes" if gold.lower() == "no" else "No"],
            "descriptive": ["I don't have enough information to answer this."],
        }
        atype = question.get("answer_type", "entity")
        response = rng.choice(wrong_answers.get(atype, ["Unknown"]))

    return {
        "response": response,
        "correct": correct,
        "gold_answer": gold,
    }


# ── Gradio interface ───────────────────────────────────────────────

def browse_question(domain: str, index: int):
    """Show a question from the benchmark in all three scripts."""
    qs = DOMAIN_QUESTIONS.get(domain, [])
    if not qs:
        return "No questions found.", "", "", "", ""
    idx = max(0, min(index - 1, len(qs) - 1))
    q = qs[idx]
    return (
        f"**[{q['id']}]** ({q['domain']})",
        q["en"],
        q["hi_dev"],
        q["hi_rom"],
        f"**Gold answer:** {q['gold_answer']}  \n**Type:** {q.get('answer_type', 'entity')}  \n**Variants:** {', '.join(q.get('gold_variants', []))}",
    )


def run_consistency_check(domain: str, index: int, model: str):
    """Run a simulated consistency check for one question across scripts."""
    qs = DOMAIN_QUESTIONS.get(domain, [])
    if not qs:
        return "No questions available."
    idx = max(0, min(index - 1, len(qs) - 1))
    q = qs[idx]

    results = {}
    for script in ["en", "hi_dev", "hi_rom"]:
        results[script] = simulate_response(q, model, script)

    script_labels = {"en": "English", "hi_dev": "Hindi (Devanagari)", "hi_rom": "Romanized Hindi"}

    lines = [f"### Results for: {model}\n", f"**Question:** {q['en']}\n"]
    all_correct = True
    all_agree = True
    responses = []

    for script in ["en", "hi_dev", "hi_rom"]:
        r = results[script]
        status = "✅" if r["correct"] else "❌"
        lines.append(f"**{script_labels[script]}:** {r['response']} {status}")
        responses.append(r["response"])
        if not r["correct"]:
            all_correct = False

    # Check pairwise agreement
    lines.append("")
    pairs = [("en", "hi_dev"), ("en", "hi_rom"), ("hi_dev", "hi_rom")]
    for s1, s2 in pairs:
        agree = results[s1]["response"].lower().strip() == results[s2]["response"].lower().strip()
        if not agree:
            all_agree = False
        symbol = "🟢" if agree else "🔴"
        lines.append(f"{symbol} {script_labels[s1]} ↔ {script_labels[s2]}: {'Agree' if agree else 'Disagree'}")

    lines.append(f"\n**Gold Answer:** {q['gold_answer']}")

    if all_correct and all_agree:
        lines.append("\n🎯 **Perfect: Correct and consistent across all scripts!**")
    elif all_correct:
        lines.append("\n⚠️ **Correct in all scripts but responses differ in form.**")
    elif all_agree:
        lines.append("\n⚠️ **Consistent but not all correct.**")
    else:
        lines.append("\n❌ **Inconsistent and/or incorrect across scripts.**")

    return "\n".join(lines)


def compute_model_dashboard(model: str):
    """Compute aggregate metrics for a model across all questions."""
    script_correct = {"en": 0, "hi_dev": 0, "hi_rom": 0}
    pair_agree = {"en-hi_dev": 0, "en-hi_rom": 0, "hi_dev-hi_rom": 0}
    total = len(QUESTIONS)

    for q in QUESTIONS:
        responses = {}
        for script in ["en", "hi_dev", "hi_rom"]:
            r = simulate_response(q, model, script)
            responses[script] = r
            if r["correct"]:
                script_correct[script] += 1

        # Pairwise agreement
        pairs = [("en", "hi_dev"), ("en", "hi_rom"), ("hi_dev", "hi_rom")]
        for s1, s2 in pairs:
            if responses[s1]["response"].lower().strip() == responses[s2]["response"].lower().strip():
                pair_agree[f"{s1}-{s2}"] += 1

    # Compute metrics
    acc_en = script_correct["en"] / total
    acc_hi = script_correct["hi_dev"] / total
    acc_rom = script_correct["hi_rom"] / total
    avg_acc = (acc_en + acc_hi + acc_rom) / 3

    agree_eh = pair_agree["en-hi_dev"] / total
    agree_er = pair_agree["en-hi_rom"] / total
    agree_hr = pair_agree["hi_dev-hi_rom"] / total
    avg_agree = (agree_eh + agree_er + agree_hr) / 3

    fcs = avg_acc * avg_agree
    delta_lang = acc_en - (acc_hi + acc_rom) / 2
    delta_script = acc_hi - acc_rom

    lines = [
        f"## {model} — ScriptConsist Dashboard\n",
        "### Per-Script Accuracy",
        f"| Script | Accuracy |",
        f"|--------|----------|",
        f"| English | {acc_en:.1%} |",
        f"| Hindi (Devanagari) | {acc_hi:.1%} |",
        f"| Romanized Hindi | {acc_rom:.1%} |",
        "",
        "### Pairwise Agreement",
        f"| Pair | Agreement |",
        f"|------|-----------|",
        f"| EN ↔ HI_DEV | {agree_eh:.1%} |",
        f"| EN ↔ HI_ROM | {agree_er:.1%} |",
        f"| HI_DEV ↔ HI_ROM | {agree_hr:.1%} |",
        "",
        "### Composite Metrics",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| **Factual Consistency Score (FCS)** | **{fcs:.3f}** |",
        f"| Δ_lang (English advantage) | {delta_lang:+.1%} |",
        f"| Δ_script (Devanagari advantage) | {delta_script:+.1%} |",
    ]

    return "\n".join(lines)


def compare_all_models():
    """Generate a comparison table across all models."""
    rows = []
    for model in MODELS:
        total = len(QUESTIONS)
        sc = {"en": 0, "hi_dev": 0, "hi_rom": 0}
        for q in QUESTIONS:
            for s in ["en", "hi_dev", "hi_rom"]:
                if simulate_response(q, model, s)["correct"]:
                    sc[s] += 1

        acc_en = sc["en"] / total
        acc_hi = sc["hi_dev"] / total
        acc_rom = sc["hi_rom"] / total
        avg_acc = (acc_en + acc_hi + acc_rom) / 3
        delta_lang = acc_en - (acc_hi + acc_rom) / 2
        delta_script = acc_hi - acc_rom

        rows.append(f"| {model} | {acc_en:.1%} | {acc_hi:.1%} | {acc_rom:.1%} | {delta_lang:+.1%} | {delta_script:+.1%} |")

    header = [
        "## All Models — Comparison\n",
        "| Model | Acc (EN) | Acc (HI) | Acc (ROM) | Δ_lang | Δ_script |",
        "|-------|----------|----------|-----------|--------|----------|",
    ]

    footer = [
        "",
        "**Δ_lang** = English advantage over Hindi avg  ",
        "**Δ_script** = Devanagari advantage over Romanized  ",
        "",
        "*Note: Results shown are simulated for demonstration. Connect API keys for real model evaluation.*",
    ]

    return "\n".join(header + rows + footer)


# ── Build the Gradio app ──────────────────────────────────────────

with gr.Blocks(
    title="ScriptConsist — Cross-Script Factual Consistency",
    theme=gr.themes.Soft(),
) as demo:
    gr.Markdown(
        """
        # ScriptConsist
        ### Measuring Cross-Script Factual Consistency of LLMs across English, Hindi Devanagari, and Romanized Hindi

        A benchmark and evaluation framework for the **Threws Odyssey 2026** Applied Research category.

        ---
        """
    )

    with gr.Tabs():
        # ── Tab 1: Browse Benchmark ───────────────────────────────
        with gr.Tab("📚 Browse Benchmark"):
            gr.Markdown("Explore the benchmark questions in all three script forms.")
            with gr.Row():
                domain_dd = gr.Dropdown(DOMAINS, value=DOMAINS[0], label="Domain")
                index_slider = gr.Slider(1, 50, value=1, step=1, label="Question #")
            with gr.Row():
                q_id = gr.Markdown(label="ID")
            with gr.Row():
                q_en = gr.Textbox(label="English", lines=2, interactive=False)
            with gr.Row():
                q_hi = gr.Textbox(label="Hindi (Devanagari)", lines=2, interactive=False)
            with gr.Row():
                q_rom = gr.Textbox(label="Romanized Hindi", lines=2, interactive=False)
            with gr.Row():
                q_gold = gr.Markdown(label="Gold Answer")

            browse_btn = gr.Button("Show Question", variant="primary")
            browse_btn.click(
                browse_question,
                inputs=[domain_dd, index_slider],
                outputs=[q_id, q_en, q_hi, q_rom, q_gold],
            )

        # ── Tab 2: Consistency Check ──────────────────────────────
        with gr.Tab("🔍 Consistency Check"):
            gr.Markdown(
                "Select a question and model to see how responses compare across scripts."
            )
            with gr.Row():
                cc_domain = gr.Dropdown(DOMAINS, value=DOMAINS[0], label="Domain")
                cc_index = gr.Slider(1, 50, value=1, step=1, label="Question #")
                cc_model = gr.Dropdown(MODELS, value=MODELS[0], label="Model")
            cc_btn = gr.Button("Run Consistency Check", variant="primary")
            cc_output = gr.Markdown()
            cc_btn.click(
                run_consistency_check,
                inputs=[cc_domain, cc_index, cc_model],
                outputs=cc_output,
            )

        # ── Tab 3: Model Dashboard ────────────────────────────────
        with gr.Tab("📊 Model Dashboard"):
            gr.Markdown("View aggregate metrics for a single model.")
            dash_model = gr.Dropdown(MODELS, value=MODELS[0], label="Model")
            dash_btn = gr.Button("Compute Metrics", variant="primary")
            dash_output = gr.Markdown()
            dash_btn.click(
                compute_model_dashboard,
                inputs=dash_model,
                outputs=dash_output,
            )

        # ── Tab 4: Compare All Models ─────────────────────────────
        with gr.Tab("⚖️ Compare Models"):
            gr.Markdown("Side-by-side comparison of all models.")
            compare_btn = gr.Button("Generate Comparison", variant="primary")
            compare_output = gr.Markdown()
            compare_btn.click(compare_all_models, outputs=compare_output)

        # ── Tab 5: About ──────────────────────────────────────────
        with gr.Tab("ℹ️ About"):
            gr.Markdown(
                """
                ## About ScriptConsist

                **ScriptConsist** is a benchmark and evaluation framework for measuring
                cross-script factual consistency of Large Language Models across three
                input forms commonly used in India:

                1. **English** — the global lingua franca of LLM training
                2. **Hindi (Devanagari)** — the native script for Hindi
                3. **Romanized Hindi** — Hindi written in Roman letters, the dominant
                   form in digital communication (messaging, social media, search)

                ### Key Metrics

                - **Factual Consistency Score (FCS)**: A multiplicative metric combining
                  per-script accuracy and pairwise agreement
                - **Δ_lang**: The "English advantage" — how much better models perform
                  on English vs. Hindi
                - **Δ_script**: The "Devanagari advantage" — how much better models
                  perform on Devanagari vs. Romanized Hindi

                ### Citation

                ```
                @article{surana2026scriptconsist,
                  title={ScriptConsist: Measuring Cross-Script Factual Consistency
                         of LLMs Across English, Hindi Devanagari, and Romanized Hindi},
                  author={Surana, Aadeesh},
                  year={2026}
                }
                ```

                ### Links

                - [GitHub Repository](https://github.com/Aadeesh-01/ScriptConsist)
                - Threws Odyssey 2026 — Applied Research Category
                - IIIT Vadodara

                ---
                *Demo version uses simulated responses. Connect API keys for real evaluation.*
                """
            )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
