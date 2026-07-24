import math
import io
import logging
import uuid
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_insights import get_provider_chain
from auth import UserContext, get_user_context
from chart_generator import charts_description, generate_charts
from config import FRONTEND_URL, MAX_COLUMNS, MAX_ROWS, MAX_UPLOAD_BYTES
from persistence import save_dataset
from profiler import profile_dataframe
from dataset_store import datasets
from ask_on_data import ask_data, AskRequest, AskResponse


app = FastAPI(title="Intelletrics API", version="1.0")
logger = logging.getLogger("intelletrics.api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def sanitize_for_json(obj):
    """Convert pandas/numpy values and non-finite numbers to JSON-safe values."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, tuple):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        return sanitize_for_json(obj.item())
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def parse_upload(filename: str, content: bytes) -> pd.DataFrame:
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if suffix == "csv":
            return pd.read_csv(io.BytesIO(content))
        if suffix in {"xlsx", "xls"}:
            return pd.read_excel(io.BytesIO(content))
    except (UnicodeDecodeError, ValueError, OSError, ImportError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse dataset: {exc}") from exc
    raise HTTPException(status_code=415, detail="Only .csv, .xlsx, and .xls files are supported")


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/upload")
async def upload(
    context: Annotated[UserContext, Depends(get_user_context)],
    file: UploadFile = File(...),
):
    filename = file.filename or "dataset"
    # Read one byte past the limit so an oversized request is rejected without
    # accepting an arbitrarily large payload into memory.
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit")

    df = parse_upload(filename, content)
    rows, cols = df.shape
    if rows > MAX_ROWS:
        raise HTTPException(status_code=413, detail=f"Dataset exceeds the {MAX_ROWS:,} row limit")
    if cols > MAX_COLUMNS:
        raise HTTPException(status_code=413, detail=f"Dataset exceeds the {MAX_COLUMNS} column limit")
    if rows == 0 or cols == 0:
        raise HTTPException(status_code=400, detail="The dataset must contain at least one row and one column")

    # Normalize column names once so preview/profile/chart keys are stable.
    df.columns = [str(column).strip() or f"column_{index + 1}" for index, column in enumerate(df.columns)]
    if df.columns.duplicated().any():
        raise HTTPException(status_code=400, detail="Column names must be unique")

    df = df.where(pd.notnull(df), None)
    column_names = list(df.columns)
    preview = sanitize_for_json(df.head(10).to_dict(orient="records"))
    profiles = sanitize_for_json(profile_dataframe(df))
    charts = sanitize_for_json(charts_description(generate_charts(df, profiles), profiles))

    dataset_id = str(uuid.uuid4())
    try:
        save_dataset(
            context.client,
            dataset_id=dataset_id,
            user_id=context.user_id,
            filename=filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            rows=rows,
            columns=cols,
            column_names=column_names,
            preview=preview,
            profiles=profiles,
        )
    except Exception as exc:
        logger.exception("Failed to persist dataset %s", dataset_id)
        raise HTTPException(status_code=502, detail="Could not persist dataset in Supabase") from exc

    # Keep a short-lived local cache for the current process; persistence remains the source of truth.
    datasets[dataset_id] = {"user_id": context.user_id, "dataframe": df}

    summary = ""
    insights = []
    try:
        insights_result = await get_provider_chain().generate_insights(profiles, filename, rows, cols)
        insights_data = sanitize_for_json(insights_result.model_dump())
        summary = insights_data["summary"]
        insights = insights_data["insights"]
    except Exception:
        # Upload and deterministic analysis must still succeed when AI is unavailable.
        pass

    return {
        "dataset_id": dataset_id,
        "filename": filename,
        "content_type": file.content_type,
        "rows": rows,
        "columns": cols,
        "column_names": column_names,
        "preview": preview,
        "charts": charts,
        "profiles": profiles,
        "summary": summary,
        "insights": insights,
    }


@app.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    context: Annotated[UserContext, Depends(get_user_context)],
) -> AskResponse:
    return await ask_data(request, context)
