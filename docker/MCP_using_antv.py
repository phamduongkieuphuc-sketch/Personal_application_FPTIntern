import json
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Literal
import requests

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import re

load_dotenv()

FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=FPT_API_KEY,
    base_url="https://mkp-api.fptcloud.com/v1",
    temperature=0,
)

class ToolDecision(BaseModel):
    tool_name: str
    arguments: Optional[dict] = None
    reason: str

structured_llm = llm.with_structured_output(ToolDecision)

DECISION_PROMPT = PromptTemplate(
    template="""
You are a chart decision-making assistant.

Available tools:
{tools}

Rules:
- Select the MOST appropriate chart tool
- If data is insufficient or meaningless → tool_name = "none"
- Use tool names EXACTLY as listed
- If the data is empty, incomplete, missing required fields, or cannot form a meaningful chart → select tool_name = "none"
- If the data contains latitude AND longitude AND population → use plotly to draw a population bubble chart
- If the user asks for a map, geographic, globe, or world visualization → use plotly
- Otherwise, use vegalite to generate an analytical chart
- Arguments MUST match the selected tool schema
- Output JSON only

User question:
{question}

Data sample:
{data}
""",
    input_variables=["tools", "question", "data"],
)

def load_file(path: Path):
    text = path.read_text(encoding="utf-8").strip()

    # Support both JSON array and line-by-line JSON
    if text.startswith("["):
        return json.loads(text)

    return json.loads(f"[{text}]")

def is_insufficent_data(data):
    return not data or (isinstance(data, list) and len(data) == 0)

# MCP server connection
server_params = StdioServerParameters(
    command="python",
    args=["chart_MCP_server.py"],
)

def extract_image_urls(text: str):
    return re.findall(r"https?://\S+", text)


def download_image(url: str, output_dir="charts", filename=None):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = "chart.png"

    output_path = Path(output_dir) / filename

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


async def main():
    print("---------- Chart MCP Client -----------")

    # Load data file
    while True:
        file_input = input("Enter the data file: ").strip()
        path = Path(file_input)

        if not path.exists():
            print("File cannot be found!")
            continue

        try:
            data = load_file(path)
            if not isinstance(data, list):
                raise ValueError("Data must be a list")
            break
        except Exception as e:
            print(f"Failed to load data: {e}")

    print("Successfully loaded data from file!")

    # MCP session
    async with stdio_client(server_params) as (read, write):
        print("REached here @1")
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools_response = await session.list_tools()
            mcp_tools = []

            for tool in tools_response.tools:
                mcp_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                })

            tool_description = "\n".join(
                f"""Tool name: {t['function']['name']}
                Description: {t['function']['description']}
                Parameters schema:
                {json.dumps(t['function']['parameters'], indent=2)}
                """
                for t in mcp_tools
            )

            print("REached here @1")
            print(mcp_tools)

            print("\nConnected to AntV MCP server")
            print("Available tools:")
            print([t["function"]["name"] for t in mcp_tools])

            print("\nType the question you want to ask!")
            print("Type 'quit' to exit.\n")

            # ----------------------------
            # Interactive loop
            # ----------------------------
            while True:
                question = input("Enter your question: ").strip()
                if question.lower() == "quit":
                    break

                decision = structured_llm.invoke(
                    DECISION_PROMPT.format(
                        tools=tool_description,
                        question=question,
                        data=json.dumps(data[:3], ensure_ascii=False),
                    )
                )

                print("\n--- LLM Decision ---")
                print(f"Tool selected : {decision.tool_name}")
                print(f"Reason        : {decision.reason}")
                print(f"Arguments     : {decision.arguments}")

                # No-tool case
                if decision.tool_name == "none":
                    print("\nNo chart generated.")
                    continue

                # MCP tool execution
                result = await session.call_tool(
                    decision.tool_name,
                    decision.arguments or {},
                )

                print("\nRaw MCP result:", result.content)
                print("REACHED HERE @2")

                # Extract text payload
                text_payload = "".join(
                    c.text for c in result.content if c.type == "text"
                ).strip()
                
                if text_payload.startswith("{"):
                    payload = json.loads(text_payload)
                    print("\nParsed payload:")
                    print(json.dumps(payload, indent=2))
                    print(f"Chart ID: {payload.get('id')}")

                # Image / map charts
                else:
                    print("\nChart output:")
                    print(text_payload)

                    urls = extract_image_urls(text_payload)

                    for url in urls:
                        if "mdn.alipayobjects.com" in url:
                            saved_path = download_image(url)
                            print(f"Image saved to: {saved_path}")
                            



if __name__ == "__main__":
    asyncio.run(main())