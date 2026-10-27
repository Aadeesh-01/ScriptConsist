# ScriptConsist Dataset Construction Protocol (v1)

Status: draft, 2026-10-23. The early drafts (now `archive/data/benchmark_seed_v0.json` / `archive/data/scriptconsist_v0_draft.json`)
(65 items) are **deprecated drafts** and are not used for any reported result.

## 1. Why the drafts were rejected

| Problem | Examples | Consequence if kept |
|---|---|---|
| Wrong or outdated gold | Amaravati as "new national capital" (it is the AP state capital); India "5th" by GDP (now disputed 4th vs 6th); Zepto "most valued startup"; CJI question | Accuracy numbers measure our errors, not the model's |
| No single defensible answer | "National sport" (no sport officially declared, per RTI); Preamble "also known as"; Chilika "largest lake" (a lagoon; Wular is largest freshwater); Nalanda "world's first" | Reviewer can dispute the item |
| Wrong answer content | Palk Strait gold mentions Arabian Sea; "father of Hindi literature" (Bharatendu is father of *modern* Hindi literature) | Same |
| Scoring traps | Speed of light as `299792458` (fails on "3×10⁸") | Matcher, not model, decides the score |
| Pipeline bug | 25 new items silently dropped because their IDs collided with seed IDs | Dataset composition not what we think |
| No provenance | `source` is a generic phrase, not a citation | Unverifiable |
| AI-authored, unverified Hindi | Questions and translations written by an LLM, no native-speaker check; some Romanizations unnatural | Circularity + translation-quality critique |
| One Romanization per item | Single spelling (e.g. "pradhanmantri") | Script effect confounded with one arbitrary spelling |
| Ceiling-level difficulty | All common GK | Frontier models near 100% in every script → gaps vanish |

## 2. Inclusion criteria (every item must satisfy all)

1. **Single answer.** One correct answer, expressible in ≤ 5 words, number, or date.
2. **Time-stable.** No "current", "recent", "latest". Time-bound facts carry an explicit anchor ("as of 2023") and the fact must predate 2024 so every evaluated model could have seen it.
3. **Uncontested.** No territorial or political disputes, no "considered the first/greatest", no honorific titles with multiple holders.
4. **Two sources.** Gold verified in ≥ 2 independent authoritative sources, with URL (and page for books). At least one Indian official/educational source (NCERT, gov.in, Constitution text) where applicable.
5. **Scorable.** Answer type ∈ {entity, number, date, year}. Numbers have a tolerance or canonical form; no free-text descriptive answers.
6. **No answer leakage.** The question text in any script does not contain the answer or a transliteration of it.

## 3. Sources

- **NCERT textbooks (Classes 6–12)**, which are published in parallel English and Hindi editions. Each item is authored from a specific passage; the Hindi edition provides officially used Hindi terminology for the same fact.
- **Wikidata** for entity answers: English and Hindi labels + aliases populate `gold_variants` systematically instead of by hand.
- **Constitution of India** (official English and Hindi texts) for Civics.
- Not used: LLM-generated questions without a source passage.

## 4. Design variables (so the dataset supports analysis, not just a score)

| Variable | Levels | Why |
|---|---|---|
| Domain | History, Geography, Science, Civics, Culture, Economy & Society | Domain effects |
| Knowledge locality | India-specific / global | Tests whether the script gap depends on where the knowledge lives in training data |
| Difficulty tier | T1 common GK / T2 textbook (Class 9–12) / T3 long-tail (regional figures, district-level facts) | Avoids ceiling effects; T3 is where gaps are expected |
| Answer type | entity / number / date | Separates knowledge errors from formatting errors |

"Current Affairs" is replaced by **Economy & Society** with date-anchored facts, because undated current-events questions are not defensible across models with different cutoffs.

## 5. Size and power

Script comparisons are paired (same item, two scripts), analysed with McNemar's test.
For α = 0.05, power = 0.8, and a 15% discordant-pair rate:

| Gap to detect | Items needed |
|---|---|
| 8 pp | ~180 |
| 5 pp | ~470 |
| 3 pp | ~1,300 |

**Target: 600 accepted items** (100 per domain), enough for 5 pp overall gaps.
Per-domain results (n = 100) are reported with confidence intervals and described as exploratory.
Author ~800 candidates; expect ~25% rejection at verification.

## 6. Three script forms

- **English**: authored from the source passage.
- **Hindi (Devanagari)**: written by native speaker A as natural Hindi (not word-for-word), checked independently by native speaker B. Disagreements are resolved and logged.
- **Romanized Hindi**, two variants per item:
  - `hi_rom_natural`: how a native speaker would type it on WhatsApp, written by a native speaker without looking at a scheme;
  - `hi_rom_std`: deterministic transliteration of the Devanagari (IndicXlit / ITRANS-style), for a fully reproducible condition.
  The gap between the two is itself a reported result (sensitivity to Romanization).
