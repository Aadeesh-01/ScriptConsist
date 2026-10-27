"""
ScriptConsist — Cross-Script Factual Consistency Evaluation Pipeline
=====================================================================
Evaluates LLMs on the ScriptConsist benchmark across English, Hindi
Devanagari, and Romanized Hindi, computing accuracy, agreement, and
the Factual Consistency Score (FCS).

Usage:
    python evaluate.py --benchmark ../data/benchmark_seed.json \
                       --model qwen2.5-7b-instruct \
                       --output ../results/

For API-based models (GPT-4o, Gemini):
    python evaluate.py --benchmark ../data/benchmark_seed.json \
                       --model gpt-4o \
                       --api-key $OPENAI_API_KEY \
                       --output ../results/
"""

import json
import argparse
import os
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QuestionResult:
    question_id: str
    domain: str
    script: str  # en | hi_dev | hi_rom
    question_text: str
    gold_answer: str
    model_response: str
    is_correct: bool
    confidence: float  # fuzzy match score
    latency_ms: float


@dataclass
class PairwiseAgreement:
    question_id: str
    script_a: str
    script_b: str
    response_a: str
    response_b: str
    agree: bool
    method: str  # "exact" | "fuzzy" | "llm_judge"


@dataclass
class EvalResults:
    model_name: str
    timestamp: str
    per_question: list = field(default_factory=list)
    pairwise: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Matching utilities
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, remove articles."""
    text = text.lower().strip()
    text = re.sub(r'^(the|a|an|dr\.?|shri|श्री)\s+', '', text)
    text = re.sub(r'[.,;:!?()"\']', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fuzzy_match(response: str, gold: str, variants: list[str],
                threshold: float = 0.80) -> tuple[bool, float]:
    """
    Check if model response matches gold answer or any variant.
    Returns (is_match, best_score).
    """
    resp_norm = normalize(response)

    candidates = [normalize(gold)] + [normalize(v) for v in variants]

    best_score = 0.0
    for cand in candidates:
        # Exact containment
        if cand in resp_norm or resp_norm in cand:
            return True, 1.0

        # Sequence matcher ratio
        score = SequenceMatcher(None, resp_norm, cand).ratio()
        best_score = max(best_score, score)

        # Also check if candidate appears as a substring in a longer response
        if len(resp_norm) > len(cand) * 2:
            # Model may have given explanation; check if answer is in there
            words = resp_norm.split()
            for i in range(len(words)):
                for j in range(i + 1, min(i + len(cand.split()) + 3, len(words) + 1)):
                    chunk = ' '.join(words[i:j])
                    s = SequenceMatcher(None, chunk, cand).ratio()
                    best_score = max(best_score, s)

    return best_score >= threshold, best_score


def responses_agree(resp_a: str, resp_b: str) -> tuple[bool, str]:
    """
    Check if two responses convey the same factual content.
    Uses progressive matching: exact -> fuzzy -> keyword overlap.
    """
    norm_a = normalize(resp_a)
    norm_b = normalize(resp_b)

    # Exact match after normalization
    if norm_a == norm_b:
        return True, "exact"

    # Fuzzy ratio
    ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
    if ratio > 0.80:
        return True, "fuzzy"

    # Keyword overlap (for short answers)
    words_a = set(norm_a.split())
    words_b = set(norm_b.split())
    if words_a and words_b:
        overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
        if overlap > 0.6:
            return True, "keyword"

    return False, "none"


# ---------------------------------------------------------------------------
# Model interface (abstract)
# ---------------------------------------------------------------------------

class ModelInterface:
    """Base class for model querying."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    def query(self, question: str, script: str) -> tuple[str, float]:
        """Returns (response_text, latency_ms)."""
        raise NotImplementedError


