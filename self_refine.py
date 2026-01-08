import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GENAI_API_KEY")) 

model = genai.GenerativeModel('gemini-2.5-flash')   

def self_refine(prompt, max_iterations=3):
    current_prompt = prompt
    responses = []

    for i in range(1, max_iterations + 1):
        response = model.generate_content(current_prompt)
        content = response.candidates[0].content.parts[0].text.strip()


        print(f"\n--- Iteration {i} ---")
        print(content)

        responses.append(content)

        # Ask the model to refine its own previous answer
        current_prompt = (
            "Please improve and refine the following response. "
            "Make it clearer, more accurate, and more concise:\n\n"
            f"{content}"
        )

    return responses


# Example usage
prompt = input("Enter your prompt: ")
result = self_refine(prompt)
#print("Final Response:", result)
