import math
import uuid
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import shutil
import pandas as pd
from profiler import profile_dataframe
from chart_generator import generate_charts, charts_description
from ai_insights import get_provider_chain
from fastapi.middleware.cors import CORSMiddleware
from ask_on_data import ask_data, AskResponse
from dataset_store import datasets

def sanitize_for_json(obj):
    """Recursively convert NaN/Inf/numpy scalars to native Python types for JSON compliance."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif hasattr(obj, "item"):
        return obj.item()
    return obj


app = FastAPI()

ai_client = get_provider_chain()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def test():
    return "working"


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    destination_path = f"saved_{file.filename}"

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(destination_path)
    else:
        df = pd.read_excel(destination_path)

    df = df.where(pd.notnull(df), None)
    rows, cols = df.shape
    col_names = df.columns.to_list()
    preview = df.head(10).to_dict(orient="records")
    
    profiler = profile_dataframe(df)
    charts = generate_charts(df, profiler)
    charts = charts_description(charts, profiler)
    insights_result = await ai_client.generate_insights(profiler, file.filename or "", rows, cols)

    preview = sanitize_for_json(preview)
    charts = sanitize_for_json(charts)
    profiler = sanitize_for_json(profiler)
    insights_raw = sanitize_for_json(insights_result.model_dump())
    # insights_raw is guaranteed non-None (sanitize_for_json returns original type for dicts)
    insights_data: dict = insights_raw  # type: ignore[assignment]

    dataset_id = str(uuid.uuid4())
    datasets[dataset_id] = df

    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "rows": rows,
        "columns": cols,
        "column_names": col_names,
        "preview": preview,
        "charts": charts,
        "profiles": profiler,
        "summary": insights_data["summary"],
        "insights": insights_data["insights"],
    }
class AskRequest(BaseModel):
    dataset_id: str
    question: str

@app.post("/ask")
async def ask(request:AskRequest) -> AskResponse:
    return await ask_data(request)