class HuggingFaceModel(ModelInterface):
    """Query a HuggingFace model via transformers pipeline."""

    def __init__(self, model_name: str, device: str = "auto"):
        super().__init__(model_name)
        self.device = device
        self.pipeline = None

    def _load(self):
        if self.pipeline is not None:
            return
        try:
            from transformers import pipeline as hf_pipeline
            print(f"Loading model: {self.model_name}...")
            self.pipeline = hf_pipeline(
                "text-generation",
                model=self.model_name,
                device_map=self.device,
                max_new_tokens=256,
                do_sample=False,
                temperature=None,
            )
            print(f"Model loaded: {self.model_name}")
        except ImportError:
            raise ImportError("Install transformers: pip install transformers torch")

    def _get_system_prompt(self, script: str) -> str:
        prompts = {
            "en": "Answer the following factual question concisely and accurately. Provide only the answer, no explanation.",
            "hi_dev": "निम्नलिखित तथ्यात्मक प्रश्न का संक्षिप्त और सटीक उत्तर दें। केवल उत्तर दें, कोई स्पष्टीकरण नहीं।",
            "hi_rom": "Niche diye gaye tathyatmak prashn ka sankshipt aur sateek uttar dein. Kewal uttar dein, koi spashtikaran nahi.",
        }
        return prompts.get(script, prompts["en"])

    def query(self, question: str, script: str) -> tuple[str, float]:
        self._load()
        system = self._get_system_prompt(script)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

        start = time.perf_counter()
        out = self.pipeline(messages, return_full_text=False)
        elapsed = (time.perf_counter() - start) * 1000

        response = out[0]["generated_text"].strip()
        return response, elapsed


class OpenAIModel(ModelInterface):
    """Query OpenAI-compatible API."""

    def __init__(self, model_name: str, api_key: str,
                 base_url: str = "https://api.openai.com/v1"):
        super().__init__(model_name)
        self.api_key = api_key
        self.base_url = base_url
        self.client = None

    def _load(self):
        if self.client is not None:
            return
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("Install openai: pip install openai")

    def _get_system_prompt(self, script: str) -> str:
        prompts = {
            "en": "Answer the following factual question concisely and accurately. Provide only the answer, no explanation.",
            "hi_dev": "निम्नलिखित तथ्यात्मक प्रश्न का संक्षिप्त और सटीक उत्तर दें। केवल उत्तर दें, कोई स्पष्टीकरण नहीं।",
            "hi_rom": "Niche diye gaye tathyatmak prashn ka sankshipt aur sateek uttar dein. Kewal uttar dein, koi spashtikaran nahi.",
        }
        return prompts.get(script, prompts["en"])

    def query(self, question: str, script: str) -> tuple[str, float]:
        self._load()
        system = self._get_system_prompt(script)

        start = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=256,
        )
        elapsed = (time.perf_counter() - start) * 1000

        text = resp.choices[0].message.content.strip()
        return text, elapsed


class DummyModel(ModelInterface):
    """For testing the pipeline without a real model."""

    def query(self, question: str, script: str) -> tuple[str, float]:
        # Returns a plausible dummy answer for pipeline testing
        import random
        dummy_answers = {
            "en": "This is a test answer",
            "hi_dev": "यह एक परीक्षण उत्तर है",
            "hi_rom": "Yeh ek test answer hai",
        }
        return dummy_answers.get(script, "test"), random.uniform(50, 200)


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------

