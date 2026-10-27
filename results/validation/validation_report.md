# Scorer validation

Blind human judgments of 388 answers: 340 for the scorer check (300 from five general models, 40 from Airavata and Gajendra) and 48 repeats for the validator's self-consistency. One validator (the first author); the scorer's verdict and the model name were hidden.

Verdicts (main set): {'correct': 177, 'wrong': 154, 'unsure': 9}. Median time per judgment: 7 s (interquartile 5–14 s).

## 1. Scorer vs human, per form

| Form | n | Agreement % | Cohen's κ | False accepts (human wrong / scorer correct) | Missed correct (human correct / scorer wrong) |
|---|---|---|---|---|---|
| English | 83 | 96.4 | 0.927 | 0/43 = 0.0% [0.0–8.2] | 3/40 = 7.5% [2.6–19.9] |
| Devanagari | 83 | 97.6 | 0.952 | 0/43 = 0.0% [0.0–8.2] | 2/40 = 5.0% [1.4–16.5] |
| Rule-based Roman | 83 | 98.8 | 0.976 | 1/43 = 2.3% [0.4–12.1] | 0/40 = 0.0% [0.0–8.8] |
| Natural Hinglish | 82 | 97.6 | 0.951 | 0/42 = 0.0% [0.0–8.4] | 2/40 = 5.0% [1.4–16.5] |
| All forms | 331 | 97.6 | 0.952 | 1/171 = 0.6% [0.1–3.2] | 7/160 = 4.4% [2.1–8.8] |

### Sensitivity: `unsure` counted as wrong

| Form | n | Agreement % | Cohen's κ | False accepts (human wrong / scorer correct) | Missed correct (human correct / scorer wrong) |
|---|---|---|---|---|---|
| English | 85 | 96.5 | 0.929 | 0/43 = 0.0% [0.0–8.2] | 3/42 = 7.1% [2.5–19.0] |
| Devanagari | 85 | 97.6 | 0.953 | 0/43 = 0.0% [0.0–8.2] | 2/42 = 4.8% [1.3–15.8] |
| Rule-based Roman | 85 | 98.8 | 0.976 | 1/43 = 2.3% [0.4–12.1] | 0/42 = 0.0% [0.0–8.4] |
| Natural Hinglish | 85 | 96.5 | 0.929 | 1/43 = 2.3% [0.4–12.1] | 2/42 = 4.8% [1.3–15.8] |
| All forms | 340 | 97.4 | 0.947 | 2/172 = 1.2% [0.3–4.1] | 7/168 = 4.2% [2.0–8.3] |

Brackets: 95% Wilson intervals. The sample is half scorer-correct and half scorer-wrong in each form, so raw agreement here is not the scorer's accuracy on the full data; that is estimated in section 3.

### By model group (main set, unsure excluded)

| Group | n | Agreement % | κ |
|---|---|---|---|
| Five general models | 293 | 97.3 | 0.945 |
| Airavata + Gajendra | 38 | 100.0 | 1.000 |

## 2. Validator self-consistency (48 repeated answers)

Same verdict both times: 47/48 (97.9%), counting `unsure` as its own verdict. Excluding pairs with an `unsure`: 47/47, κ = 1.000. Each repeat was shown at least 90 positions (median ≈ 200) after the first showing.

- v020 → v368 (Rule-based Roman): wrong → unsure. Gold: Among Us. Answer: I apologize, but I don't have specific information about which gem had a unique characteristic or wa

## 3. Accuracies corrected for scorer error (%)

corrected = scorer accuracy × (1 − false-accept rate) + (1 − scorer accuracy) × missed-correct rate, with the per-form rates from section 1. Rates are pooled over models.

| Model | English | Devanagari | Rule-based Roman | Natural Hinglish |
|---|---|---|---|---|
| Qwen2.5-7B | 60.7 → **63.6** | 12.4 → **16.8** | 9.1 → **8.9** | 45.7 → **48.4** |
| Llama-3.1-8B | 72.5 → **74.6** | 36.4 → **39.6** | 23.0 → **22.4** | 62.6 → **64.5** |
| Aya-Expanse-8B | 76.8 → **78.5** | 53.4 → **55.7** | 11.1 → **10.9** | 64.0 → **65.8** |
| Nemotron-Hindi-4B | 58.2 → **61.4** | 44.8 → **47.6** | 36.4 → **35.5** | 55.3 → **57.5** |
| Gemma-2-9B (4-bit) | 74.4 → **76.4** | 43.5 → **46.3** | 24.8 → **24.2** | 69.6 → **71.1** |
| Airavata-7B | 32.3 → **37.4** | 11.7 → **16.1** | 6.9 → **6.7** | 25.9 → **29.6** |
| Gajendra-7B | 40.8 → **45.2** | 12.0 → **16.4** | 11.0 → **10.8** | 34.2 → **37.5** |
| Qwen2.5-7B (4-bit) | 56.8 → **60.0** | 10.9 → **15.4** | 8.1 → **7.9** | 43.2 → **46.1** |
| Llama-3.1-8B (4-bit) | 70.2 → **72.4** | 30.0 → **33.5** | 21.3 → **20.8** | 59.2 → **61.3** |

Estimated scorer accuracy on the full data (share of all scored answers where a human would agree), per form, averaged over the nine runs: English 97.0%, Devanagari 96.4%, Rule-based Roman 99.6%, Natural Hinglish 97.6%.

## 4. Do the main gaps survive scorer error? (percentage points)

Worst case: the form expected to be higher gets its lowest plausible accuracy and the other form its highest (ends of the 95% intervals of both error rates).

