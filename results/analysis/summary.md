# ScriptConsist v1: results

Questions: 296 (each asked with 3 prompt wordings). Accuracy is averaged over wordings per question;
95% CIs are bootstrap over questions; p-values are paired permutation tests, Holm-corrected per table.

## 1. Accuracy by model and question form (%)

| Model | English | Devanagari | Romanized (rule-based) | Hinglish (natural) | Hinglish (2nd typist) |
|---|---|---|---|---|---|
| Qwen2.5-7B | 60.7 [55.5–65.8] | 12.4 [9.2–15.8] | 9.1 [6.6–11.7] | 45.7 [40.9–50.6] | 44.3 [34.2–54.8] |
| Llama-3.1-8B | 72.5 [67.9–76.9] | 36.4 [31.4–41.3] | 23.0 [18.9–27.3] | 62.6 [57.6–67.5] | 53.4 [43.4–63.9] |
| Aya-Expanse-8B | 76.8 [72.2–81.3] | 53.4 [48.3–58.5] | 11.2 [8.7–13.9] | 64.0 [59.2–68.6] | 53.9 [43.8–63.9] |
| Nemotron-Hindi-4B | 58.2 [53.4–63.2] | 44.8 [39.9–50.0] | 36.4 [31.6–41.0] | 55.3 [50.2–60.4] | 49.3 [39.7–58.9] |
| Gemma-2-9B (4-bit) | 74.4 [69.7–79.2] | 43.5 [38.2–48.9] | 24.8 [20.6–29.4] | 69.6 [64.6–74.3] | 61.6 [51.1–71.7] |
| Airavata-7B | 32.3 [27.4–37.3] | 11.7 [8.7–15.1] | 6.9 [4.8–9.1] | 25.9 [21.6–30.4] | 26.0 [17.3–35.2] |
| Gajendra-7B | 40.8 [35.8–45.8] | 12.0 [9.1–15.2] | 11.0 [8.5–14.0] | 34.2 [29.6–39.0] | 33.3 [24.2–42.9] |
| Qwen2.5-7B (4-bit) | 56.8 [51.5–61.8] | 10.9 [7.9–14.2] | 8.1 [5.7–10.7] | 43.2 [38.3–48.1] | 45.2 [35.2–55.2] |
| Llama-3.1-8B (4-bit) | 70.2 [65.4–74.8] | 29.9 [25.3–34.7] | 21.3 [17.3–25.4] | 59.2 [54.3–64.1] | 52.5 [42.5–63.0] |

## 2. Paired gaps (percentage points, A − B)

| Model | language gap (EN - Devanagari) | script gap (Devanagari - rule-based Roman) | code-mixing gain (natural Hinglish - rule-based Roman) | natural Hinglish - Devanagari | EN - natural Hinglish |
|---|---|---|---|---|---|
| Qwen2.5-7B | +48.3* [+43.4, +53.4] | +3.3 [+0.0, +6.6] | +36.6* [+32.1, +41.3] | +33.3* [+28.5, +38.2] | +15.0* [+11.2, +18.9] |
| Llama-3.1-8B | +36.1* [+30.7, +41.4] | +13.4* [+8.1, +18.7] | +39.6* [+34.4, +45.1] | +26.2* [+21.2, +31.6] | +9.9* [+6.4, +13.5] |
| Aya-Expanse-8B | +23.4* [+18.4, +28.6] | +42.2* [+37.3, +47.1] | +52.8* [+48.3, +57.3] | +10.6* [+6.1, +15.2] | +12.8* [+9.1, +16.7] |
| Nemotron-Hindi-4B | +13.4* [+8.7, +18.2] | +8.5* [+3.9, +13.1] | +18.9* [+14.3, +23.6] | +10.5* [+6.0, +15.1] | +2.9 [-0.7, +6.5] |
| Gemma-2-9B (4-bit) | +31.0* [+25.4, +36.4] | +18.7* [+13.6, +23.9] | +44.8* [+39.5, +49.9] | +26.1* [+20.9, +31.3] | +4.8* [+1.6, +8.1] |
| Airavata-7B | +20.6* [+15.9, +25.4] | +4.8* [+1.7, +8.0] | +19.0* [+14.9, +23.2] | +14.2* [+9.8, +18.6] | +6.4* [+2.8, +10.1] |
| Gajendra-7B | +28.7* [+23.5, +33.8] | +1.0 [-1.9, +4.0] | +23.2* [+19.0, +27.5] | +22.2* [+17.6, +26.9] | +6.5* [+2.9, +10.1] |