def run_evaluation(benchmark_path: str, model: ModelInterface,
                   num_runs: int = 1) -> EvalResults:
    """Run the full evaluation pipeline."""
    with open(benchmark_path) as f:
        benchmark = json.load(f)

    questions = benchmark["questions"]
    scripts = ["en", "hi_dev", "hi_rom"]

    results = EvalResults(
        model_name=model.model_name,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
    )

    # Phase 1: Query model and score per-question accuracy
    print(f"\n{'='*60}")
    print(f"Evaluating: {model.model_name}")
    print(f"Questions: {len(questions)} × {len(scripts)} scripts × {num_runs} runs")
    print(f"{'='*60}\n")

    responses = {}  # {(qid, script): response}

    for q in questions:
        qid = q["id"]
        gold = q["gold_answer"]
        variants = q.get("gold_variants", [])

        for script in scripts:
            question_text = q[script]

            # Average over runs
            best_response = None
            best_score = -1
            total_latency = 0

            for run in range(num_runs):
                response, latency = model.query(question_text, script)
                total_latency += latency
                is_correct, score = fuzzy_match(response, gold, variants)
                if score > best_score:
                    best_score = score
                    best_response = response

            is_correct, confidence = fuzzy_match(best_response, gold, variants)
            avg_latency = total_latency / num_runs

            qr = QuestionResult(
                question_id=qid,
                domain=q["domain"],
                script=script,
                question_text=question_text,
                gold_answer=gold,
                model_response=best_response,
                is_correct=is_correct,
                confidence=confidence,
                latency_ms=avg_latency,
            )
            results.per_question.append(qr)
            responses[(qid, script)] = best_response

            status = "✓" if is_correct else "✗"
            print(f"  [{status}] {qid} ({script}): {best_response[:60]}...")

    # Phase 2: Pairwise agreement
    print(f"\nComputing pairwise agreement...")
    script_pairs = [("en", "hi_dev"), ("en", "hi_rom"), ("hi_dev", "hi_rom")]

    for q in questions:
        qid = q["id"]
        for s_a, s_b in script_pairs:
            resp_a = responses.get((qid, s_a), "")
            resp_b = responses.get((qid, s_b), "")
            agree, method = responses_agree(resp_a, resp_b)

            pa = PairwiseAgreement(
                question_id=qid,
                script_a=s_a,
                script_b=s_b,
                response_a=resp_a,
                response_b=resp_b,
                agree=agree,
                method=method,
            )
            results.pairwise.append(pa)

    # Phase 3: Compute metrics
    results.metrics = compute_metrics(results)

    return results


def compute_metrics(results: EvalResults) -> dict:
    """Compute all ScriptConsist metrics."""
    scripts = ["en", "hi_dev", "hi_rom"]
    domains = sorted(set(qr.domain for qr in results.per_question))
    script_pairs = [("en", "hi_dev"), ("en", "hi_rom"), ("hi_dev", "hi_rom")]

    metrics = {}

    # Per-script accuracy
    for s in scripts:
        qs = [qr for qr in results.per_question if qr.script == s]
        acc = sum(1 for qr in qs if qr.is_correct) / len(qs) if qs else 0
        metrics[f"accuracy_{s}"] = round(acc, 4)

    # Per-domain per-script accuracy
    for d in domains:
        for s in scripts:
            qs = [qr for qr in results.per_question
                  if qr.script == s and qr.domain == d]
            acc = sum(1 for qr in qs if qr.is_correct) / len(qs) if qs else 0
            metrics[f"accuracy_{d}_{s}"] = round(acc, 4)

    # Pairwise agreement
    for s_a, s_b in script_pairs:
        pairs = [pa for pa in results.pairwise
                 if pa.script_a == s_a and pa.script_b == s_b]
        agree_rate = sum(1 for p in pairs if p.agree) / len(pairs) if pairs else 0
        metrics[f"agreement_{s_a}_{s_b}"] = round(agree_rate, 4)

    # Script gap metrics
    acc_en = metrics["accuracy_en"]
    acc_hi_dev = metrics["accuracy_hi_dev"]
    acc_hi_rom = metrics["accuracy_hi_rom"]

    metrics["delta_lang"] = round(acc_en - (acc_hi_dev + acc_hi_rom) / 2, 4)
    metrics["delta_script"] = round(acc_hi_dev - acc_hi_rom, 4)

    # Factual Consistency Score (FCS)
    avg_acc = (acc_en + acc_hi_dev + acc_hi_rom) / 3
    avg_agree = sum(
        metrics[f"agreement_{a}_{b}"] for a, b in script_pairs
    ) / len(script_pairs)
    metrics["fcs"] = round(avg_acc * avg_agree, 4)

    # Average latency per script
    for s in scripts:
        qs = [qr for qr in results.per_question if qr.script == s]
        avg_lat = sum(qr.latency_ms for qr in qs) / len(qs) if qs else 0
        metrics[f"avg_latency_ms_{s}"] = round(avg_lat, 2)

    return metrics


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(results: EvalResults):
    """Print a formatted evaluation report."""
    m = results.metrics
    scripts = ["en", "hi_dev", "hi_rom"]
    script_labels = {"en": "English", "hi_dev": "Hindi (Dev)", "hi_rom": "Hindi (Rom)"}

    print(f"\n{'='*60}")
    print(f"  ScriptConsist Evaluation Report")
    print(f"  Model: {results.model_name}")
    print(f"  Timestamp: {results.timestamp}")
    print(f"{'='*60}\n")

    # Overall accuracy
    print("┌─ Overall Accuracy by Script ─────────────────────────┐")
    for s in scripts:
        acc = m[f"accuracy_{s}"]
        bar = "█" * int(acc * 30) + "░" * (30 - int(acc * 30))
        print(f"│  {script_labels[s]:<16} {bar} {acc:.1%} │")
    print("└──────────────────────────────────────────────────────┘\n")

    # Domain breakdown
    domains = sorted(set(qr.domain for qr in results.per_question))
    print("┌─ Accuracy by Domain × Script ────────────────────────┐")
    header = f"│  {'Domain':<16}"
    for s in scripts:
        header += f" {script_labels[s]:<14}"
    print(header + "│")
    print("│  " + "─" * 52 + " │")
    for d in domains:
        row = f"│  {d:<16}"
        for s in scripts:
            acc = m.get(f"accuracy_{d}_{s}", 0)
            row += f" {acc:.1%}{'':>9}"
        print(row + "│")
    print("└──────────────────────────────────────────────────────┘\n")

    # Agreement
    print("┌─ Pairwise Agreement ─────────────────────────────────┐")
    pairs = [("en", "hi_dev"), ("en", "hi_rom"), ("hi_dev", "hi_rom")]
    for a, b in pairs:
        agree = m[f"agreement_{a}_{b}"]
        print(f"│  {script_labels[a]} ↔ {script_labels[b]}: {agree:.1%}")
    print("└──────────────────────────────────────────────────────┘\n")

    # Gap metrics & FCS
    print("┌─ Key Metrics ────────────────────────────────────────┐")
    print(f"│  Language Gap (Δ_lang):   {m['delta_lang']:+.1%}")
    print(f"│  Script Gap (Δ_script):   {m['delta_script']:+.1%}")
    print(f"│  Factual Consistency Score (FCS): {m['fcs']:.4f}")
    print("└──────────────────────────────────────────────────────┘\n")


