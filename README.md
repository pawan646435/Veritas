# Veritas

![CI](https://github.com/pawan646435/veritas/actions/workflows/ci.yml/badge.svg)

**An autonomous agent that audits other AI agents — catching hallucinated facts, misused tools, and unanswered questions, then validating its own judgment against a human, blind.**

## The problem

Every team shipping an LLM agent — a support bot, a financial assistant, a
research tool — has the same unsolved problem: **they don't actually know
how often it's wrong.** Manual spot-checking doesn't scale past a handful
of test conversations, "it seemed fine when I tried it" isn't measurement,
and in domains like finance, a hallucinated number is a trust-destroying
failure, not a minor bug.

Veritas turns "does our agent hallucinate?" into a repeatable, measurable
number — with concrete evidence for every failure it flags, and a formal
process for checking whether its own judgment can be trusted at all.

## What it does

Given a target agent in a domain (a small finance Q&A agent, built here as
the first thing audited):

1. **Generates adversarial test cases automatically** — ambiguous
   questions, questions about data that doesn't exist, conflicting
   instructions, plus normal control questions. No hand-written test
   scripts; an LLM invents the questions.
2. **Runs** each test case against the target agent, capturing the full
   transcript: question, every tool call made, final answer.
3. **Judges** each transcript with three narrow, specialized graders —
   groundedness (did it fabricate a fact?), tool use (did it call the
   right tool correctly?), task completion (did it actually answer?).
4. **Reports** a hallucination rate, a category-level breakdown, and the
   worst-offending transcripts — not a single vague score.
5. **Validates itself** — a formal, blind human-labeling process measures
   how often the judges agree with independent human judgment, using
   Cohen's kappa, not just raw agreement.

## A real finding, not a hypothetical

In a formal 25-case blind meta-evaluation, the `tool_use` judge justified
a failing verdict by claiming a tool call "requires a different time frame
argument" — but the actual tool schema has exactly one parameter,
`ticker`, and never had a time-based parameter at all. **A judge built to
catch hallucination hallucinated a tool capability that never existed,
while grading tool use.** Full write-up, including every disagreement
between the judges and a human reviewer, in [`FINDINGS.md`](./FINDINGS.md).

## Architecture

```
Test generator --> Test runner <--> Target agent
                         |
                         v
                   Judge panel
                         |
                         v
                   Audit report
```

Layered structure:

```
FastAPI app
├── API layer            — routes, request validation
└── Services and agents   — test generator, test runner, judges, reporter
        │
        ├──> Groq API        (LLM calls)
        └──> Neon Postgres   (persisted audit history)
```

## Tech stack

| Layer | Choice |
|---|---|
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Backend | FastAPI, async |
| Database | Postgres (Neon) via SQLAlchemy 2.0 async + Alembic migrations |
| Testing | pytest, pytest-asyncio, mocked LLM calls, in-memory SQLite for DB tests |
| Linting | ruff |
| Config | pydantic-settings, fail-fast validation |
| Retries | tenacity, with `reraise=True` |
| Containerization | Docker (multi-stage build) |
| CI | GitHub Actions — lint + full test suite on every push |

## Getting started

```bash
git clone https://github.com/pawan646435/veritas.git
cd veritas
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in your real GROQ_API_KEY and DATABASE_URL
alembic upgrade head    # creates the database schema
```

## Running tests

```bash
pytest -v      # full suite — mocked LLM calls, in-memory SQLite, no real secrets needed
ruff check .   # lint
```

## Running it

```bash
uvicorn app.main:app --reload
```

Then:
- `GET /health` — liveness check
- `POST /audits/run?n=10` — generate, run, judge, and persist a real batch
- `GET /audits/report` — aggregated report from persisted audit history

Or with Docker:

```bash
docker-compose up
```

## The meta-evaluation, in detail

`FINDINGS.md` is a running log of every real observation from live runs —
not curated highlights, the actual disagreements, including cases where
the judges were probably right and a human reviewer (me) was probably
being lenient. `DESIGN.md` has the full design rationale and build
roadmap, phase by phase.

## Project structure

```
veritas/
├── app/
│   ├── core/        # config, logging, exceptions
│   ├── schemas/      # Pydantic models — the shared data language
│   ├── agents/        # target agent(s) under test — pluggable
│   ├── services/      # test generator, runner, judges, reporter, meta-eval
│   ├── db/            # SQLAlchemy models, session, repository
│   └── api/            # FastAPI routes
├── tests/
├── alembic/             # migrations
├── scripts/              # manual/live smoke-test entrypoints
├── .github/workflows/    # CI
├── Dockerfile
└── docker-compose.yml
```

## License

MIT
