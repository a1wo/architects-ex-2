# Stage 1 — Baseline Report

**Setup.** 48 Hebrew dev questions (`reference_questions.json`) through bare `deepseek-ai/DeepSeek-V4-Pro` on Nebius Token Factory — no documents. Three system prompts: **default** (provided), **strict** ("answer only if certain, else refuse"), **cite** ("every claim must cite document + page"). Scored by `eval_harness.py`: LLM-as-judge pinned to `deepseek-ai/DeepSeek-V4-Pro`, temperature 0, forced-JSON verdicts; refusals are counted separately, not as hallucinations; hallucination = confident **and** contradicts ground truth.

| metric | default | strict | cite |
|---|---|---|---|
| correct | **35%** | 13% | 31% |
| partial | 2% | 0% | 6% |
| incorrect | 58% | 10% | 42% |
| refusals | 4% | **77%** | 21% |
| **hallucination rate** | **56%** | **8%** | **42%** |
| citation accuracy | 0 (no citations) | 0 (no citations) | 0 (all invented) |
| conversational quality (judged 0-1) | 0.98 | 0.41 | 0.84 |
| latency mean / p95 (ms) | 9292 / 27148 | 2289 / 6362 | 7082 / 17074 |

Correct by difficulty (default): easy 8/16, medium 4/16, hard 5/16. By domain: business/life 67%, health 50%, **travel 0%**, car/mortgage 17%.

## 1. Where does the bare model succeed, and what does that say about its training data?

It succeeds where the answer is **Israeli insurance law or industry-standard practice**, not Harel-specific: the 3-year limitation period (חוק חוזה הביטוח), "join via your insurance agent," beneficiary defaults, proportional premium refunds. These are in the training data because they appear across the public Israeli legal/insurance web. It fails hardest where answers depend on **Harel's specific numbers and service contracts** — travel (0%) and car (17%) hinge on particular service providers, coverage caps, and rider names. The model knows *insurance*; it does not know *Harel's policies*.

## 2. When it's wrong, is it wrong confidently? Which failure is worse?

Almost always confidently: 56% of all default answers are confident contradictions of the ground truth, with fabricated specifics — "עד 12 חודשים" where the policy says 100 days (dev-09), "8% מסכום הביטוח" where the truth is 6,000 ₪ (dev-04), 12,000 ₪ where the cap is 24,000 ₪ (dev-06). The **cite** prompt is the cautionary tale: it *invents* authoritative-looking citations ("פוליסת ביטוח מחזיקי אקדח, סעיף 4.2.1, עמוד 7") pointing at documents/pages that don't exist. For an insurer, a confident wrong answer is far worse than "I don't know": it creates reliance, liability, and regulatory exposure — a customer who is told their earthquake damage is state-compensated doesn't buy the cover. The strict prompt shows the dial exists — hallucinations drop 56%→8% — but at the cost of refusing 77% of everything, including the 23% it actually knew. **Retrieval is the only way to move both numbers at once.**

## 3. A question where we disagree with the judge

`dev-13-car-easy` (keys locked in car — does the service cover break-in?). Ground truth: yes, unconditionally. The model answered "depends on your service rider: covered under כתב שירות DRIVE, not under כתב שירות כבישים" — and the judge scored it **incorrect + confident**, i.e., a hallucination. We'd call it partial-correct: the caveat is reasonable customer-service behavior, and the DRIVE branch matches the ground truth. Implication at scale: an LLM judge anchors on the ground-truth phrasing and punishes legitimate conditional answers, so (a) judged deltas between systems are trustworthy only when large, (b) borderline verdicts need spot-checks, and (c) we should keep the judge model + prompt pinned so this bias at least stays constant across runs.

**Takeaway.** Bare-model ceiling: ~35% relevance, 0% grounded citations, hallucination profile unacceptable for insurance. Stage 2 must (1) beat 35% relevance with retrieval, (2) make citations real (file+page resolvable in the corpus), (3) keep refusals meaningful — refuse only when retrieval genuinely comes up empty.
