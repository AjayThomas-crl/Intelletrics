import math
from fastapi import FastAPI , UploadFile,File
import shutil
import pandas as pd
from profiler import profile_dataframe
from chart_generator import generate_charts
from fastapi.middleware.cors import CORSMiddleware


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


app=FastAPI()


app.add_middleware(
CORSMiddleware,
allow_origins=["http://localhost:3000"],
allow_methods=[""],
allow_headers=[""],
     )
@app.get("/")
def test():
    return "working"
@app.post("/upload")
async def upload(file: UploadFile= File(...)):
    destination_path=f"saved_{file.filename}"

    with open(destination_path,"wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    if(file.filename.lower().endswith(".csv")):
        df=pd.read_csv(destination_path)
    else:
        df=pd.read_excel(destination_path)

    df = df.where(pd.notnull(df), None)
    rows,cols=df.shape
    col_names=df.columns.to_list()
    preview=df.head(10).to_dict(orient="records")
    preview = sanitize_for_json(preview)
    profiler=profile_dataframe(df)
    charts=generate_charts(df,profiler)
    charts = sanitize_for_json(charts)
    profiler = sanitize_for_json(profiler)
    return {"filename":file.filename,
            "content_type": file.content_type,"rows":rows,
            "columns":cols,"column_names":col_names, "preview":preview,"charts":charts,"profiles":profiler}