\* Holm-adjusted p < 0.05.

## 3. India-specific vs global questions (%)

| Model | Locality | n | English | Devanagari | Rule-based Roman | Natural Hinglish | EN − Hinglish | EN − Devanagari |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-7B | india | 53 | 44.0 | 11.9 | 11.3 | 34.6 | +9.4 | +32.1 |
| Qwen2.5-7B | global | 243 | 64.3 | 12.5 | 8.6 | 48.1 | +16.2 | +51.8 |
| Llama-3.1-8B | india | 53 | 54.7 | 40.9 | 34.6 | 52.8 | +1.9 | +13.8 |
| Llama-3.1-8B | global | 243 | 76.4 | 35.4 | 20.4 | 64.8 | +11.7 | +41.0 |
| Aya-Expanse-8B | india | 53 | 38.4 | 33.3 | 11.9 | 28.3 | +10.1 | +5.0 |
| Aya-Expanse-8B | global | 243 | 85.2 | 57.8 | 11.0 | 71.7 | +13.5 | +27.4 |
| Nemotron-Hindi-4B | india | 53 | 48.4 | 52.2 | 49.1 | 52.2 | -3.8 | -3.8 |
| Nemotron-Hindi-4B | global | 243 | 60.4 | 43.2 | 33.6 | 56.0 | +4.4 | +17.2 |
| Gemma-2-9B (4-bit) | india | 53 | 62.9 | 47.8 | 41.5 | 59.1 | +3.8 | +15.1 |
| Gemma-2-9B (4-bit) | global | 243 | 77.0 | 42.5 | 21.1 | 71.9 | +5.1 | +34.4 |
| Airavata-7B | india | 53 | 18.2 | 5.7 | 3.1 | 18.9 | -0.6 | +12.6 |
| Airavata-7B | global | 243 | 35.4 | 13.0 | 7.7 | 27.4 | +8.0 | +22.4 |
| Gajendra-7B | india | 53 | 23.9 | 6.9 | 8.8 | 22.0 | +1.9 | +17.0 |
| Gajendra-7B | global | 243 | 44.4 | 13.2 | 11.5 | 36.9 | +7.5 | +31.3 |

## 4. Quantization (fp16 − 4-bit NF4, percentage points)

| Model | Form / contrast | fp16 − nf4 | 95% CI | Holm p |
|---|---|---|---|---|
| Qwen2.5-7B-Instruct | en | +3.9 | [+1.6, +6.4] | 0.0154 |
| Qwen2.5-7B-Instruct | hi_dev | +1.5 | [-0.6, +3.5] | 0.823 |
| Qwen2.5-7B-Instruct | hi_rom_std | +1.0 | [-0.9, +2.8] | 1 |
| Qwen2.5-7B-Instruct | hi_rom_natural | +2.5 | [-0.3, +5.4] | 0.811 |
| Qwen2.5-7B-Instruct | extra loss vs EN: hi_dev | -2.5 | [-5.4, +0.3] | 0.811 |
| Qwen2.5-7B-Instruct | extra loss vs EN: hi_rom_natural | -1.5 | [-5.1, +2.0] | 1 |
| Llama-3.1-8B-Instruct | en | +2.4 | [-0.3, +5.1] | 0.811 |
| Llama-3.1-8B-Instruct | hi_dev | +6.4 | [+3.3, +9.7] | 0.0012 |
| Llama-3.1-8B-Instruct | hi_rom_std | +1.7 | [-0.6, +3.9] | 0.823 |
| Llama-3.1-8B-Instruct | hi_rom_natural | +3.4 | [+0.8, +6.0] | 0.143 |
| Llama-3.1-8B-Instruct | extra loss vs EN: hi_dev | +4.0 | [+0.1, +8.2] | 0.536 |
| Llama-3.1-8B-Instruct | extra loss vs EN: hi_rom_natural | +1.0 | [-2.4, +4.4] | 1 |

