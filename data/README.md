# ScriptConsist v1: data card

**File:** `scriptconsist_v1.jsonl`, 296 factual questions, one JSON object per line.
**Licence:** CC BY-NC-SA 4.0 (derived from Mintaka, CC BY 4.0, and L3Cube-IndicQuest, CC BY-NC-SA 4.0).

## What each item contains

| Field | Meaning |
|---|---|
| `id` | `mk_…` (from Mintaka) or `iq_…` (from IndicQuest) |
| `source` | `mintaka` or `indicquest` |
| `domain` | History, Geography, Politics, Books, Movies, Music, Sports, Video Games, Economics, Literature |
| `locality` | `india` (53 items, all from IndicQuest) or `global` (243) |
| `answer_type` | `entity` (223), `year` (67), `number` (6) |
| `en` | English question, as in the source dataset |
| `hi_dev` | Hindi in Devanagari, unedited: Mintaka's professional translation, or IndicQuest's released machine translation (`hi_dev_origin` says which) |
| `hi_rom_std` | Rule-based romanization of `hi_dev` (`code/romanize.py`: Aksharamukha IAST, Hindi schwa deletion, ASCII). Same words, Roman script |
| `hi_rom_natural` | Hinglish typed on a phone by the author, a native Hindi speaker, with English words used freely and no transliteration scheme |
| `gold_answer`, `gold_variants` | The answer and accepted variants (English, Devanagari, common spellings) |
| `sources` | Where the question and answer come from |
| `notes` | Gold corrections and retyping notes |

## How it was built

1. **Mintaka** (train + test, 18,000 questions) filtered to 3,685 with a single, stable, non-guessable entity or year answer (`code/build_from_mintaka.py`, counts in `build/mintaka_filtering.csv`); a seeded stratified sample of 300.
2. **IndicQuest** (200 pairs) reviewed by hand; 81 kept (`code/build_from_indicquest.py`, reasons in `build/indicquest_filtering.csv`).
3. **Annotation** in `annotation/index.html`: the author typed every Hinglish question and checked every gold answer, mostly with a source.
4. **Review** (`code/finalize_mintaka.py`, `code/freeze_v1.py`): 62 Mintaka items rejected (ambiguous, two valid answers, records that changed after 2022, near-duplicates); 3 IndicQuest items rejected; 6 gold answers corrected. Every rejection and its reason is in `build/mintaka_review.csv` and `build/indicquest_review.csv`.

## Other files

- `annotations/annotations_final.jsonl`: raw annotation records (Hinglish, answer checks, sources, time taken).
- `annotations/spelling_variation_pairs.json`: 73 questions typed by a second native speaker before the author retyped them; used to measure the effect of the typist. Only 5 of 73 match exactly.
- `raw/`: the untouched source datasets.

## Known limitations

- All evaluated Hinglish comes from one typist.
- The Devanagari is unedited; Mintaka's translation has occasional spelling errors and IndicQuest's is machine translation.
- India-specific questions are few (53) and all come from IndicQuest, so locality and source are confounded.
- Facts were checked as of October 2026.
