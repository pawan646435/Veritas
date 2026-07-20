from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agents.finance_agent import FinanceAgent


def _fake_tool_call_response():
    """Mimics what Groq returns when the model decides to call a tool."""
    tool_call = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="get_stock_data", arguments='{"ticker": "INFY"}'),
    )
    message = SimpleNamespace(content=None, tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _fake_final_response(text: str):
    """Mimics what Groq returns on the second call, once it has tool data."""
    message = SimpleNamespace(content=text, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@patch("app.agents.finance_agent.Groq")
def test_finance_agent_calls_tool_and_returns_answer(mock_groq_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _fake_tool_call_response(),
        _fake_final_response("Infosys's P/E ratio is 27.3."),
    ]
    mock_groq_cls.return_value = mock_client

    agent = FinanceAgent()
    response = agent.answer("What is the P/E ratio of Infosys?")

    assert response.tool_calls[0].tool_name == "get_stock_data"
    assert response.tool_calls[0].arguments == {"ticker": "INFY"}
    assert "27.3" in response.final_answer
    assert mock_client.chat.completions.create.call_count == 2
