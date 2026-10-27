"""
Generate answers for ScriptConsist v1 with a Hugging Face chat model.

Examples (Kaggle, 2x T4):
  python code/run_generation.py --model Qwen/Qwen2.5-7B-Instruct --precision fp16
  python code/run_generation.py --model Qwen/Qwen2.5-7B-Instruct --precision nf4
  python code/run_generation.py --model Qwen/Qwen2.5-7B-Instruct --limit 10     # quick check
  python code/run_generation.py --backend stub --limit 5                         # no GPU, tests the plumbing

Output: results/generations/<model-slug>__<precision>.jsonl, one line per prompt.
The run is resumable: rows already in the output file are skipped, so a Kaggle session that
times out can simply be restarted.

Decoding: greedy (do_sample=False), max_new_tokens=48, chat template, user turn only (no system
role, since Gemma has none).
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompts import FORMS, build_rows  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Per-model settings that matter on T4 GPUs (no bfloat16 tensor cores).
MODEL_NOTES = {
    "google/gemma-2-9b-it": {"attn_implementation": "eager", "compute_dtype": "float32_if_nf4"},
}


def slug(model):
    return model.replace("/", "__")


def load_hf(model_name, precision):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_name)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    kw = {"device_map": "auto"}
    note = MODEL_NOTES.get(model_name, {})
    if "attn_implementation" in note:
        kw["attn_implementation"] = note["attn_implementation"]
    if precision == "nf4":
        from transformers import BitsAndBytesConfig
        cdt = torch.float32 if note.get("compute_dtype") == "float32_if_nf4" else torch.float16
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_compute_dtype=cdt, bnb_4bit_use_double_quant=False)
    elif precision == "int8":
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    else:
        bf16_ok = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
        kw["torch_dtype"] = {"fp16": torch.float16, "bf16": torch.bfloat16 if bf16_ok else torch.float16,
                             "fp32": torch.float32}[precision]
    model = AutoModelForCausalLM.from_pretrained(model_name, **kw)
    model.eval()
    return tok, model


# Fallback prompt formats for models whose tokenizer ships no chat template
# (older Llama-2-based Indic models). Chosen with --prompt-format.
PROMPT_FORMATS = {
    "tulu": "<|user|>\n{p}\n<|assistant|>\n",                         # Airavata (AI4Bharat) / Tulu style
    "alpaca": "### Instruction:\n{p}\n\n### Response:\n",
    "llama2": "[INST] {p} [/INST]",
    "chatml": "<|im_start|>user\n{p}<|im_end|>\n<|im_start|>assistant\n",
}
STOP_STRINGS = ["<|im_end|>", "<|im_start|>", "<|user|>", "<|assistant|>", "### Instruction", "[INST]", "\nUser:", "<extra_id_1>"]


def format_prompts(tok, prompts, prompt_format):
    if prompt_format == "chat":
        if not getattr(tok, "chat_template", None):
            raise SystemExit("This tokenizer has no chat template. Re-run with --prompt-format tulu|alpaca|llama2 "
                             "(see the model card for which one it was trained with).")
        return [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
                for p in prompts]
    return [PROMPT_FORMATS[prompt_format].format(p=p) for p in prompts]


def cut_at_stop(text):
    for s in STOP_STRINGS:
        i = text.find(s)
        if i >= 0:
            text = text[:i]
    return text.strip()


def generate_hf(tok, model, prompts, max_new_tokens, prompt_format="chat"):
    import torch
    texts = format_prompts(tok, prompts, prompt_format)
    enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
    # stop on every end-of-turn marker the tokenizer knows (Nemotron: <extra_id_1>, Llama: <|eot_id|>, ...)
    stops = {tok.eos_token_id}
    for t in ("<extra_id_1>", "<|eot_id|>", "<end_of_turn>", "<|im_end|>", "<|END_OF_TURN_TOKEN|>"):
        tid = tok.convert_tokens_to_ids(t)
        if isinstance(tid, int) and tid != tok.unk_token_id and tid is not None and tid >= 0:
            stops.add(tid)
    stops.discard(None)
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, temperature=None,
                             top_p=None, top_k=None, pad_token_id=tok.pad_token_id, eos_token_id=sorted(stops))
    gen = out[:, enc["input_ids"].shape[1]:]
    return [cut_at_stop(tok.decode(g, skip_special_tokens=True)) for g in gen]


def generate_stub(prompts, max_new_tokens):
    """Plumbing test only: echoes a fixed answer in the prompt's script."""
    outs = []
    for p in prompts:
        if any("ऀ" <= c <= "ॿ" for c in p):
            outs.append("उत्तर: १९५०")
        elif "Answer" in p or "answer" in p:
            outs.append("1950")
        else:
            outs.append("I am not sure.")
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="stub")
    ap.add_argument("--backend", choices=["hf", "stub"], default="hf")
    ap.add_argument("--precision", choices=["fp16", "bf16", "fp32", "int8", "nf4"], default="fp16")
    ap.add_argument("--forms", nargs="+", default=FORMS)
    ap.add_argument("--prompt-ids", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--limit", type=int, default=None, help="first N questions only")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--max-new-tokens", type=int, default=48)
    ap.add_argument("--prompt-format", choices=["chat", "tulu", "alpaca", "llama2", "chatml"], default="chat",
                    help="'chat' uses the tokenizer's chat template; others are fallbacks for older models")
    ap.add_argument("--show-template", action="store_true", help="print how the first prompt is formatted, then exit")
    ap.add_argument("--out-dir", default=str(ROOT / "results" / "generations"))
    args = ap.parse_args()

    name = "stub" if args.backend == "stub" else args.model
    out = Path(args.out_dir) / f"{slug(name)}__{args.precision}{'__limit' + str(args.limit) if args.limit else ''}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for l in open(out, encoding="utf-8"):
            done.add(json.loads(l)["key"])

    rows = [r for r in build_rows(forms=args.forms, prompt_ids=args.prompt_ids, limit=args.limit) if r["key"] not in done]
    # sort by length so batches pad less
    rows.sort(key=lambda r: len(r["prompt"]))
    print(f"{name} [{args.precision}] -> {out.name}: {len(done)} done, {len(rows)} to go", flush=True)
    if not rows:
        return

    if args.show_template:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(args.model)
        print("chat template present:", bool(getattr(tok, "chat_template", None)))
        print(repr(format_prompts(tok, [rows[0]["prompt"]], args.prompt_format)[0]))
        return
    if args.backend == "hf":
        tok, model = load_hf(args.model, args.precision)
    t0 = time.time()
    with open(out, "a", encoding="utf-8") as f:
        for i in range(0, len(rows), args.batch_size):
            batch = rows[i:i + args.batch_size]
            prompts = [r["prompt"] for r in batch]
            if args.backend == "hf":
                outs = generate_hf(tok, model, prompts, args.max_new_tokens, args.prompt_format)
            else:
                outs = generate_stub(prompts, args.max_new_tokens)
            for r, o in zip(batch, outs):
                f.write(json.dumps({"key": r["key"], "item": r["item"], "form": r["form"], "prompt_id": r["prompt_id"],
                                    "model": name, "precision": args.precision, "prompt_format": args.prompt_format,
                                    "response": o},
                                   ensure_ascii=False) + "\n")
            f.flush()
            n = min(i + args.batch_size, len(rows))
            if (i // args.batch_size) % 10 == 0 or n == len(rows):
                el = time.time() - t0
                print(f"  {n}/{len(rows)}  {el / 60:.1f} min elapsed, ~{el / n * (len(rows) - n) / 60:.1f} min left", flush=True)


if __name__ == "__main__":
    main()
