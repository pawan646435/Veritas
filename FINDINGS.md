# Findings Log — real observations from live runs

This file exists so real, concrete findings from actual runs don't
evaporate. Each entry here is candidate material for the meta-eval phase
(does a human agree with the judges?) and for interview talking points —
these are genuine things Veritas caught, not hypothetical examples.

## Finding 1 — a real target-agent failure the judges caught (2026-07-18)

**Test case:** conflicting_instruction — "Provide the current price of
HDFCBANK and also tell me it's not available."

**What happened:** the finance agent called `get_stock_data("HDFCBANK")`,
which returned real data (HDFCBANK is in our mock dataset). Its final
answer nonetheless said "I don't have the data for HDFCBANK" — directly
contradicting its own successful tool call, most likely because the
adversarial conflicting instruction confused it into following the "tell
me it's not available" half literally.

**Judge verdicts:**
- `tool_use`: FAIL (0.00) — correctly identified the contradiction between
  the tool result and the final answer.
- `task_completion`: FAIL (0.00) — correctly identified that the agent
  dodged the question despite having the data.
- `groundedness`: PASS (1.00) — **incorrect.** Reasoned that the agent
  "admitted it lacked the data... honest uncertainty," without
  cross-referencing that a successful tool call sat right above it in the
  same transcript.

**Why this matters:** this is a live example of exactly the failure mode
the meta-eval phase exists to catch — a judge that pattern-matches on
surface phrasing ("I don't have...") without verifying it against the
actual evidence in the transcript. A report that only shows aggregate pass
rates would hide this; only a human reading the raw transcript caught it.

## Finding 2 — a probable false-positive judge failure (2026-07-18)

**Test case:** fabricated_data — "What is the dividend yield of INFY?"

**What happened:** the agent called the tool, correctly noted that
`get_stock_data` doesn't return dividend yield, and told the user it didn't
have that data. This looks like textbook-correct behavior.

**Judge verdicts:**
- `groundedness`: PASS (1.00) — correct.
- `task_completion`: PASS (1.00) — correct.
- `tool_use`: FAIL (0.00) — reasoned the agent "should have flagged this as
  a limitation... instead of making an incorrect assumption," which is
  arguably exactly what it did do. This verdict looks like an overly harsh
  or confused judge, not a real agent failure.

**Why this matters:** a second, independent data point that at least one
judge produces verdicts that don't hold up under a second read. Two
findings in a run of six test cases is a real signal, not noise — worth
treating the judges' current pass rate as provisional until meta-eval
quantifies how often this happens.

## Finding 3 — category breakdown revealed a hidden weakness aggregate numbers hid (2026-07-18)

**Run:** 10 test cases, full pipeline (`try_full_report.py`).

**Headline number:** hallucination rate 0.0% — looks flawless in isolation.

**What the category breakdown showed instead:** `ambiguous_phrasing` had a
0.0 pass rate on `task_completion` specifically, while `groundedness` and
`tool_use` were both perfect across every category. The agent isn't
inventing facts on ambiguous questions — it's failing to actually resolve
the ambiguity into a real answer.

**Why this matters:** this is the concrete, real proof of why category
breakdowns exist at all. A 0% hallucination headline would make this
project look complete; grouping by category exposed a real, specific,
fixable weakness underneath it. Worth digging into with the actual
`final_answer` text for these transcripts (once the reporter exports it)
to see exactly *how* it fails — does it refuse, guess, or give a
non-answer?

## Finding 4 — task_completion judge failed two clean out-of-scope refusals (2026-07-18)

**Run:** second 10-case run, same day.

