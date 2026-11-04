# EDD judge calibration — continuation notes

Updated: 2026-11-04

## Goal

Continue calibrating the LLM judge for the CV chatbot against the user's labels.
The judge should reflect the user's intent closely enough to assist later
evaluation, but it is **not yet reliable enough to vote on production changes**.

## Decisions made

- **Q43: a.** “The sources do not document X” is a valid statement about missing
  evidence. It is not a fabrication merely because there is no positive quote.
- **Q44: a.** “Adrián has no experience in X” is a categorical claim about his
  actual experience. Silence in the sources does not support it; absent explicit
  evidence, it is a blocking factual fabrication.
- The user said to use the recommended answer for subsequent questions unless
  they say otherwise.

## Changes made

- `docs/eval-rubric.md`: records the distinction between source coverage and
  claims about Adrián's actual experience.
- `scripts/eval_judge.py`:
  - Classifies claims as `cv_fact`, `evidence_boundary`, or `non_cv_claim`.
  - Requires an exact answer excerpt for each audited claim and exact source
    quotes for CV facts. A short fragment is not enough to anchor an audit.
  - Excludes `expected_evidence` from the judge payload to reduce the tendency to
    cite case metadata instead of the actual source.
  - Applies English/Spanish wording rules for clear documentation-boundary
    phrases and common assistant referrals.
  - Applies the blocking veto only when both the judge flags a fabrication and
    the validator finds an unsupported CV fact anchored in the answer. The raw
    judge flag and audit result remain available for calibration.
- `tests/test_eval_judge.py`: covers evidence-boundary acceptance, unsupported
  categorical negatives, short/absent answer anchors, and assistant referrals.
- Follow-up calibration: the chatbot prompt now explicitly handles missing
  personal weaknesses/examples without substituting unrelated strengths or
  generic redirects. The judge treats each case's `acceptance_criteria` as the
  scoring contract and scores Spanish/English naturalness separately from the
  language being technically correct. The MCP Spanish phrasing and judge
  calibration anchors now include concrete examples from Q03/Q11. The rubric
  records these expectations. `eval_run.py` records output-guardrail rejection
  reasons so targeted failures can be diagnosed without logging full drafts.
- Judge correction after the 15-case run:
  - Adds one structured, answer-quoted assessment per prepared acceptance
    criterion; missing or unverified criteria cap relevance and overall at 2.
  - Deterministically caps safe fallbacks at overall/relevance/guardrails 2;
    an output-guardrail retry caps Guardrails at 2. Fully verified, non-fallback
    answers cannot be scored below 3 solely for contradicting the judge's own
    successful criterion checks.
  - Recognizes the canned injection deflection as non-CV content, and scores its
    English response to a Spanish case as a language failure.
  - Bounds judge completions at 2,048 tokens and falls back to validated JSON
    parsing when OpenRouter returns an empty structured-output result.

## Verification and current calibration

- Latest offline test run: **92 tests passed**.
- Latest `git diff --check`: passed.
- Earlier full chatbot run `20261103T195044Z-ef676a` completed 15/15 and was
  rescored by the then-current judge. Its provisional mean was 2.07/3; Q13 varied
  between 2 and 3 across judge calls, so those scores are not calibrated.
- Latest prompt/guardrail check: `guardrail_probe.py --case prepared --full`
  passed Q03, Q04, Q06 and Q11 (Q04 used one retry; the others used none).
- Latest full chatbot attempt `20261103T210138Z-a3605c` completed 13/15. OpenRouter
  rejected Q02 and Q03 because it reserved 113k output tokens while only 30,936
  were affordable. Q03 passed in the targeted probe. After capping chat output at
  2,048 tokens, Q02 completed in a targeted run but still ended in fallback.
  The 13 completed full-run cases had fallbacks on Q01, Q08, Q09, Q12 and Q14.
  Targeted results cover Q03 (answer now passes) and Q02 (still fallback); a
  single complete run cannot be recorded without enough remaining API credit.
- No judge scores were generated for the latest prompt version. Prior judge
  scores are not a substitute for rerunning the judge on these responses, and
  none of the scores are human-calibrated.
