# Veritas — Design Document

Status: **planning complete, build in progress**
Last updated: 2026-07-12

## 1. One-line pitch

An autonomous agent that stress-tests and evaluates other AI agents — catching hallucinated facts, wrong tool use, and unanswered questions — and then validates its own judgment against human labels.

## 2. The problem

Every team shipping an LLM agent (support bot, financial assistant, research tool) has the same unsolved problem: **they don't actually know how often it's wrong.**

- Manual spot-checking doesn't scale past a handful of test conversations.
- "It seemed fine when I tried it" is not measurement.
- In finance specifically, a hallucinated number is a trust-destroying failure, not a minor bug — this is exactly the domain AlphaMatrix and SkillPilot's target companies (Screener.in, Smallcase, Tickertape, etc.) operate in.
- Industry analysts project a large share of enterprise apps will ship task-specific agents very soon — more agents shipping, with no standard way to know which ones are lying to their users.

Veritas turns "does our agent hallucinate?" into a repeatable, measurable number, with concrete evidence for every failure it flags.

## 3. What it does (functional loop)

Given a target agent in a domain (starting with finance):

1. **Generate** adversarial test cases automatically — ambiguous questions, questions about data that doesn't exist, conflicting instructions, plus normal control questions.
2. **Run** each test case against the target agent, capturing the full transcript: question asked, every tool call made (name, arguments, result), and the final answer.
3. **Judge** each transcript with a panel of narrow, specialized graders:
   - Groundedness judge — does every number/claim trace back to real source data?
   - Tool-use judge — was the right tool called, with correct arguments?
   - Task-completion judge — did the answer actually address the question asked?
4. **Report** — aggregate results into a hallucination rate, failure categories, and worst-offending examples (not a single vague score).
5. **Meta-evaluate** — hand-label a sample of transcripts, then measure how often the judges agree with the human labels. This is the step that turns "an eval script" into "a trustworthy eval system," and it's the rarest thing in this entire plan.

First test subject: a small finance Q&A agent we build from scratch (Phase 1). Second test subject: AlphaMatrix's real assistant — a genuine before/after portfolio story.

## 4. Tech stack (all free-tier)

| Layer | Choice | Why |
|---|---|---|
| LLM | Groq, `llama-3.3-70b-versatile` | Already used in AlphaMatrix/SkillPilot, generous free tier, fast |
| Backend | FastAPI | Matches existing stack, async-native |
| Database | Postgres via Neon free tier | Reuse from AlphaMatrix; queryable audit history, not just files |
| ORM / migrations | SQLAlchemy (async) + Alembic | Schema evolution is a real interview topic |
| Caching | Upstash Redis free tier | Optional — cache repeated test-generation calls |
| Containerization | Docker | Already in workflow |
| Deployment | Google Cloud Run free tier | Reuse GCP project from SkillPilot |
| Testing | pytest + pytest-asyncio | Biggest single differentiator for AI-role interviews |
| Linting/formatting | ruff | One tool, fast, signals maintained code |
| Config | pydantic-settings | Typed config, no scattered `os.getenv()` |
| CI | GitHub Actions free tier | Green checkmark = production signal |
| Retries | tenacity | Proper backoff around every Groq call |

## 5. Architecture

**Pipeline (what happens on one audit run):**

```
Test generator --> Test runner <--> Target agent
                         |
                         v
                   Judge panel
                         |
                         v
                   Audit report
```

**Layered structure (how the code is organized):**

```
Veritas service (FastAPI app)
├── API layer            — routes, request validation
└── Services and agents   — test generator, test runner, judges, reporter
        │
        ├──> Groq API        (LLM calls)
        └──> Neon Postgres   (persisted state)
```

**Folder structure:**

