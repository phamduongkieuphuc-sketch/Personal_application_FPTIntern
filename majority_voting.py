import os
from dotenv import load_dotenv
import requests
from typing import Optional, List
#import re
#from collections import Counter
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

from langchain_core.language_models.llms import LLM
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate, 
)

# Load environment variables
load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

class FinalAnswerResponse(BaseModel):
    answer: str = Field(..., description="The final answer extracted from the model's response.")

class ExtractScoreResponse(BaseModel):
    score: float = Field(..., description="The score extracted from the model's evaluation response.")


final_answer_parser = PydanticOutputParser(pydantic_object=FinalAnswerResponse)
extract_score_parser = PydanticOutputParser(pydantic_object=ExtractScoreResponse)

# Define a custom LLM class for FPT Cloud
class FPTCloudLLM(LLM):
    api_key: str
    model_name: str
    api_url: str
    number_of_samples: int = 10

    def _llm_type(self) -> str:
        return "fptcloud"
    
    def build_sampling_prompt(self, prompt: str) -> str:
        return f""" {prompt} 
        {final_answer_parser.get_format_instructions()} """
    
    def build_evaluation_prompt(self, prompt: str, answer: str) -> str:
        return f""" You are a fair and very harsh evaluator. 
        Given the following prompt: {prompt}

        And the candidate answer: {answer}

        Evaluate this answer based on its correctness, relevance, and completeness.
        Provide a score from 1 to 10, where 10 is the best possible score.
        {extract_score_parser.get_format_instructions()} """
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        responses = []
        for _ in range(self.number_of_samples):
            ''' sampled_prompt = f""" {prompt}
            Respond using EXACTLY this format:
            FINAL_ANSWER: <your final answer>
            """

            response = self.get_response(sampled_prompt)
            final_answer = self.extract_final_answer(response)
            responses.append(final_answer) '''

            sampled_prompt = self.build_sampling_prompt(prompt)
            response = self.get_response(sampled_prompt)
            final_answer = final_answer_parser.parse(response)
            responses.append(final_answer.answer)

        response_scores = []
        for answer in responses:
            '''evaluation_prompt = f""" You are a fair and very good evaluator. 
            Given the following prompt: {prompt}

            And the candidate answer: {answer}

            Evaluate this answer based on its correctness, relevance, and completeness.
            Provide a score from 1 to 10, where 10 is the best possible score.
            Respond using EXACTLY this format:
            SCORE: <your score>
            """ '''

            evaluation_prompt = self.build_evaluation_prompt(prompt, answer)
            evaluation_response = self.get_response(evaluation_prompt)
            evaluation_score = extract_score_parser.parse(evaluation_response)
            response_scores.append((answer, evaluation_score.score))

            print(f"Answer: {answer} | Score: {evaluation_score.score}")
        
        # 3. Select highest-scoring answer
        best_answer, best_score = max(response_scores, key=lambda x: x[1])
        print (f"Best Answer: {best_answer} with Score: {best_score}")

        return best_answer
    
    """  def extract_final_answer(self, response: str) -> str:
        for line in response.splitlines():
            if line.strip().startswith("FINAL_ANSWER:"):
                return line.split("FINAL_ANSWER:", 1)[1].strip()
        return response.strip()
    
    def extract_score(self, response: str) -> float:
        match = re.search(r"SCORE:\s*([0-9]+(\.[0-9]+)?)", response) # extract the score expression
        if match:
            return float(match.group(1)) # capture the score
        return 0.0
    """

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
            "system_prompt": "You are a very helpful and respectful assistant.",
            "streaming": False,
            "temperature": 1,
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
    
# Prompt message
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


if __name__ == "__main__":
    main()