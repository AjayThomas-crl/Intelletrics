import math
import logging
import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ai_insights import get_provider_chain
from auth import UserContext, get_user_context
from chart_generator import charts_description, generate_charts
from config import FRONTEND_URLS, MAX_UPLOAD_BYTES
from persistence import save_dataset
from profiler import profile_dataframe
from dataset_store import datasets
from data_io import parse_dataset
from health import readiness
from ask_on_data import ask_data, AskRequest, AskResponse


app = FastAPI(title="Intelletrics API", version="1.0")
logger = logging.getLogger("intelletrics.api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
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


# Compatibility for callers using the original parser name.
parse_upload = parse_dataset


@app.api_route("/", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    return await readiness()


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
        logger.exception("AI insight generation failed for dataset %s", dataset_id)

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
