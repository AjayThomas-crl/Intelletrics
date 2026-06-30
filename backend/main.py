from fastapi import FastAPI , UploadFile,File
import shutil
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware


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

    
    rows,cols=df.shape
    col_names=df.columns.to_list()
    preview=df.head(10).to_dict(orient="records")
    return {"filename":file.filename,
            "content_type": file.content_type,"rows":rows,
            "columns":cols,"column_names":col_names, "preview":preview}