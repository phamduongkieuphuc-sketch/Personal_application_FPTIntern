import os
from dotenv import load_dotenv
import requests
from typing import Optional, List

from langchain_core.language_models.llms import LLM
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate, 
)

# Load environment variables
load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
print(FPT_API_KEY)
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

# Define a custom LLM class for FPT Cloud
class FPTCloudLLM(LLM):
    api_key: str
    model_name: str
    api_url: str

    def _llm_type(self) -> str:
        return "fptcloud"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:

        first_answer = self.get_response(prompt)
        refined_prompt = f"""
        You provided the following answer to the question: {first_answer}. Print out the old answer first.
        Please refine and improve this answer until you think it can not be improved further.
        Explain your reasoning for improvements made and where improvements were made.
        """
        refined_answer = self.get_response(refined_prompt)

        return refined_answer
    
    def get_response(self, user_prompt: str) -> str:

        headers = {
            "Authorization": f"Bearer {FPT_API_KEY}",
            "Content-Type": "application/json",
            }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", 
                 "content": user_prompt}
            ],
            "system_prompt": "You are a very helpful and respectful assistant. Please use formal language when responding",
            "streaming": False,
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 1, #nucleus sampling
            "top_k": 40, #top-k sampling
            "presence_penalty": 0, #penalize new topic
            "frequency_penalty": 0, #penalize frequent topics
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"]


PROMPT_INFO = """ Complete this task {task_description}."""

def main():
    llm = FPTCloudLLM(
        api_key=FPT_API_KEY,
        api_url=API_URL,
        model_name=MODEL_NAME,
    )

    task = input("Enter the task description you need help with: ")
    message = HumanMessagePromptTemplate.from_template(PROMPT_INFO)
    prompt = ChatPromptTemplate.from_messages([message])

    prompt_text = prompt.format_prompt(
        task_description=task
    ).to_string()

    response = llm.invoke(prompt_text)
    print(response)


if __name__ == "__main__":
    main()