## 5. Same questions, two typists (n = 73)

| Model | First author | Second typist | Diff | 95% CI | Holm p | Mean per-question change |
|---|---|---|---|---|---|---|
| Qwen2.5-7B | 44.3 | 44.3 | -0.0 | [-3.6, +3.6] | 1 | 6.4 |
| Llama-3.1-8B | 53.9 | 53.4 | +0.5 | [-4.6, +5.5] | 1 | 7.8 |
| Aya-Expanse-8B | 56.2 | 53.9 | +2.3 | [-2.3, +7.3] | 1 | 10.5 |
| Nemotron-Hindi-4B | 50.2 | 49.3 | +0.9 | [-3.6, +5.5] | 1 | 10.1 |
| Gemma-2-9B (4-bit) | 64.8 | 61.6 | +3.2 | [+0.0, +6.9] | 0.673 | 5.9 |
| Airavata-7B | 37.0 | 26.0 | +11.0 | [+5.9, +16.9] | 0.0007 | 12.8 |
| Gajendra-7B | 37.0 | 33.3 | +3.6 | [-0.9, +8.2] | 0.838 | 9.1 |

## 6. Prompt-wording sensitivity (range of accuracy across the 3 wordings, points)

| Model | English | Devanagari | Romanized (rule-based) | Hinglish (natural) | Hinglish (2nd typist) |
|---|---|---|---|---|---|
| Qwen2.5-7B | 3.4 | 3.7 | 5.7 | 1.4 | 8.2 |
| Llama-3.1-8B | 4.0 | 1.0 | 3.7 | 6.8 | 11.0 |
| Aya-Expanse-8B | 1.4 | 3.0 | 12.8 | 4.7 | 16.4 |
| Nemotron-Hindi-4B | 5.7 | 1.4 | 6.8 | 6.4 | 6.9 |
| Gemma-2-9B (4-bit) | 1.0 | 1.4 | 2.4 | 2.0 | 5.5 |
| Airavata-7B | 1.0 | 3.7 | 2.0 | 2.4 | 5.5 |
| Gajendra-7B | 5.1 | 4.4 | 4.4 | 4.4 | 2.7 |

## 7. Script of the model's answer (% of answers containing it)

| Model | Question form | Devanagari | Latin only | Chinese/Japanese | Name placeholder (NAME_1) |
|---|---|---|---|---|---|
| Qwen2.5-7B | English | 0.0 | 80.9 | 0.2 | 0.0 |
| Qwen2.5-7B | Devanagari | 72.3 | 6.9 | 5.1 | 0.0 |
| Qwen2.5-7B | Romanized (rule-based) | 23.9 | 68.4 | 3.5 | 0.0 |
| Qwen2.5-7B | Hinglish (natural) | 1.5 | 76.2 | 3.4 | 0.0 |
| Llama-3.1-8B | English | 0.0 | 83.8 | 0.0 | 0.0 |
| Llama-3.1-8B | Devanagari | 90.8 | 0.0 | 0.0 | 0.0 |
| Llama-3.1-8B | Romanized (rule-based) | 0.0 | 99.7 | 0.0 | 0.0 |
| Llama-3.1-8B | Hinglish (natural) | 0.0 | 90.6 | 0.0 | 0.0 |
| Aya-Expanse-8B | English | 0.0 | 80.6 | 0.0 | 0.0 |
| Aya-Expanse-8B | Devanagari | 82.9 | 1.7 | 0.0 | 0.0 |
| Aya-Expanse-8B | Romanized (rule-based) | 77.7 | 19.5 | 0.0 | 0.0 |
| Aya-Expanse-8B | Hinglish (natural) | 28.4 | 64.9 | 0.1 | 0.0 |
| Nemotron-Hindi-4B | English | 0.1 | 87.7 | 0.0 | 0.0 |
| Nemotron-Hindi-4B | Devanagari | 92.6 | 0.0 | 0.0 | 0.0 |
| Nemotron-Hindi-4B | Romanized (rule-based) | 1.4 | 95.8 | 0.0 | 0.0 |
| Nemotron-Hindi-4B | Hinglish (natural) | 0.7 | 95.4 | 0.0 | 0.0 |
| Gemma-2-9B (4-bit) | English | 0.0 | 78.9 | 0.0 | 0.0 |
| Gemma-2-9B (4-bit) | Devanagari | 77.8 | 0.7 | 0.0 | 0.0 |
| Gemma-2-9B (4-bit) | Romanized (rule-based) | 9.6 | 66.4 | 0.0 | 0.0 |
| Gemma-2-9B (4-bit) | Hinglish (natural) | 1.8 | 76.0 | 0.0 | 0.0 |
| Airavata-7B | English | 0.0 | 80.3 | 0.0 | 3.0 |
| Airavata-7B | Devanagari | 82.7 | 0.0 | 0.0 | 1.4 |
| Airavata-7B | Romanized (rule-based) | 1.7 | 86.0 | 0.0 | 2.6 |
| Airavata-7B | Hinglish (natural) | 0.3 | 88.6 | 0.0 | 5.4 |
| Gajendra-7B | English | 0.9 | 78.3 | 0.0 | 3.5 |
| Gajendra-7B | Devanagari | 91.7 | 0.1 | 0.0 | 5.4 |
| Gajendra-7B | Romanized (rule-based) | 1.9 | 80.4 | 0.0 | 1.6 |
| Gajendra-7B | Hinglish (natural) | 1.6 | 82.0 | 0.1 | 1.5 |

