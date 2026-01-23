import os
import requests
from typing import Optional, List, TypedDict, Any, Annotated
import operator
from dotenv import load_dotenv

from langchain_core.language_models.llms import LLM
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from langgraph.types import interrupt
from langgraph.checkpoint.memory import MemorySaver

from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
import numpy as np

#model to score the response
import google.generativeai as genai
load_dotenv()
'''
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
judge_model = genai.GenerativeModel(
    model_name="gemini-2.5-pro",
)
'''

class FinalAnswerResponse(BaseModel):
    answer: str = Field(..., description="The final answer extracted from the model's response.")

class ExtractScoreResponse(BaseModel):
    score: float = Field(..., description="The score extracted from the model's evaluation response.")

final_answer_parser = PydanticOutputParser(pydantic_object=FinalAnswerResponse)
extract_score_parser = PydanticOutputParser(pydantic_object=ExtractScoreResponse)


FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
API_URL = "https://mkp-api.fptcloud.com/v1/chat/completions"
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"


# Custom FPT LLM
class FPTCloudLLM(LLM):
    api_key: str
    model_name: str
    api_url: str

    def _llm_type(self) -> str:
        return "fptcloud"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        headers = {
            "Authorization": f"Bearer {FPT_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", 
                 "content": prompt}
            ],
            "system_prompt": "You are a very helpful and respectful assistant. Please use formal and appropriate language when responding",
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
    
class State(TypedDict):
    task_description: str
    answer: Annotated[list[str], operator.add]
    decision: str
    score: float
    number_of_options: int
    selected_answer: int
    final_answer: str

# Generate the initial answer
def answer_generation(state: State) -> State:
    llm = FPTCloudLLM(
        api_key=FPT_API_KEY,
        api_url=API_URL,
        model_name=MODEL_NAME,  
    )

    outcomes = [1, 2, 3]
    probabilities = [0.45, 0.35, 0.2]
    random_number_of_outputs = np.random.choice(outcomes, p=probabilities, size=1)[0]


    answers = []
    for _ in range(random_number_of_outputs):
        answer = llm.invoke(f"Complete the following task: \n\n{state['task_description']}")
        answers.append(answer)

    return {"answer": answers, "number_of_options": len(answers)}

# Select which answer when there are multiple options
def select_answer(state: State) -> State:
    answers = state["answer"]
    number_of_options = len(state["answer"])

    if number_of_options == 1:
        return {
            "answer": [answers[0]],
            "number_of_options": 1,
        }
    
    return interrupt(
        {
            "question": "Which answer do you prefer?",
            "answer": [
                {"option_number": i, "answer": answer}
                for i, answer in enumerate(answers, start=1)
                    ],
                    "instructions": "Please select the option number of your preferred answer.",
                    })


def apply_selected_answer(state: State) -> State:
    answer_index = state["selected_answer"] - 1
    selected_answer = state["answer"][answer_index]
    return {
        "final_answer": [selected_answer],
        "number_of_options": len(state["answer"]), 
    }

# Involve human in the loop for approval
def human_in_loop(state: State) -> State:
    return interrupt(
        {
            "question": "Do you accept this answer?",
            "answer": state["answer"],
            "options": ["approve", "refine"],
        }
    )

# Refine the answer based on human feedback
def refine_answer(state: State) -> State:
    llm = FPTCloudLLM(
        api_key=FPT_API_KEY,
        api_url=API_URL,
        model_name=MODEL_NAME,
    )

    refine_prompt = f""" The previous answer was: {state['answer']}
    Please refine the answer to better complete the task: {state['task_description']}.
    Explain which part of the original answer you are refining and why.
    Provide the refined answer below:"""

    refined_answer = llm.invoke(refine_prompt)
    return {"answer": [refined_answer]}


def judge_score(state: State) -> State:

    llm = FPTCloudLLM(
        api_key=FPT_API_KEY,
        api_url=API_URL,
        model_name="gemma-3-27b-it",
    )

    answer = state["answer"]

    prompt = f"""
    You are a fair evaluator. Score the following response on a scale of 1 to 10,
    where 1 is poor and 10 is excellent.
    Task:
    {state['task_description']}

    Response:
    {answer}

    Respond ONLY in JSON format as follows:
    {extract_score_parser.get_format_instructions()}
    """

    response_text = llm.invoke(prompt)
    parsed = extract_score_parser.parse(response_text)

    print(f"Judged answer score: {parsed.score}")

    return {
        "answer": [answer],
        "score": parsed.score,
        "number_of_options": 1,
    }


# Decision function to determine next step
def decision(state: State):
    if state["decision"] == "approve":
        return END
    if state["decision"] == "refine":
        return "refine"
    
def route_after_scoring(state: State):
    if state["score"] >= 9.0:
        return END
    else:
        return "approve"
    
def finalise(state: State) -> State:
    return {
        "final_answer": state["answer"][0]
    }
    

builder = StateGraph(State)
builder.add_node("generate", answer_generation)
builder.add_node("approve", human_in_loop)
builder.add_node("refine", refine_answer)
builder.add_node("judge", judge_score)
builder.add_node("select", select_answer)
builder.add_node("apply_selection", apply_selected_answer)
builder.add_node("finalise", finalise)

builder.set_entry_point("generate")
# builder.add_edge("generate", "judge")
# builder.add_edge("generate", "select")
builder.add_edge("apply_selection", END)
builder.add_edge("refine", "approve")
builder.add_edge("finalise", END)
builder.add_edge("select", "apply_selection")

builder.add_conditional_edges(
    "approve",
    lambda s: "finalise" if s["decision"] == "approve" else "refine",
    {
        "finalise": "finalise",
        "refine": "refine",
    },
)

builder.add_conditional_edges(
    "judge",
    route_after_scoring,
    {
        END: END,
        "approve": "approve",
    },
)

builder.add_conditional_edges(
    "generate",
    lambda state: "select" if len(state["answer"]) > 1 else "judge",
    {
        "select": "select",
        "judge": "judge",
    }
)

'''
builder.add_conditional_edges(
    "approve",
    decision,
    {
        "refine": "refine",
        END: END,
    },
)
'''

checkpoint = MemorySaver()
agent = builder.compile(checkpointer=checkpoint)

mermaid_code = agent.get_graph().draw_mermaid()
print(mermaid_code)

"""
def main():
    task = input("Enter the task you need help with: ")

    config = {"configurable": {"thread_id": "human_in_loop_thread"}}

    stream = agent.stream({"task_description": task}, config=config, stream_mode=["updates"])

    while True:
        stopped = False

        # first run (will interrupt for human feedback)
        for mode, chunk in stream:
            if mode == "updates" and "__interrupt__" in chunk:
                stopped = True

                raw_interrupt = chunk["__interrupt__"]
                interrupt_data = (
                    raw_interrupt[0]
                    if isinstance(raw_interrupt, tuple)
                    else raw_interrupt
                )

                print("\n--- Human Approval Required ---")
                print("Answer:\n")
                print(interrupt_data.value["answer"])

                decision = input("\nDecision (approve/refine): ").strip().lower()
                while decision not in ["approve", "refine"]:
                    print("Invalid decision. Please enter 'approve' or 'refine'.")
                    decision = input("Decision (approve/refine): ").strip().lower()
                stream = agent.stream(
                    Command(resume={"decision": decision}), 
                    config=config,
                    stream_mode=["updates"])
                
                break

        if not stopped:
            break

        print ("\n--- Final Answer ---")
        print (agent.get_state(config).values["answer"])

if __name__ == "__main__":
    main()

"""