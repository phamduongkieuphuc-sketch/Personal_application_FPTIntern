import os
import requests
from dotenv import load_dotenv

load_dotenv()

FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")

API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct" 

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": MODEL_NAME,
    "messages": [
        {
            "role": "user",
            "content": "generate a simple poem about love in English"
        }
    ],
    "temperature": 0.7,
    "max_tokens": 300
}

response = requests.post(
    API_URL,
    headers=headers,
    json=payload,
    timeout=30
)

response.raise_for_status()

# print response
print(response.json()["choices"][0]["message"]["content"])
