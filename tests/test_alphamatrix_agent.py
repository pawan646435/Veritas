from unittest.mock import MagicMock, patch

from app.agents.alphamatrix_agent import AlphaMatrixAgent


@patch("app.agents.alphamatrix_agent.httpx.Client")
def test_answer_translates_alphamatrix_response_correctly(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": "The Alpha Score verdict for ETERNAL is 41.4, rated AVOID.",
        "scheme_code": 0,
        "sources": ["Eternal Limited"],
    }
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    agent = AlphaMatrixAgent(symbol="ETERNAL")
    response = agent.answer("What is the current verdict?")

    assert "41.4" in response.final_answer
    assert response.tool_calls[0].tool_name == "alphamatrix_lookup"
    assert response.tool_calls[0].arguments == {"symbol": "ETERNAL"}
    assert "Eternal Limited" in response.tool_calls[0].result

    # Confirm the actual request shape sent to AlphaMatrix's real API
    call_kwargs = mock_client.post.call_args
    assert call_kwargs.kwargs["json"]["symbol"] == "ETERNAL"
    assert call_kwargs.kwargs["json"]["message"] == "What is the current verdict?"


@patch("app.agents.alphamatrix_agent.httpx.Client")
def test_answer_handles_missing_sources_gracefully(mock_client_cls):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "I don't have that data.", "sources": []}
    mock_response.raise_for_status.return_value = None
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    agent = AlphaMatrixAgent(symbol="")
    response = agent.answer("What is the P/E ratio of a made-up ticker?")

    assert response.tool_calls[0].result == "no sources returned"