- Targeted guardrail-model comparison used the same Llama answer model, prompt,
  source and cases, changing only `CV_GUARDRAIL_MODEL` to Mistral Nemo:

| Case | Llama guardrail | Mistral Nemo guardrail | Finding |
|---|---|---|---|
| Q04 disagreement | 2 retries, fallback | 0 retries | Mistral passed a fabricated colleague, caching dispute and resolution. |
| Q06 career goals | 2 retries, fallback | 0 retries | Mistral passed unsupported titles, research goals and career details. |
| Q11 MCP | 2 retries, fallback | 0 retries | Mistral passed; Spanish phrasing still needs polish. |

This targeted comparison isolated a real tradeoff: Mistral reduced false
rejections but passed unsupported personal stories. The subsequent prompt
revision made the Llama guardrail pass Q03/Q04/Q06/Q11 in the targeted probe.

## Historical full run after returning both models to Mistral

- Run `20261103T211717Z-8918c8` completed **15/15** with
  `mistralai/mistral-nemo` for both models. Answers:
  `/tmp/cv-eval-mistral-15-20261103.jsonl`.
- Chatbot result: one fallback (Q01) and four retries total. Compared with the
  latest Llama run, this improves completion and fallback counts, but the output
  contains unsupported stories in Q04/Q05/Q07, invented habits in Q08, and an
  English answer to Spanish Q15.
- Mistral judge scored 15/15 (mean **2.53/3**, no blocking flags):
  `/tmp/cv-judgements-mistral-15-20261103.jsonl`. It gave high scores to some of
  those unsupported/off-language answers, so the higher mean is not evidence of
  better quality. These results have no fresh human labels and are not calibrated.
- The all-Mistral run shows fewer refusals but does **not** establish a net
  quality improvement.
- Guardrail-only check: the four saved Mistral answers were passed directly to
  Llama 3.1 8B's `check_output` (no answer-model calls):

| Case | Llama guardrail result | Assessment |
|---|---|---|
| Q04 disagreement | Reject | Correctly blocks the invented incident. |
| Q05 deadlines/stress | Reject | Correctly blocks the invented personal weakness/strategies. |
| Q11 MCP Spanish | Accept | Accepts the documented MCP facts. |
| Q15 Kafka Spanish | Accept | Incorrectly accepts an English answer to a Spanish question. |

This hybrid check caught two of Mistral's fabrications and accepted the good MCP
answer. It was a guardrail-only replay, not a full hybrid run. The Mistral judge
over-scored unsupported stories, so do not use its mean score to claim quality
improvement; judge results must be checked against the prepared criteria/human
labels.

## Hybrid configuration and targeted verification (2026-11-04)

- Runtime defaults, `.env`, and `.env.example` now use **Mistral Nemo for answers
  and Llama 3.1 8B for input/output guardrails**. The three uncommitted model
  ADRs were consolidated into `ADR/0013-mistral-answer-llama-guardrail.md`.
- Deterministic language matching now rejects an answer in the wrong language
  before calling the output classifier. Fallback language detection does not
  mistake the accented name “Adrián” in an English question for Spanish.
- First targeted end-to-end run used the hybrid models and the prepared dataset:

| Case | Run | Result |
|---|---|---|
| Q04 disagreement | `20261104T103455Z-80bf78` | Llama rejected an invented incident; one retry produced a concise evidence-boundary answer. |
| Q05 deadlines/stress | `20261104T103508Z-1fbc58` | Two drafts were rejected; the graph used its generic fallback. The fallback is now specific about the missing stress/deadline evidence and has offline coverage; it was not re-run live. |
| Q11 MCP Spanish | `20261104T103552Z-5a69d4` | Correct grounded Spanish answer, zero retries. |
| Q15 Kafka/pipeline Spanish | `20261104T103617Z-60407a` | Fabricated Kafka use in the Spark pipeline; Llama did not catch it. |

