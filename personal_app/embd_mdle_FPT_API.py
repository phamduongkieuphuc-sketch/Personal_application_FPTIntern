import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
from typing import List
from langchain_core.output_parsers import PydanticOutputParser
import torch

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
img_path = "/home/william-pham/Downloads/hoa_don.png"
API_URL = "https://mkp-api.fptcloud.com/v1/embeddings"
MODEL_NAME = "multilingual-e5-large"

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
}

app = FastAPI(title="API of FPT Embedding Model")

# Get the embeddings fromm FPT model
def get_embeddings(texts, dimensions=1024):
    """
    texts: list[str]
    returns" torch.Tensor [len(texts), dimensions]
    """
    payload = {
        "model": MODEL_NAME,
        "input": texts,
        "dimensions": dimensions,
        "encoding_format": "float",
        "input_text_truncate": "none",
        "input_type": "passage",
    }

    response = requests.post(
        API_URL,
        json=payload,
        headers=headers,
    )

    response.raise_for_status()

    data = response.json()["data"]

    embeddings = [item["embedding"] for item in data]

    return torch.Tensor(embeddings)

def prompt_to_embeddings(prompt: str):
    return get_embeddings([prompt])[0]

class EmbeddingRequest(BaseModel):
    query: str

class EmbeddingResponse(BaseModel):
    query: str
    first_8_values: List[float]


embedding_history = []
@app.post("/embeddings", response_model=EmbeddingResponse)
def create_embeddings(request: EmbeddingRequest):
    try:
        embedding = prompt_to_embeddings(request.query)

        record = EmbeddingResponse(
            query=request.query,
            first_8_values=embedding[:8].tolist()
        )
        
        with open("embedding.txt", "w") as f:
            f.write(str(embedding.tolist()))

        embedding_history.append(record)
        return record
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
@app.get("/")
def home():
    return {
        "message": "Embedding API is running",
        "total_requests": len(embedding_history),
        "history": embedding_history
    }
    
