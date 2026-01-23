import os
import requests
from dotenv import load_dotenv
import base64


load_dotenv()

FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
img_path = "/home/william-pham/Downloads/hoa_don.png"

API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "gemma-3-27b-it" 

headers = {
    "Authorization": f"Bearer {FPT_API_KEY}",
    "Content-Type": "application/json",
}

# Convert the image to base 64
def image_base64(image_path: str) -> str:
    if not os.path.exists(img_path):
        raise FileNotFoundError("Couldn't find the selected image at path: {image_path}")
    
    with open(image_path, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

        img_type = image_path.lower().split(".")[-1]
        if img_type in ["jpg", "jpeg"]:
            mime = "jpeg"
        else:
            mime = img_type

        return f"data:image/{mime};base64,{encoded}"

image_base64_url = image_base64(img_path)
print("Type your question about the image.\n")
print("Type 'exit', 'quit', or 'q' to stop.\n")

while True:

    question = input("Ask a question about the image: ")
    if question.lower() in ["exit", "quit", "q"]:
        break

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": question
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
        "temperature": 0.7,
        "max_tokens": 1024,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0
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
