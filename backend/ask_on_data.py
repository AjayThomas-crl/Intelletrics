from dataset_store import datasets
from ai_insights import get_provider_chain
from pydantic import BaseModel, field_validator
from fastapi import HTTPException

class AskResponse(BaseModel):
    answer: str | int | float

    @field_validator("answer", mode="before")
    @classmethod
    def coerce_answer(cls, v: object) -> str:
        return str(v) if not isinstance(v, str) else v

async def ask_data(request):
    ai_client = get_provider_chain()
    df=datasets.get(request.dataset_id)

    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found. The server may have restarted — please re-upload your file.")

    prompt=f"""
Dataset:
{df.to_markdown(index=False)}

Question:
{request.question}

             """

    response= await ai_client.generate_structured(prompt,AskResponse)
    return response