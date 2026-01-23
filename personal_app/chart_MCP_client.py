'''
import json
import asyncio
from typing import Literal, Optional
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import sys

load_dotenv()
FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=FPT_API_KEY,
    base_url="https://mkp-api.fptcloud.com/v1",
    temperature=0,
)

class ToolDecison(BaseModel):
    tool_name: str
    arguments: dict
    reason: Optional[str]

structured_llm = llm.with_structured_output(ToolDecison)
DECISION_PROMPT = PromptTemplate(
    template="""

You are a chart decision-making assistant.

Available tools:
{tools}

Rules:
- If the data contains latitude/longitude AND population, then you use plotly to draw population bubble chart
- If the user asks for a map, geographic, globe, world -> use plotly
- Otherwise, use vegalite to represent data in an analytic chart
- Output JSON only

User Question:
{question}

Data:
{data}

""",
    input_variables=["tools", "question", "data"],
)

def load_file(path: Path):
    text = path.read_text(encoding="utf-8").strip()

    if text.startswith("["):
        return json.loads(text)
    
    return json.loads(f"[{text}]")

server_script_path = "chart_MCP_server.py"
path = Path(server_script_path).resolve()
server_params = StdioServerParameters(
    command=sys.executable,
    args=[path.name],
    env=None,
)

def is_insufficient_data(data):
    if not data:
        return True
    if isinstance(data, list) and len(data) > 0:
        first_item = data[0]
        if isinstance(first_item, dict) and len(first_item) == 1:
            return True
    return False

async def main():
    print ("----------Chart MCP Client-----------")

    while True:
        file_input = input("Enter the data file: ")
        path = Path(file_input)

        if not path.exists():
            print("File cannot be found!")
            continue
        try:
            data = load_file(path)
            if not isinstance(data, list):
                raise ValueError("Data must be a list!")
            break
        except Exception as e:
            print ("Failed to load data from the file!")

    print("Successfully loaded data from file!")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = []

            tools = await session.list_tools()

            print("REached here @1")
            for tool in tools.tools:
                mcp_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                })

            print (mcp_tools)

            tool_description = "\n".join(
            f"""Tool name: {t['function']['name']}
            Description: {t['function']['description']}
            Parameters schema: {json.dumps(t['function']['parameters'], indent=2)} """
            for t in mcp_tools
            )
                
            print("\nConnected to server with tools:",
                  [t["function"]["name"] for t in mcp_tools])

            print("Type the question you want to ask!\n")
            print("Type quit to end!\n")

            while True:
                question = input("Enter your question: ").strip()
                if question.lower() in ["quit"]:
                    break
                
                decision = structured_llm.invoke(

                    DECISION_PROMPT.format(
                        tools = tool_description,
                        question=question,
                        data = json.dumps(data[:3], ensure_ascii=False),
                    )
                )

                print(f"--Tool selected: {decision.tool_name}")
                print(f"--Selection Reason: {decision.reason}")
                print(f"--Argumnets: {json.dumps(decision.arguments)}")

            
                if is_insufficient_data(data):
                    print("No chart generated due to insufficient data.")
                    continue

                # Otherwise call the tool
                result = await session.call_tool(
                    decision.tool_name, decision.arguments,
)


                result = await session.call_tool(
                    decision.tool_name, decision.arguments,
                )
                
                print(f"Raw MCP result: {result.content}")
                
                # 1. Extract text from TextContent
                text_payload = "".join(
                    c.text for c in result.content if c.type == "text"
                )

                # 2. Parse JSON
                payload = json.loads(text_payload)

                print(f"PAYLOAD: {payload}\n")

                print(f"Chart generated: {payload['id']}")

                print()

asyncio.run(main())
'''

import json
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Literal

from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

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
    tool_name: Literal["plotly_chart", "vegalite_chart", "none"]
    arguments: Optional[dict] = None
    reason: str

structured_llm = llm.with_structured_output(ToolDecision)

DECISION_PROMPT = PromptTemplate(
    template="""
You are a chart decision-making assistant.

Available tools:
{tools}

Rules:
- If the data is empty, incomplete, missing required fields, or cannot form a meaningful chart → select tool_name = "none"
- If the data contains latitude AND longitude AND population → use plotly to draw a population bubble chart
- If the user asks for a map, geographic, globe, or world visualization → use plotly
- Otherwise, use vegalite to generate an analytical chart
- If tool_name is "none", arguments MUST be null
- Always explain your reasoning clearly
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

server_script_path = "chart_MCP_server.py"
server_path = Path(server_script_path).resolve()

server_params = StdioServerParameters(
    command=sys.executable,
    args=[server_path.name],
    env=None,
)

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

            print(
                "\nConnected to server with tools:",
                [t["function"]["name"] for t in mcp_tools],
            )

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

                # Extract text payload
                text_payload = "".join(
                    c.text for c in result.content if c.type == "text"
                )

                payload = json.loads(text_payload)

                print("\nParsed payload:", payload)
                print(f"Chart generated with ID: {payload.get('id')}")
                print()


if __name__ == "__main__":
    asyncio.run(main())



