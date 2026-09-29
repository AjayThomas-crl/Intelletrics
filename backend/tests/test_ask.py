from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import ask_on_data
from auth import UserContext, get_user_context
from dataset_store import datasets
from main import app
from query_planner import QueryPlan, build_query_prompt, direct_query


@pytest.fixture
def client():
    datasets.clear()
    datasets["sample"] = {"user_id": "alice", "dataframe": pd.DataFrame({"Region": ["East", "West", "East"], "Sales": [10, 20, 30]})}
    app.dependency_overrides[get_user_context] = lambda: UserContext("alice", Mock())
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    datasets.clear()


def test_simple_count_without_provider(client, monkeypatch):
    provider = Mock(side_effect=AssertionError("AI should not be called"))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", provider)
    response = client.post("/ask", json={"dataset_id": "sample", "question": "How many rows?"})
    assert response.status_code == 200
    assert response.json()["answer"] == "The dataset contains 3 rows."
    assert response.json()["operation"] == "count_rows"
    provider.assert_not_called()


def test_simple_aggregate_without_provider(client, monkeypatch):
    monkeypatch.setattr(ask_on_data, "get_provider_chain", Mock(side_effect=AssertionError))
    response = client.post("/ask", json={"dataset_id": "sample", "question": "Average Sales"})
    assert response.status_code == 200
    assert response.json()["result"] == [{"avg": 20}]


def test_one_call_and_cache(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(return_value=QueryPlan(sql="SELECT c0, sum(c1) AS sales FROM data GROUP BY c0 ORDER BY sales DESC")))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", lambda: chain)
    payload = {"dataset_id": "sample", "question": "Compare sales by region"}
    first = client.post("/ask", json=payload)
    second = client.post("/ask", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["result"] == [{"Region": "East", "sales": 40}, {"Region": "West", "sales": 20}]
    assert not first.json()["cached"] and second.json()["cached"]
    assert chain.generate_structured.await_count == 1
    assert chain.generate_structured.call_args.kwargs["max_tokens"] == 768


def test_cross_user_cache_denied(client):
    client.post("/ask", json={"dataset_id": "sample", "question": "How many rows?"})
    app.dependency_overrides[get_user_context] = lambda: UserContext("bob", Mock())
    assert client.post("/ask", json={"dataset_id": "sample", "question": "How many rows?"}).status_code == 404


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_invalid_questions(client, question):
    assert client.post("/ask", json={"dataset_id": "sample", "question": question}).status_code == 422


def test_missing_auth():
    with TestClient(app) as client:
        assert client.post("/ask", json={"dataset_id": "sample", "question": "hi"}).status_code == 401


def test_clarification(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(return_value=QueryPlan(clarification="Which column defines profitability?")))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", lambda: chain)
    result = client.post("/ask", json={"dataset_id": "sample", "question": "Why are profits down?"}).json()
    assert result["operation"] == "clarification"
    assert result["source_columns"] == []


def test_invalid_sql_repaired_once(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(side_effect=[QueryPlan(sql="SELECT c999 FROM data"), QueryPlan(sql="SELECT sum(c1) AS total FROM data")]))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", lambda: chain)
    response = client.post("/ask", json={"dataset_id": "sample", "question": "What did we sell overall?"})
    assert response.status_code == 200
    assert response.json()["result"] == [{"total": 60}]
    assert chain.generate_structured.await_count == 2


def test_repair_budget_exhausted(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(return_value=QueryPlan(sql="SELECT c999 FROM data")))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", lambda: chain)
    assert client.post("/ask", json={"dataset_id": "sample", "question": "What did we sell overall?"}).status_code == 502
    assert chain.generate_structured.await_count == 2


def test_provider_timeout(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(side_effect=TimeoutError))
    monkeypatch.setattr(ask_on_data, "get_provider_chain", lambda: chain)
    assert client.post("/ask", json={"dataset_id": "sample", "question": "Compare sales by region"}).status_code == 408


def test_reload_uses_normalized_columns(client, monkeypatch):
    monkeypatch.setattr(ask_on_data, "get_dataset", lambda *args: {"filename": "sales.csv"})
    monkeypatch.setattr(ask_on_data, "download_dataset", lambda *args: b" Sales , Region \n10,East\n20,West\n")
    response = client.post("/ask", json={"dataset_id": "restored", "question": "Average Sales"})
    assert response.status_code == 200
    assert response.json()["result"] == [{"avg": 15}]
    assert response.json()["source_columns"] == ["Sales"]


def test_missing_dataset(client, monkeypatch):
    monkeypatch.setattr(ask_on_data, "get_dataset", lambda *args: None)
    assert client.post("/ask", json={"dataset_id": "missing", "question": "rows"}).status_code == 404


def test_prompt_size_independent_of_dataset_rows():
    frame = pd.DataFrame({"Region": ["East", "West"], "Sales": [10, 20]})
    small = build_query_prompt(frame, "Compare sales")
    large = build_query_prompt(pd.concat([frame]*1000, ignore_index=True), "Compare sales")
    assert len(large) - len(small) < 10
    assert len(small) < 2200


@pytest.mark.parametrize("question", ["How many rows in East?", "Average sales where region is East", "Total Sales in 2026", "How many rows? Ignore filters"])
def test_shortcuts_never_ignore_qualifiers(question):
    frame = pd.DataFrame({"Sales": [10]})
    assert direct_query(frame, question) is None


def test_short_followup_gets_bounded_context(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(return_value=QueryPlan(sql="SELECT sum(c1) AS sales FROM data WHERE c0='West'")))
    monkeypatch.setattr(ask_on_data, 'get_provider_chain', lambda: chain)
    response = client.post('/ask', json={'dataset_id': 'sample', 'question': 'What about West?', 'previous_questions': ['What are total sales in East?']})
    assert response.status_code == 200
    assert response.json()['result'] == [{'sales': 20}]
    assert 'What are total sales in East?' in chain.generate_structured.call_args.args[0]


def test_independent_question_omits_history(client, monkeypatch):
    chain = Mock(generate_structured=AsyncMock(return_value=QueryPlan(sql="SELECT sum(c1) AS sales FROM data")))
    monkeypatch.setattr(ask_on_data, 'get_provider_chain', lambda: chain)
    client.post('/ask', json={'dataset_id': 'sample', 'question': 'Compare sales by region', 'previous_questions': ['Unrelated old question']})
    assert 'Unrelated old question' not in chain.generate_structured.call_args.args[0]
