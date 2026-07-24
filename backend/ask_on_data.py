import io

import pandas as pd
from ai_insights import get_provider_chain
from auth import UserContext
from dataset_store import datasets
from persistence import download_dataset, get_dataset
from pydantic import BaseModel, field_validator
from fastapi import HTTPException


class AskRequest(BaseModel):
    dataset_id: str
    question: str


class AskResponse(BaseModel):
    answer: str | int | float

    @field_validator("answer", mode="before")
    @classmethod
    def coerce_answer(cls, v: object) -> str:
        return str(v) if not isinstance(v, str) else v

async def ask_data(request, context: UserContext):
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
        df = pd.read_csv(io.BytesIO(raw)) if suffix == "csv" else pd.read_excel(io.BytesIO(raw))
        datasets[request.dataset_id] = {"user_id": user_id, "dataframe": df}

    ai_client = get_provider_chain()

    prompt=f"""
Dataset:
{df.to_markdown(index=False)}

Question:
{request.question}

             """

    response= await ai_client.generate_structured(prompt,AskResponse)
    return response
