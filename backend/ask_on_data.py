"""Dataset Q&A: load, plan once, compute locally, and return compact answers."""
from __future__ import annotations

import asyncio
import logging
import re
from collections import OrderedDict
from typing import Any, Annotated

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from ai_insights import get_provider_chain
from auth import UserContext
from data_io import parse_dataset
from dataset_store import datasets
from persistence import download_dataset, get_dataset
from query_engine import MAX_RESULT_ROWS, QueryResult
from query_planner import QueryPlan, build_query_prompt, direct_query
from query_runner import execute_in_isolated_process

logger = logging.getLogger(__name__)
PLAN_MAX_TOKENS = 768
PLAN_TIMEOUT_SECONDS = 45
MAX_CACHED_ANSWERS = 16
_query_slots = asyncio.Semaphore(2)


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    dataset_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=2000)
    previous_questions: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=2)


class AskResponse(BaseModel):
    answer: str
    operation: str
    result: list[dict[str, Any]] | dict[str, Any] | int | float
    source_columns: list[str]
    truncated: bool = False
    cached: bool = False


def _load_dataset(request: AskRequest, context: UserContext) -> dict:
    cached = datasets.get(request.dataset_id)
    if cached is not None:
        if cached["user_id"] != context.user_id:
            raise HTTPException(404, "Dataset not found")
        return cached
    dataset = get_dataset(context.client, request.dataset_id, context.user_id)
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    frame = parse_dataset(dataset["filename"], download_dataset(context.client, dataset))
    cached = {"user_id": context.user_id, "dataframe": frame}
    datasets[request.dataset_id] = cached
    return cached


def _format_value(value: Any) -> str:
    if value is None:
        return "not available"
    if isinstance(value, float):
        return f"{value:,.6g}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)[:200]


def _format_response(result: QueryResult, operation: str = "query") -> AskResponse:
    truncated = result.truncated or len(result.rows) > MAX_RESULT_ROWS
    rows = result.rows[:MAX_RESULT_ROWS]
    if not rows:
        answer = "No matching rows."
    elif operation == "count_rows":
        answer = f"The dataset contains {rows[0]['rows']:,} rows."
    elif len(rows) == 1:
        answer = "; ".join(f"{key}: {_format_value(value)}" for key, value in list(rows[0].items())[:6]) + "."
    else:
        answer = f"{'Showing the first' if truncated else 'Returned'} {len(rows)} results."
    if truncated:
        answer += " Result size is limited; narrow your question for more detail."
    return AskResponse(answer=answer, operation=operation, result=rows,
                       source_columns=result.source_columns, truncated=truncated)


async def _execute(frame, sql):
    async with _query_slots:
        return await run_in_threadpool(execute_in_isolated_process, frame, sql)


async def _generate_plan(prompt: str) -> QueryPlan:
    async with asyncio.timeout(PLAN_TIMEOUT_SECONDS):
        return await get_provider_chain().generate_structured(prompt, QueryPlan, max_tokens=PLAN_MAX_TOKENS)


async def ask_data(request: AskRequest, context: UserContext) -> AskResponse:
    try:
        entry = await run_in_threadpool(_load_dataset, request, context)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Could not restore dataset")
        raise HTTPException(502, "Could not load the dataset") from exc

    # Ownership is checked before every lookup; cache lifetime follows the dataset.
    answers = entry.setdefault("answers", OrderedDict())
    # Include short history only when the question refers to an earlier answer.
    follow_up = re.search(r"\b(it|them|those|these|that|same|previous|instead|again)\b|^(and|now|what about|how about|only|also|by|for)\b", request.question, re.I)
    history = request.previous_questions if follow_up else []
    key = (request.question, tuple(history))  # Preserve literal filter values.
    if key in answers:
        answers.move_to_end(key)
        return answers[key].model_copy(update={"cached": True}, deep=True)
    frame = entry["dataframe"]
    try:
        direct = await run_in_threadpool(direct_query, frame, request.question)
        if isinstance(direct, tuple):
            operation, result = direct
            response = _format_response(result, operation)
        else:
            prompt = None
            if isinstance(direct, str):
                plan = QueryPlan(sql=direct)
            else:
                prompt = await run_in_threadpool(build_query_prompt, frame, request.question, history)
                plan = await _generate_plan(prompt)
            if plan.sql:
                try:
                    result = await _execute(frame, plan.sql)
                except ValueError as exc:
                    if prompt is None:
                        raise
                    # At most one repair, only on invalid SQL. Normal queries use one call.
                    plan = await _generate_plan(prompt + "\nRepair this invalid query once. "
                        + f"SQL: {plan.sql}\nError: {str(exc)[:300]}")
                    if plan.sql:
                        result = await _execute(frame, plan.sql)
                if plan.sql:
                    response = _format_response(result)
            if not plan.sql:
                response = AskResponse(answer=plan.clarification or "Please clarify your question.",
                    operation="clarification", result={}, source_columns=[])
    except TimeoutError as exc:
        raise HTTPException(408, "Analysis timed out. Try a narrower question.") from exc
    except Exception as exc:
        logger.exception("Dataset question analysis failed")
        raise HTTPException(502, "Could not analyze this question. Please rephrase it or try again.") from exc

    answers[key] = response.model_copy(deep=True)
    answers.move_to_end(key)
    while len(answers) > MAX_CACHED_ANSWERS:
        answers.popitem(last=False)
    return response
