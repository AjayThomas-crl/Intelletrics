from dataset_store import datasets
from ai_insights import get_provider_chain
from pydantic import BaseModel

class AskResponse(BaseModel):
    answer:str

async def ask_data(request):
    ai_client = get_provider_chain()
    df=datasets.get(request.dataset_id)

    prompt=f"""
Dataset:
{df.to_markdown(index=False)}

Question:
{request.question}

             """

    response= await ai_client.generate_structured(prompt,AskResponse)
    return response