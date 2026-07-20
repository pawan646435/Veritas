import json
from unittest.mock import MagicMock, patch

from app.schemas.models import TestCategory
from app.services.test_generator import TestGenerator

FAKE_CASES = {
    "test_cases": [
        {
            "category": "straightforward",
            "question": "What is the P/E ratio of Infosys?",
            "notes": "Control case.",
        },
        {
            "category": "fabricated_data",
            "question": "What is Wipro's dividend yield?",
            "notes": "Wipro is not in the mock data; checks for fabrication.",
        },
        {
            "category": "bogus_category",
            "question": "This one should be skipped",
            "notes": "Invalid category the model hallucinated.",
        },
    ]
}
FAKE_JSON = json.dumps(FAKE_CASES)


@patch("app.services.test_generator.Groq")
def test_generate_parses_valid_cases_and_skips_invalid_category(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=FAKE_JSON))
    ]
    mock_groq_cls.return_value = mock_client

    generator = TestGenerator()
    cases = generator.generate(n=3)

    # Only 2 of the 3 raw cases are valid — the "bogus_category" one is
    # silently skipped (with a logged warning) rather than crashing the run.
    assert len(cases) == 2
    assert cases[0].category == TestCategory.STRAIGHTFORWARD
    assert cases[1].category == TestCategory.FABRICATED_DATA
    assert all(case.id for case in cases)
