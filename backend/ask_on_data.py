from __future__ import annotations

import math
from io import BytesIO
from typing import Any, Literal

import pandas as pd
from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator

from ai_insights import get_provider_chain
from auth import UserContext
from dataset_store import datasets
from persistence import download_dataset, get_dataset
from query_runner import execute_in_isolated_process


ALLOWED_AGGREGATIONS = {"mean", "sum", "min", "max", "count", "median"}


class AskRequest(BaseModel):
    dataset_id: str
    question: str = Field(min_length=1, max_length=500)


class QueryPlan(BaseModel):
    operation: Literal[
        "count_rows",
        "group_aggregate",
        "top_categories",
        "column_summary",
        "missing_values",
        "unsupported",
    ]
    column: str | None = None
    group_by: str | None = None
    aggregation: Literal["mean", "sum", "min", "max", "count", "median"] | None = None
    limit: int = Field(default=10, ge=1, le=100)


class AskResponse(BaseModel):
    answer: str | int | float
    operation: str
    result: list[dict[str, Any]] | dict[str, Any] | int | float
    source_columns: list[str]

    @field_validator("answer", mode="before")
    @classmethod
    def coerce_answer(cls, value: object) -> str:
        return str(value) if not isinstance(value, str) else value


def _safe_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return _safe_value(value.item())
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _safe_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _safe_value(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _require_column(df: pd.DataFrame, column: str | None, label: str) -> str:
    if not column or column not in df.columns:
        raise ValueError(f"Select a valid {label} column")
    return column


def execute_query_plan(df: pd.DataFrame, plan: QueryPlan) -> tuple[Any, list[str], str]:
    """Execute only explicitly supported Pandas operations."""
    if plan.operation == "unsupported":
        return (
            {
                "supported_operations": [
                    "count_rows",
                    "group_aggregate",
                    "top_categories",
                    "column_summary",
                    "missing_values",
                ]
            },
            [],
            "I can't answer that question yet. I can answer questions about row counts, "
            "grouped aggregations, top categories, column summaries, and missing values.",
        )

    if plan.operation == "count_rows":
        return len(df), [], f"The dataset contains {len(df):,} rows."

    if plan.operation == "missing_values":
        if plan.column:
            column = _require_column(df, plan.column, "data")
            count = int(df[column].isna().sum())
            percentage = round(count * 100 / len(df), 2) if len(df) else 0
            return (
                {"column": column, "missing": count, "percentage": percentage},
                [column],
                f"{column} has {count:,} missing values ({percentage:.2f}%).",
            )

        result = pd.DataFrame(
            {
                "column": df.columns,
                "missing": [int(df[column].isna().sum()) for column in df.columns],
            }
        )
        result["percentage"] = (result["missing"] * 100 / len(df)).round(2) if len(df) else 0
        result = result.sort_values("missing", ascending=False)
        return _safe_records(result), list(df.columns), "Here are the missing-value counts by column."

    if plan.operation == "column_summary":
        column = _require_column(df, plan.column, "data")
        series = df[column]
        result: dict[str, Any] = {
            "column": column,
            "type": str(series.dtype),
            "count": int(series.count()),
            "missing": int(series.isna().sum()),
            "unique": int(series.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(series):
            result.update(
                {
                    "mean": _safe_value(series.mean()),
                    "median": _safe_value(series.median()),
                    "min": _safe_value(series.min()),
                    "max": _safe_value(series.max()),
                }
            )
        else:
            result["top_values"] = _safe_records(
                series.value_counts(dropna=False).head(plan.limit).rename("count").reset_index()
            )
        return result, [column], f"Here is the summary for {column}."

    if plan.operation == "top_categories":
        column = _require_column(df, plan.column, "category")
        result = (
            df[column]
            .value_counts(dropna=False)
            .head(plan.limit)
            .rename_axis(column)
            .reset_index(name="count")
        )
        return _safe_records(result), [column], f"Here are the most common values in {column}."

    if plan.operation == "group_aggregate":
        group_by = _require_column(df, plan.group_by, "grouping")
        column = _require_column(df, plan.column, "measure")
        if plan.aggregation not in ALLOWED_AGGREGATIONS:
            raise ValueError("Unsupported aggregation")
        if plan.aggregation != "count" and not pd.api.types.is_numeric_dtype(df[column]):
            raise ValueError(f"{column} must be numeric for {plan.aggregation}")

        grouped = (
            df.groupby(group_by, dropna=False)[column]
            .agg(plan.aggregation)
            .reset_index(name="value")
            .sort_values("value", ascending=False)
            .head(plan.limit)
        )
        return (
            _safe_records(grouped),
            [group_by, column],
            f"Here are the top groups by {plan.aggregation} of {column}.",
        )

    raise ValueError("Unsupported operation")


def _build_query_prompt(df: pd.DataFrame, question: str) -> str:
    columns = ", ".join(f"{column} ({df[column].dtype})" for column in df.columns)
    return f"""Convert the user's question into one safe query plan.

Allowed operations:
- count_rows: count all rows
- group_aggregate: aggregate a numeric column grouped by another column
- top_categories: count the most common values in one column
- column_summary: summarize one column
- missing_values: report missing values for one column or all columns
- unsupported: use this when the question cannot be answered by the operations above

Allowed aggregations: mean, sum, min, max, count, median.
Use exact column names from the dataset. Do not invent columns.
Return only the structured plan, with no explanation.

Dataset columns: {columns}
User question: {question}
"""


async def ask_data(request: AskRequest, context: UserContext) -> AskResponse:
    user_id = context.user_id
    cached = datasets.get(request.dataset_id)

    if cached is not None:
        if cached["user_id"] != user_id:
            raise HTTPException(status_code=404, detail="Dataset not found")
        df = cached["dataframe"]
    else:
        dataset = get_dataset(context.client, request.dataset_id, user_id)
        if dataset is None:
            raise HTTPException(status_code=404, detail="Dataset not found")
        raw = download_dataset(context.client, dataset)
        suffix = dataset["filename"].lower().rsplit(".", 1)[-1]
        df = pd.read_csv(BytesIO(raw)) if suffix == "csv" else pd.read_excel(BytesIO(raw))
        datasets[request.dataset_id] = {"user_id": user_id, "dataframe": df}

    try:
        plan = await get_provider_chain().generate_structured(
            _build_query_prompt(df, request.question), QueryPlan, max_tokens=512
        )
        result, source_columns, answer = execute_in_isolated_process(df, plan)
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Could not analyze the question") from exc

    return AskResponse(
        answer=answer,
        operation=plan.operation,
        result=result,
        source_columns=source_columns,
    )