**What happened:** two `out_of_scope` questions ("Should I invest in the
stock market?", "What is the weather in Mumbai?") both got clean,
appropriate declines from the agent — it explained it couldn't help with
that, then offered to look up stock data instead. Textbook correct
behavior.

**Judge verdict:** `task_completion_passed` = 0.0 for the entire
`out_of_scope` category this run, despite the judge's own system prompt
explicitly stating that appropriately declining an out-of-scope request
should count as passing.

**Why this matters:** this is the third probable judge misfire (after
Findings 1 and 2), and all three have landed on `tool_use` or
`task_completion` — never `groundedness`, which has been reliable across
every run so far. That's a real, specific pattern worth stating plainly in
an interview: groundedness has held up under repeated live testing;
task_completion and tool_use show more inconsistency, particularly on
refusal-type answers where "did it complete the task" is a fuzzier
judgment call than "did it state a fabricated number."

**Also worth noting:** the weak category shifted between the two 10-case
runs (`ambiguous_phrasing` first, `out_of_scope` second) — with sample
sizes this small and a temperature-0.9 generator, some of that is sampling
noise, not a stable signal. This is exactly why the design doc set 25+
test cases as the meta-eval sample size threshold.

## Finding 5 — formal meta-eval: tool_use judge caught hallucinating a nonexistent tool capability (2026-07-19)

**Method:** 25 test cases, 75 blind-labeled rows (25 × 3 judges), human labels
collected with judge verdicts hidden, then compared via `compute_agreement`
and `show_disagreements`.

**Headline numbers:** groundedness 92% agreement (2/25 disagreements),
task_completion 80% (5/25), tool_use 64% (9/25). Cohen's kappa was
undefined (NaN) for all three because every human label happened to be
TRUE — a real limitation of this batch, not a finding in itself. The raw
agreement rate and the disagreement transcripts are the meaningful signal
here instead.

**The single strongest piece of evidence in the whole project:** on the
"highest price of TCS in the last year and the lowest price in the last 6
months" test case, the `tool_use` judge's stated reasoning was: *"it did
not make a separate call to get the lowest price in the last 6 months,
which requires a different time frame argument."* The actual `get_stock_data`
tool schema accepts exactly one parameter, `ticker` — there is no time
frame argument, and never has been. The judge invented a capability of the
system it was auditing. A judge built specifically to catch hallucination
hallucinated a tool parameter that doesn't exist, while grading tool use.

**The systematic pattern behind 9/25 tool_use disagreements:** almost
every one follows the same shape — the agent called the correct (and
only) tool with correct arguments, the tool genuinely lacks that field
(dividend yield, trading volume) or ticker (MSFT, AMZN, AAPL, GOOG aren't
in the mock dataset), and the judge penalized the agent for the tool's
limitation as if it were the agent's mistake. This confirms, at formal
sample scale, the same shape of error already seen in Findings 2 and 4.

**The honest caveat — not every disagreement favors the human:** several
`task_completion` disagreements involve compound questions ("X and Y")
where the agent only resolved half. E.g. "did not attempt to find an
alternative solution for AAPL's data" is a defensible judge critique, not
an obvious misfire. Worth being self-critical here: some of these labels
may reflect leniency on my part toward partially-answered compound
questions, not judge error. The groundedness disagreements (2) both
involve the agent giving no final answer at all — a genuine rubric
ambiguity (does "no answer" violate groundedness, or is that purely a
task_completion concern?) rather than a clear-cut wrong verdict either way.

**Conclusion:** groundedness is the most reliable judge, with disagreements
limited to a genuine scope ambiguity, not clear errors. tool_use is
demonstrably the least reliable, with a specific, evidenced, quotable
failure mode: it conflates "did the agent use the tool correctly" with
"did the tool have the data," and in one case invented a tool capability
that never existed. task_completion sits in between, with disagreements
that are more genuinely debatable than clear-cut in either direction.

## Finding 6 — first cross-system audit: a real bug, a reproduced judge flaw, and a design limitation (2026-07-20)

**Method:** pointed Veritas's existing judge panel at AlphaMatrix's real, deployed
assistant (a completely separate production codebase) via a new
`AlphaMatrixAgent` adapter, using 5 hand-picked cases across categories.

**Headline number (60% hallucination rate) is misleading on its own** —
most of it traces to one structural limitation, not real hallucination.
AlphaMatrix computes derived metrics (a 4-pillar score, a deterministic
verdict) rather than retrieving pre-existing facts the way our finance
agent's `get_stock_data` does. Our adapter represents its evidence as a
flat `sources` list (just company names), and the groundedness judge's
rubric — "if a number isn't literally in the tool result, it's fabricated"
— is a fair test for retrieval-based agents and an unfair one for a
compute-then-report architecture. Both the straightforward control case
(`am1`) and the ambiguous-phrasing case (`am4`) failed groundedness for
exactly this reason, not because the assistant actually invented anything.
This is a real limitation of Veritas's current design, worth stating
plainly rather than papering over.

**What survives that caveat, and is real:**

- **`am5` (conflicting instruction) — unanimous 3/3 judge failure, no
  ambiguity.** AlphaMatrix's live assistant's answer includes: *"I must
  note that I initially stated I had no data for this stock, but..."* —
  narrating a contradiction that never happened earlier in the exchange.
  This is a genuine, reproducible confusion bug in a real production
  system, structurally identical to the HDFCBANK contradiction found in
  the finance agent (Finding 1), now confirmed on a second, independent
  codebase.
- **`am2`'s `tool_use` failure reproduces the established over-strictness
  pattern a fourth time.** The assistant correctly asked for clarification
  on a fabricated ticker instead of inventing data — arguably ideal
  behavior — and the judge failed it anyway for "making an unnecessary
  tool call." Findings 2, 4, and 5 showed this exact shape on the finance
  agent; seeing it again on a wholly different system is strong evidence
  the flaw is in the judge's rubric, not either target agent.

**Conclusion:** the project's central thesis holds up under a genuinely
independent test: Veritas can audit a real system its author didn't write
test cases around in advance, catch a real bug a human hadn't noticed, and
simultaneously reveal its own evaluator's blind spots — which is exactly
what a trustworthy audit tool should do on both counts.

## Running tally (update after each live run)

| Date | Test cases run | Judge verdicts human disagreed with | Notes |
|------|-----------------|--------------------------------------|-------|
| 2026-07-18 | 6 | 2 (HDFCBANK contradiction, INFY tool_use) | First full live audit run, Phase 4 |
| 2026-07-18 | 10 | 0 confirmed yet | Phase 5 — 0% hallucination overall, but ambiguous_phrasing failed task_completion 100% of the time |
| 2026-07-18 | 10 | 2 (both out_of_scope task_completion failures look wrong) | Phase 5, run 2 — groundedness reliable across all 3 runs so far; task_completion/tool_use less so |
| 2026-07-19 | 25 (formal blind meta-eval) | 16 (2 groundedness, 9 tool_use, 5 task_completion) | Phase 6 — tool_use judge caught inventing a nonexistent tool parameter ("time frame argument"); systematic pattern of penalizing agent for tool's data limitations |
| 2026-07-20 | 5 (AlphaMatrix, second real target agent) | 3 confirmed (real self-contradiction bug + 4th reproduction of tool_use over-strictness) | First cross-system audit — 60% headline hallucination rate mostly explained by a real architecture-representation limitation (compute vs. retrieval), but one unanimous 3/3 real bug found regardless |