| Model | Hinglish − Devanagari: scorer | corrected | worst case | Devanagari − rule-based Roman: scorer | corrected | worst case |
|---|---|---|---|---|---|---|
| Qwen2.5-7B | +33.3 | +31.7 | +15.8 | +3.3 | +7.9 | -4.5 |
| Llama-3.1-8B | +26.2 | +24.9 | +11.0 | +13.4 | +17.1 | +4.6 |
| Aya-Expanse-8B | +10.6 | +10.1 | -2.0 | +42.2 | +44.8 | +30.8 |
| Nemotron-Hindi-4B | +10.5 | +9.9 | -2.6 | +8.4 | +12.1 | +0.1 |
| Gemma-2-9B (4-bit) | +26.1 | +24.8 | +11.4 | +18.7 | +22.1 | +9.4 |
| Airavata-7B | +14.2 | +13.5 | -1.5 | +4.8 | +9.4 | -3.0 |
| Gajendra-7B | +22.2 | +21.1 | +5.7 | +1.0 | +5.7 | -6.5 |
| Qwen2.5-7B (4-bit) | +32.3 | +30.7 | +14.8 | +2.8 | +7.5 | -4.9 |
| Llama-3.1-8B (4-bit) | +29.3 | +27.8 | +13.3 | +8.7 | +12.7 | +0.4 |

Extreme bound: Hinglish > Devanagari holds for 6/9 runs; Devanagari > rule-based Roman for 5/9. This bound puts both forms' error rates at opposite ends of their intervals at once, and a form with 0 observed errors in ~40 answers still gets an 8% error rate, so it is very conservative.

### Uncertainty in the scorer's error rates, propagated (20,000 simulations)

Each simulation draws every form's two error rates from what the validation sample allows (Beta posterior, uniform prior) and recomputes the corrected gap. Shown: median gap, 95% range, and the share of simulations where the gap stays above zero.

| Model | Hinglish − Devanagari | P(> 0) | Devanagari − rule-based Roman | P(> 0) |
|---|---|---|---|---|
| Qwen2.5-7B | +30.6 [+21.0, +37.7] | 1.000 | +7.2 [-0.2, +16.3] | 0.973 |
| Llama-3.1-8B | +24.0 [+16.5, +29.7] | 1.000 | +16.2 [+9.8, +23.1] | 1.000 |
| Aya-Expanse-8B | +9.7 [+3.4, +15.1] | 0.997 | +42.9 [+36.0, +48.3] | 1.000 |
| Nemotron-Hindi-4B | +9.6 [+2.8, +15.6] | 0.996 | +11.4 [+5.6, +17.7] | 1.000 |
| Gemma-2-9B (4-bit) | +23.9 [+16.8, +29.1] | 1.000 | +21.0 [+14.8, +27.3] | 1.000 |
| Airavata-7B | +13.1 [+3.4, +21.6] | 0.994 | +8.7 [+1.2, +17.8] | 0.986 |
| Gajendra-7B | +20.4 [+10.8, +28.3] | 1.000 | +5.1 [-2.2, +14.2] | 0.932 |
| Qwen2.5-7B (4-bit) | +29.6 [+20.0, +37.0] | 1.000 | +6.8 [-0.7, +16.0] | 0.965 |
| Llama-3.1-8B (4-bit) | +26.8 [+18.8, +32.7] | 1.000 | +11.9 [+5.4, +19.3] | 0.999 |

This covers uncertainty about the scorer only. Uncertainty from the choice of questions is in `results/analysis/summary.md` (bootstrap over questions).

## 5. Every disagreement and `unsure`

| id | Form | Scorer | Human | Gold | Answer (start) |
|---|---|---|---|---|---|
| v022 | English | wrong | correct | Liberal Democratic Party | LDP. |
| v197 | English | wrong | correct | Greece | Ancient Athens |
| v218 | English | wrong | correct | The Fellowship of the Ring | The Lord of the Rings. |
| v117 | Devanagari | wrong | correct | Vice President of the United States | व्हिसपर प्रेसिडेंट |
| v164 | Devanagari | wrong | correct | Mediterranean Sea | एजियन समुद्र |
| v055 | Natural Hinglish | wrong | correct | suicide | Ernest Hemingway, a renowned American author, died in 1961 due to a self-inflict |
| v146 | Natural Hinglish | wrong | correct | Satopanth Glacier | Bhagirathi glaciers |
| v122 | Rule-based Roman | correct | wrong | 1519 | 67 sal ki umra men Mona Lisa aur Da Vinci (jisne uska chitra banaya) ka nishaan  |
| v157 | English | wrong | unsure | Ibrahim Adil Shah II | I couldn't find any information on the book 'Kitab-e-Navras'. |
| v177 | English | wrong | unsure | 16,110 rupees | I am unable to verify the construction cost of Shaniwar Wada. |
| v231 | Devanagari | wrong | unsure | Wright brothers | किटी हॉक पर सबसे पहले अल और जेम्स हॉक भाइयों ने उड� |
| v234 | Devanagari | wrong | unsure | Super Nintendo Entertainment System | निंटेंडो एंटरटेनमेंट सिस्टम (NES) |
| v219 | Natural Hinglish | wrong | unsure | Spain | Columbia ko 1813 mein Venezuela se swatantra mili, lekin technically Colombia ne |
| v338 | Natural Hinglish | correct | unsure | 1993 | 1991, 1993, 1998 |
| v340 | Natural Hinglish | wrong | unsure | Donald Trump | naam, jagah, title ya saal |
| v032 | Rule-based Roman | wrong | unsure | Sedimentary rock | जीवश्म सामान्यतः चट्टन में पाए जाते हैं। |
| v190 | Rule-based Roman | wrong | unsure | Majhi Janmathep | Savarkar ki atmakatha ka nam "Mere Swaraj" tha. |
