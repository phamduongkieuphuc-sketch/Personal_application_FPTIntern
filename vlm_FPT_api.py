import os
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
from typing import List, Dict, Annotated
import operator
from fastapi.responses import JSONResponse
import json
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
import re

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
print("Key exist: ", bool(FPT_API_KEY))
#img_path = "/home/william-pham/Downloads/hoa_don.png"
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "gemma-3-27b-it"

HEADERS = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
}

app = FastAPI(title="VLM API")

class VisionQA(BaseModel):
    question: str = Field(description="The user's question")
    answer: str = Field(description = "The models's response to the question")

qa_parser = PydanticOutputParser(pydantic_object=VisionQA)

class VLMRequest(BaseModel):
    question: str
    image_path: str

class VLMResponse(BaseModel):
    question: str
    answer: str

class History:
    total_requests: int
    history: List[VLMResponse]

history = []

# Convert the image to base 64
def image_base64(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError("Couldn't find the selected image at path: {image_path}")
    
    with open(image_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

        img_type = image_path.lower().split(".")[-1]
        if img_type in ["jpg", "jpeg"]:
            mime = "jpeg"
        else:
            mime = img_type

        return f"data:image/{mime};base64,{encoded}"
    
def call_vlm(img_path: str, question: str) -> str:
    image_base64_url = image_base64(img_path)

    prompt = f""" You are an extremely good assistant who is well-versed in recognising and understanding images
    
    User Request:
    "{question}"

    Return ONLY in valid JSON format.
    {qa_parser.get_format_instructions()}
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_base64_url
                        }
                    }
                ]
            }
        ],
        "system_prompt": "",
        "streaming": False,
        "temperature": 0.2,
        "max_tokens": 1024,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    # print response
    return response.json()["choices"][0]["message"]["content"]

def strip_code_fences(text: str) -> str:
    return re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()

@app.post("/vlm/qa", response_model=VisionQA)
def vlm_qa(prompt_request: VLMRequest):
    raw_output = call_vlm(
        img_path=prompt_request.image_path,
        question= prompt_request.question,
    )

    record = VLMResponse(
        question=prompt_request.question,
        answer=raw_output,
    )

    clean_answer = strip_code_fences(raw_output)
    parsed = json.loads(clean_answer)
    
    record = {
        "question": parsed["question"],
        "answer": parsed["answer"]
    }
    parsed = qa_parser.parse(raw_output)
    #vlm_history.append(parsed)
    history.append(record)

    return parsed

    
@app.get("/")
def home():
    return {
        "message": "VLM API is running",
        "total_requests": len(history),
        "history": history
    }