def save_results(results: EvalResults, output_dir: str):
    """Save results to JSON."""
    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r'[/\\:]', '_', results.model_name)
    path = os.path.join(output_dir, f"results_{safe_name}.json")

    data = {
        "model_name": results.model_name,
        "timestamp": results.timestamp,
        "metrics": results.metrics,
        "per_question": [asdict(qr) for qr in results.per_question],
        "pairwise": [
            {k: v for k, v in asdict(pa).items()
             if k not in ("response_a", "response_b")}
            for pa in results.pairwise
        ],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {path}")
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ScriptConsist: Cross-Script Factual Consistency Evaluation"
    )
    parser.add_argument("--benchmark", required=True, help="Path to benchmark JSON")
    parser.add_argument("--model", default="dummy", help="Model name or HF path")
    parser.add_argument("--api-key", default=None, help="API key for OpenAI-compatible models")
    parser.add_argument("--base-url", default=None, help="Base URL for API")
    parser.add_argument("--output", default="./results", help="Output directory")
    parser.add_argument("--runs", type=int, default=1, help="Number of runs per question")
    parser.add_argument("--dummy", action="store_true", help="Use dummy model for testing")

    args = parser.parse_args()

    # Initialize model
    if args.dummy or args.model == "dummy":
        model = DummyModel("dummy")
    elif args.api_key:
        base_url = args.base_url or "https://api.openai.com/v1"
        model = OpenAIModel(args.model, args.api_key, base_url)
    else:
        model = HuggingFaceModel(args.model)

    # Run evaluation
    results = run_evaluation(args.benchmark, model, num_runs=args.runs)

    # Report & save
    print_report(results)
    save_results(results, args.output)


if __name__ == "__main__":
    main()