```
veritas/
├── app/
│   ├── core/            # config, logging, exceptions
│   ├── schemas/          # Pydantic models (the shared data language)
│   ├── agents/           # target agent(s) under test — pluggable
│   ├── services/         # test_generator, test_runner, judges, reporter
│   ├── db/               # SQLAlchemy models + session
│   └── api/               # FastAPI routes
├── tests/
├── alembic/               # migrations
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## 6. Glossary (core concepts, precisely defined)

- **Target agent** — the system being audited. Starts as a small finance Q&A agent we build; later, AlphaMatrix's assistant.
- **Test case** — one question (adversarial or control) with a category label and notes on why it's tricky.
- **Transcript** — the full record of one run: test case + tool calls + final answer.
- **Judge** — an LLM call with a single, narrow rubric that scores one transcript on one dimension.
- **Verdict** — one judge's output: pass/fail, a 0–1 score, and reasoning.
- **Audit result** — a transcript plus every judge's verdict on it — the row unit for reporting.
- **Hallucination rate** — proportion of transcripts where the groundedness judge flags an unsupported claim.
- **Meta-evaluation** — measuring judge-vs-human agreement, to know whether the judges themselves can be trusted.

## 7. Build roadmap

- [ ] Phase 0 — project setup, environment, schemas (`app/schemas/models.py`)
- [ ] Phase 1 — target agent: small finance Q&A agent with tool use
- [ ] Phase 2 — test generator (adversarial + control test cases)
- [ ] Phase 3 — test runner (executes cases, captures transcripts)
- [ ] Phase 4 — judge panel (groundedness, tool-use, task-completion judges)
- [ ] Phase 5 — reporter (pandas aggregation, hallucination rate, categorized failures)
- [x] Phase 6 — meta-eval (hand-labeled sample vs. judge agreement)
- [ ] Phase 7 — persistence (Postgres + Alembic migrations)
- [ ] Phase 8 — FastAPI wrapper + Docker + CI
- [ ] Phase 9 — deploy to Cloud Run, point auditor at AlphaMatrix's real agent
- [ ] Phase 10 — README, write-up, resume bullet

## 8. What "done" looks like (success metrics)

- Auditor can run against 2 different target agents (finance stub + AlphaMatrix) without code changes to the auditor itself.
- Hallucination rate reported with a confidence-relevant sample size (25+ test cases minimum).
- Meta-eval shows measured agreement between judges and human labels (e.g. "judges agreed with my labels on 22/25 transcripts") — not just an assumed-correct score.
- CI green on every push; test suite doesn't assume exact-string determinism.
- Deployed, with a live endpoint or a recorded demo.

## 9. Interview talking points (keep updating this as we build)

- Why LLM-as-judge needs validation (self-preference bias, position bias, verbosity bias) and how the meta-eval step addresses it.
- How to test non-deterministic systems (assert on structure/ranges/schema conformance, not exact strings).
- Cost/latency tradeoffs — why Groq, how caching and cheaper models control cost at scale.
- Failure handling — what happens when the LLM API times out or rate-limits mid-audit (tenacity retries).
- Schema-first design — why Pydantic at every boundary prevents silent data corruption.
- **A real example of judge unreliability I found**: in an actual run, the
  finance agent contradicted its own successful tool call (said "no data"
  for a ticker it had just successfully looked up). Two of three judges
  caught it; the groundedness judge incorrectly passed it, having pattern-
  matched on the surface phrasing "I don't have the data" without cross-
  checking the transcript's own tool call result. See `FINDINGS.md` for the
  full transcript — this is real evidence for why meta-eval matters, not a
  hypothetical.
- **The formal meta-eval result (headline finding)**: ran a 25-case blind
  human-vs-judge comparison. Groundedness agreed with my independent
  judgment on 92% of cases; tool_use only 64%. The single most concrete
  piece of evidence: the tool_use judge once justified a failing verdict
  by claiming a tool call "requires a different time frame argument" —
  but the actual tool schema has exactly one parameter, `ticker`, and
  never had a time parameter at all. A judge built to catch hallucination
  hallucinated a tool capability that never existed, while grading tool
  use. This is the single strongest, most quotable piece of evidence in
  the whole project for why LLM-as-judge requires validation, not blind
  trust — see `FINDINGS.md` Finding 5 for the full write-up.