## 8. Code-mixing

Mean share of words in the natural Hinglish question taken from the English question: 43.9% (median 44.4%).

| Model | Spearman ρ: English share vs (Hinglish − rule-based) gain | p | ρ: English share vs Hinglish accuracy | p |
|---|---|---|---|---|
| Qwen2.5-7B | -0.004 | 0.941 | -0.062 | 0.29 |
| Llama-3.1-8B | +0.080 | 0.168 | +0.004 | 0.949 |
| Aya-Expanse-8B | -0.012 | 0.831 | -0.031 | 0.591 |
| Nemotron-Hindi-4B | -0.087 | 0.137 | -0.116 | 0.0465 |
| Gemma-2-9B (4-bit) | -0.023 | 0.699 | -0.068 | 0.244 |
| Airavata-7B | +0.077 | 0.185 | +0.046 | 0.426 |
| Gajendra-7B | -0.053 | 0.36 | -0.068 | 0.242 |

## 9. Names kept in English spelling (exploratory)

278 questions contain capitalised names or titles; the natural Hinglish keeps all of them in English spelling in 227 (82%), some in 51.

| Model | Outcome | Gain, all names kept | Gain, some changed | Spearman ρ (share kept vs gain) | Holm p |
|---|---|---|---|---|---|
| Qwen2.5-7B | natural - rule-based Roman | +37.9 | +34.0 | +0.037 | 1 |
| Qwen2.5-7B | natural - Devanagari | +33.8 | +33.3 | +0.020 | 1 |
| Llama-3.1-8B | natural - rule-based Roman | +40.5 | +35.9 | +0.050 | 1 |
| Llama-3.1-8B | natural - Devanagari | +28.6 | +16.3 | +0.114 | 0.758 |
| Aya-Expanse-8B | natural - rule-based Roman | +55.8 | +47.1 | +0.078 | 1 |
| Aya-Expanse-8B | natural - Devanagari | +14.2 | +5.2 | +0.069 | 1 |
| Nemotron-Hindi-4B | natural - rule-based Roman | +20.7 | +13.1 | +0.068 | 1 |
| Nemotron-Hindi-4B | natural - Devanagari | +11.9 | +5.2 | +0.074 | 1 |
| Gemma-2-9B (4-bit) | natural - rule-based Roman | +47.4 | +35.3 | +0.111 | 0.778 |
| Gemma-2-9B (4-bit) | natural - Devanagari | +29.5 | +11.8 | +0.161 | 0.102 |
| Airavata-7B | natural - rule-based Roman | +18.4 | +26.1 | -0.101 | 1 |
| Airavata-7B | natural - Devanagari | +13.7 | +19.6 | -0.018 | 1 |
| Gajendra-7B | natural - rule-based Roman | +23.9 | +21.6 | +0.020 | 1 |
| Gajendra-7B | natural - Devanagari | +24.8 | +13.7 | +0.082 | 1 |