- **Code-mixing policy** (revised 2026-10-23): `hi_rom_natural` is typed exactly as the annotator would text it, English words included ("Constitution ka kaunsa article..."). Real Romanized Hindi is code-mixed, and forcing pure Hindi vocabulary would make the condition artificial. `hi_rom_std` keeps the Devanagari's Hindi words, so the comparisons separate the two effects:
  - Devanagari → `hi_rom_std`: script only (same words)
  - `hi_rom_std` → `hi_rom_natural`: code-mixing only (same script)
  - Per item, we report the share of English tokens in `hi_rom_natural` (a code-mixing index) and test whether accuracy rises with it.

## 7. Scoring validity

- Gold variants cover all three scripts (English, Devanagari, Roman) plus Devanagari digits (०–९) and number words.
- The automatic matcher is validated against blind human judgments on a stratified sample of model responses (details in section 14). We report matcher–human agreement (Cohen's κ) per form, the matcher's error rates in each direction per form, and accuracies corrected for those errors.

## 8. Item schema

```json
{
  "id": "hist_0001",
  "domain": "History",
  "locality": "india",
  "tier": 2,
  "answer_type": "year",
  "en": "...",
  "hi_dev": "...",
  "hi_rom_natural": "...",
  "hi_rom_std": "...",
  "gold_answer": "1526",
  "gold_variants": ["1526", "१५२६"],
  "numeric_tolerance": null,
  "sources": [
    {"title": "NCERT Class 7 History, Ch. 4", "url": "...", "page": "..."},
    {"title": "...", "url": "..."}
  ],
  "provenance": "ncert_passage",
  "annotators": {"hi_dev_author": "A", "hi_dev_checker": "B", "rom_author": "A"},
  "status": "accepted",
  "notes": ""
}
```

## 9. Workflow

1. Draft candidate (EN + gold + 2 sources) → `candidates.jsonl`
2. Automatic checks: `python code/validate_dataset.py data/candidates.jsonl`
3. Hindi + Romanization by annotator A; independent check by annotator B
4. Gold re-verification by a second person; reject anything disputed
5. Accepted items → `scriptconsist_v1.jsonl`; rejected items kept with reason (reported in the paper)
6. Datasheet (Gebru et al., 2021) written from the logs

## 10. Experimental design: fixes for known critiques of the earlier draft

### 10.1 Quantization confound (4-bit NF4)
Quantization is known to hurt non-Latin-script languages most (Marchisio et al., 2024), so an NF4-only study cannot separate "the model is weak in Devanagari" from "compression broke Devanagari".
- Run at least two models at **bf16 and NF4** on identical items. Add 8-bit if compute allows.
- Report the **precision × script interaction**: if Δ_lang and Δ_script are the same at bf16 and NF4, quantization is not driving the gap; if they shrink at bf16, that is a finding.
- Headline numbers come from bf16 (or full-precision API models). NF4 results are an ablation, never the main claim.

### 10.2 Statistical power
- 600 items (Section 5) instead of 64.
- Script comparisons use paired tests (McNemar) with bootstrap 95% CIs, and Holm correction across the model × script-pair family.
- Each item is asked with **3 prompt paraphrases**; we report mean and spread, so a result cannot hinge on one template.
- Subset analyses (cultural items, self-translation) are pre-declared and only reported inferentially if the subset has ≥ 100 items; smaller subsets are descriptive only.

### 10.3 Realistic Romanization
Three Romanized conditions per item, not one rule-based proxy:
1. `hi_rom_std`: rule-based (reproducible baseline)
2. `hi_rom_natural_{A,B,C}`: typed independently by 3 native speakers on a phone keyboard, autocorrect left **on**, with no scheme given. This captures real spelling variance.
3. Spelling-variance analysis: accuracy spread across the A/B/C versions of the same question = **sensitivity to orthographic noise**.
- Validate naturalness against the Dakshina dataset (native-speaker Romanizations of Hindi): compare spelling-variant distributions of our natural forms against Dakshina's to show they resemble real typing.
- Claims are scoped to "native-typed Romanized Hindi". We do not claim coverage of all social-media text.

### 10.4 Confidence measurement
Letter probability over A–D mostly measures format adherence and position bias (Zheng et al., 2024), especially on out-of-distribution scripts. Instead:
- **Primary task is open-ended short answer** (no option letters), so letter bias cannot occur.
- **Confidence = sampling consistency**: 10 samples at T = 0.7; confidence = share of samples semantically matching the greedy answer. This is format-independent.
- Secondary: length-normalised sequence log-probability of the generated answer string, plus verbalised confidence.
- If an MC variant is kept: average over all cyclic permutations of option order to remove position/letter bias.
- "Overconfidence" is only claimed via calibration metrics computed **per script**: ECE, Brier score, and AUROC of confidence-vs-correctness. Saying "high probability on wrong answers" alone is not enough.

## 11. ScriptConsist-IQ (built 2026-10-23)

Base: L3Cube-IndicQuest (Rohera et al., 2024), 200 parallel EN/HI questions, CC BY-NC-SA 4.0.
Every item was reviewed (`code/build_from_indicquest.py`, decisions in `data/build/indicquest_filtering.csv`).

- **Kept 81 / 200.** Dropped: descriptive/essay 59, multiple valid answers 13, ambiguous 11, multi-part 9, time-sensitive 7, wrong gold 7, contested 4, ill-posed 4, answer/question mismatch 2, unverifiable 2, answer leaked by Hindi translation 1.
- Hindi questions are Google-Translate output (IndicQuest did no human review); a native speaker post-edits them. The unedited text is kept as `hi_dev_mt`, so MT vs post-edited Hindi is itself a comparison.
- `hi_rom_std` = `code/romanize.py` (Aksharamukha IAST + Hindi schwa deletion -> ASCII), regenerated from the post-edited Hindi.
- `hi_rom_natural` = typed on a phone by annotator A (all items) and annotator B (stratified 41-item subset) in the annotation page.
- Short gold answers were extracted from IndicQuest's sentence answers, with English and Devanagari variants.

## 12. ScriptConsist-MK (built 2026-10-23)

Base: Mintaka (Sen et al., COLING 2022), train + test merged = 18,000 questions, Hindi by professional translators, answers linked to Wikidata. CC BY 4.0.
Script: `code/build_from_mintaka.py`; filter counts in `data/build/mintaka_filtering.csv`.

- Filters: keep complexity types generic, superlative, intersection, multihop, ordinal (drop yes/no, comparative, count, difference); entity answers with a Hindi Wikidata label, or dates scored on the year; drop temporal wording, Latin script inside the Hindi, answer leakage, options listed in the question, **implicit US context** ("What state grows potatoes?" reads as an Indian state in Hindi), and **records that can change after 2022** ("best-selling", "highest-grossing", "of all time").
- 3,685 of 18,000 pass. A seeded, stratified sample of 300: about 37 per topic across 8 topics, 40% generic and the rest spread across the complex types.
- A 60-item stratified helper subset is typed by annotator B.
- Mintaka is almost entirely global knowledge. Paired with IndicQuest (India-specific), it gives the locality comparison.

### 12.1 Annotation and review of the 300 (2026-10-26)
- Annotator A typed `hi_rom_natural` for all 300 and checked every gold answer, mostly with sources; the professional Hindi was left unedited. Raw annotations: `data/annotations/annotations_final.jsonl`.
- Annotator corrections: 4 gold answers fixed and 16 items rejected (gold wrong with no clear fix, ambiguous, or unsure).
- Second-pass review (`code/finalize_mintaka.py`, reasons in `data/build/mintaka_review.csv`): 38 more rejected (ambiguous, two valid answers, records changed after 2022, time-sensitive "last"), 7 near-duplicates removed, 2 gold answers corrected, 3 variant lists extended, and 9 Hinglish questions sent back for retyping because they changed the meaning.
- Result: 239 usable items (230 accepted + 9 after retype), 26–34 per topic.
- Filter gaps found in review, to add to the builder for future samples: "last", "most sold", "most viewed", "box office", and present-tense roles ("coach of", "head of").

## 13. ScriptConsist v1: frozen 2026-10-26

`data/scriptconsist_v1.jsonl` (`code/freeze_v1.py`): **296 items** = 238 Mintaka + 58 IndicQuest.
- Mintaka: 8 of 9 meaning-changing Hinglish items were retyped; the 9th (position 213) is rejected.
- IndicQuest: scope limited to the 61 items annotator A completed; 3 rejected (reasons in `data/build/indicquest_review.csv`), 20 not annotated.
- The IndicQuest Devanagari is used **as released** (Google MT, not post-edited); `hi_dev_origin` records this per item. Mintaka Devanagari is the professional translation.
- Locality: 53 India-specific, 243 global.
- Helper subset (annotator B) not collected. The spelling-variance analysis in §10.3 is therefore out of scope for v1 and listed as a limitation.
- **Annotators (final, 2026-10-26):** every `hi_rom_natural` in v1 was typed by the first author (native Hindi speaker), who also confirmed every gold answer. A second native speaker had earlier typed 73 of the items; the first author retyped all of them from scratch. The second speaker's versions are kept in `data/annotations/spelling_variation_pairs.json`. On those 73 pairs the two typists matched exactly only 5 times (7%); mean character similarity was 0.85 and mean word overlap (Jaccard) 0.66.
- **Limitations recorded for the paper:**
  1. Single typist for the evaluated Hinglish: results describe one native speaker's typing style. The 73-item comparison shows how much a second speaker's version would differ, but models are not evaluated on the second version in v1.
  2. Spelling is not normalised within the typist's own work (e.g. "kaun/kon", "kab/kb"); this is deliberate realism, not cleaned.
  3. IndicQuest Devanagari is unedited Google MT.
  4. India-specific items are few (n = 53).

## 14. First model runs and scorer revision (2026-10-27)

- Kaggle (2× T4) runs completed for Qwen2.5-7B, Llama-3.1-8B, Aya-Expanse-8B, Nemotron-4-Mini-Hindi-4B (fp16), Qwen and Llama in NF4, and Gemma-2-9B (NF4, fp32 compute). Gajendra and Airavata first failed to start (an old code version on Kaggle); Airavata then ran with its Tulu format, and Gajendra was re-run with ChatML after a first run in the wrong (Tulu) format was found invalid (kept in `archive/`). 3,771 prompts per run, greedy decoding.
- **Scorer revision before any result was reported.** An audit of the lenient rules found (a) correct Devanagari answers rejected because Hindi spells foreign names in several ways (जेम्स मेडिसन vs मैडिसन, न्यूरेमबर्ग vs नूर्नबर्ग), which biased results against Devanagari, and (b) a few false accepts from subset fuzzy matching (NES for Super NES; "Article 55" for Article 54 via a Devanagari partial match).
- Fix: a token-coverage rule. Every distinctive word of a gold form must appear in the answer, compared on plain spelling and on a consonant skeleton. Descriptor words ("river", "city") and words already in the question are optional, and one word may be missing for 3+ word names. Digits must match exactly. 68 unit tests (`tests/test_score.py`) now cover every failure found in the audit.
- Effect vs the original scorer: Devanagari +3 to +7 points per model; other forms ±1–2 points.
- **Validation:** a blind, stratified sample is judged by the first author in the annotation page, without seeing the scorer's verdict or the model's name. Key: `results/validation/sample_key.jsonl`; built by `code/extend_validation_sample.py`.
  - 300 answers from the five general models: 75 per form, half auto-accepted and half auto-rejected.
  - 40 answers from Airavata and Gajendra (run later; their output styles differ): 10 per form, half auto-accepted.
  - 48 repeats of earlier items (12 per form, half auto-accepted) shown again under new ids at least 90 positions later, to measure the validator's own consistency. There is one validator, so this intra-rater agreement stands in for inter-rater agreement and is reported as such.
  - Reported: Cohen's κ per form; per form, the share of auto-accepted answers the human rejects (false accepts) and of auto-rejected answers the human accepts (missed correct answers), with Wilson CIs. Every accuracy is then corrected as acc_auto × (1 − false-accept rate) + (1 − acc_auto) × missed rate, and the main gaps (natural Hinglish − Devanagari, Devanagari − rule-based Roman) are recomputed under the corrected accuracies and under the worst-case ends of the CIs.

- **Validation result (2026-10-27)** (`results/validation/validation_report.md`, `code/analyze_validation.py`): 331 of 340 answers judged (9 `unsure`, mostly refusals). Agreement 97.6%, κ = 0.952 overall; per form κ 0.93 (English), 0.95 (Devanagari), 0.98 (rule-based Roman), 0.95 (natural Hinglish). False accepts 1/171 (0.6%); missed correct answers 7/160 (4.4%). Five of the seven missed answers are lenient judgment calls (e.g. "The Lord of the Rings" for *The Fellowship of the Ring*), so the true miss rate is if anything lower. Airavata + Gajendra: 38/38 agreement. Validator self-consistency on 48 repeats: 47/48 identical (the one change was wrong → unsure), κ = 1.0 excluding `unsure`.
- Corrected accuracies change by at most 5 points and leave every model ranking unchanged. With the scorer's error-rate uncertainty propagated (20,000 simulations), natural Hinglish > Devanagari holds for all 9 runs (P > 0.99 each); Devanagari > rule-based Roman holds for 6 of 9 runs with P > 0.98 (Llama fp16 and 4-bit, Aya, Nemotron, Gemma, Airavata), and is uncertain for Qwen (fp16 P = 0.97, 4-bit P = 0.97; intervals touch 0) and Gajendra (P = 0.93).
- **The scorer is frozen as validated.** The few errors found (acronyms such as "LDP", paraphrases such as "self-inflicted gunshot" for *suicide*, a year range "1517–1519" accepted for 1519) are reported, not patched, because a patched scorer would no longer be the one this validation measured.