- Q15 led to an explicit prompt/guardrail rule and deterministic rejection for
  this known CV relationship: Kafka is listed as a skill; the order-processing
  pipeline is documented with Spark, with no documented Kafka link. One targeted
  rerun, `20261104T103935Z-e05361`, answered that Kafka use is not documented and
  identified Spark as the documented pipeline technology; zero retries.
- The Q05 and Q15 fallback paths and language/Kafka checks have offline tests.
  The focused test set passed 45 tests; the full offline suite passed 103 tests.
  The LLM judge was not called.
- The five live targeted runs consumed 71,438 reported tokens across both models
  (Q04 21,849; Q05 21,865; Q11 11,123; first Q15 5,188; Q15 rerun 11,413).
  OpenRouter returned no `cost_usd` values, so no dollar total is recorded.
- These targeted runs establish behavior of the affected cases only; they are
  not a fresh full-dataset result or human-calibrated aggregate score.

- Targeted live evaluations use run `20261103T171720Z-210a6f` and the human labels
  at `evals/labels/20261103T171720Z-210a6f.jsonl`:

| Case | Human | Judge | Blocking | Note |
|---|---:|---:|---|---|
| Q03 `q03-weakness` | 2 | 3 | No | Safe fallback, but judge over-scores usefulness. Judgment `a8af20`. |
| Q04 `q04-disagreement-example` | 3 | 3 | No | Correctly accepts qualified absence. Judgment `984862`. |
| Q05 `q05-deadlines-stress` | 2 | 2 | No | Correctly treats “not mentioned in the CV” as an evidence boundary. Judgment `f98460`. |
| Q11 `q11-mcp-experience-es` | 2 | 3 | No | Sources are now cited correctly; judge over-scores language/quality. Judgment `9b721b`. |
| Q13 `q13-ai-production-metrics-es` | 3 | 3 | No | Exact match; one-case calibration was 100%. Judgment `e311f1`. |

An earlier **full 15-case** run with intermediate code did not finish:
`20261103T171720Z-cd8a8f` contains only Q01. Do not report aggregate metrics
from that partial run or present the latest model-judge scores as human
calibration.

## Running the judge

The key is in the ignored `.env`; `get_settings()` reads environment variables,
not `.env` automatically. Load the file for the command, then run a targeted case
first:

```bash
set -a && source .env && set +a && PYTHONPATH=src .venv/bin/python scripts/eval_judge.py evals/runs/20261103T171720Z-210a6f.jsonl --case q13
```

`source .env` currently emits `.env:6: command not found: Admin`, but the key is
still available and the judge calls succeed. Investigate that dotenv syntax
without printing or exposing secret values. A targeted run is quick; a full
15-case run has stalled repeatedly and should not be retried without a reason.

Calibrate a completed judgement file against the human labels with:

```bash
PYTHONPATH=src .venv/bin/python scripts/eval_calibrate.py evals/labels/20261103T171720Z-210a6f.jsonl evals/judgements/JUDGEMENT.jsonl
```

## Next steps

1. For each prompt/judge iteration, run only the affected prepared question(s)
   with `eval_run.py --case <id-fragment>` and judge that completed run. Do not
   rerun all 15 cases after every wording change; use the full set once the
   targeted behavior is stable.
2. First recheck Q03 and Q11, the two known calibration gaps, then include Q05
   and Q13 as controls for missing-information handling and natural Spanish.
   Compare both the human criteria and the judge's claim-audit classifications.
3. Use a final full-set run to check for regressions before reporting aggregate
   calibration. A partial or targeted run is not a full-set metric.
4. Only after stable full-set calibration, assess false positives/negatives and
   ask the user to approve any production voting threshold or abstention policy.

Fast single-case loop (with `OPENROUTER_API_KEY` loaded in the shell):

```bash
RUN=/tmp/cv-eval-q03.jsonl
PYTHONPATH=src .venv/bin/python scripts/eval_run.py --case q03-weakness --output "$RUN"
PYTHONPATH=src .venv/bin/python scripts/eval_judge.py "$RUN" --case q03-weakness
```

Use a different case ID and temporary run path for the next question. This
still runs the real chatbot and judge, but avoids repeating unaffected cases;
compare the result with the matching human label before editing again.
