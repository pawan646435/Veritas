import pandas as pd

from app.schemas.models import AuditResult


class Reporter:
    """Turns a list of AuditResults into an aggregated report: an overall
    hallucination rate, a pass-rate breakdown by test category, and the
    worst-scoring transcripts. This is the actual deliverable a person
    reads — a wall of per-transcript verdicts isn't a report, it's raw data.
    """

    def __init__(self, results: list[AuditResult]) -> None:
        self._results = results
        self._df = self._to_dataframe(results)

    @staticmethod
    def _to_dataframe(results: list[AuditResult]) -> pd.DataFrame:
        """One row per transcript. Judge columns are added dynamically —
        if a judge failed to produce a verdict for some transcript (Phase
        4's partial-failure handling), pandas fills that cell with NaN
        rather than us needing to special-case missing judges by hand.
        """
        rows = []
        for result in results:
            row = {
                "test_case_id": result.transcript.test_case.id,
                "category": result.transcript.test_case.category.value,
                "question": result.transcript.test_case.question,
                "final_answer": result.transcript.final_answer,
            }
            for verdict in result.verdicts:
                row[f"{verdict.judge_name}_passed"] = verdict.passed
                row[f"{verdict.judge_name}_score"] = verdict.score
            rows.append(row)
        return pd.DataFrame(rows)

    def hallucination_rate(self) -> float:
        """Proportion of transcripts the groundedness judge flagged as
        ungrounded. Missing verdicts (the judge failed to parse for that
        transcript) are dropped from the calculation entirely — NOT
        counted as passing, since silently treating "we don't know" as
        "it passed" would understate the real rate.
        """
        if "groundedness_passed" not in self._df.columns or self._df.empty:
            return 0.0
        col = self._df["groundedness_passed"].dropna()
        if col.empty:
            return 0.0
        return float((~col).mean())

    def category_breakdown(self) -> pd.DataFrame:
        """Pass rate per judge, grouped by test case category. This is
        what tells you WHERE the agent is weak — e.g. "94% pass rate
        overall" can hide "but 40% on conflicting_instruction specifically"
        if you never group by category.
        """
        if self._df.empty:
            return pd.DataFrame()
        judge_cols = [c for c in self._df.columns if c.endswith("_passed")]
        return self._df.groupby("category")[judge_cols].mean()

    def worst_offenders(self, n: int = 5) -> pd.DataFrame:
        """The n transcripts with the lowest average judge score — concrete
        examples for a report, not just an aggregate percentage."""
        if self._df.empty:
            return pd.DataFrame()
        score_cols = [c for c in self._df.columns if c.endswith("_score")]
        df = self._df.copy()
        df["avg_score"] = df[score_cols].mean(axis=1)
        return df.sort_values("avg_score").head(n)[
            ["test_case_id", "category", "question", "final_answer", "avg_score"]
        ]

    def export_csv(self, path: str) -> None:
        """Persist the full per-transcript table — the raw material behind
        the summary, worth keeping for later meta-eval comparison."""
        self._df.to_csv(path, index=False)

    def summary(self) -> str:
        """A human-readable report — what you'd paste into a README or
        read out in an interview."""
        if self._df.empty:
            return "No results to report."
        lines = [
            f"Audited {len(self._df)} test cases.",
            f"Hallucination rate: {self.hallucination_rate():.1%}",
            "",
            "Pass rate by category and judge:",
            self.category_breakdown().to_string(),
        ]
        return "\n".join(lines)
