import os
import sys
import json
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from dotenv import load_dotenv
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

load_dotenv()

FPT_API_KEY = os.getenv("FPT_CLOUD_API_KEY")
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"


def try_parse_tool_call(text: str):
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "name" in data and "arguments" in data:
            return data
    except Exception:
        pass
    return None


class MCPClient:
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()

        self.llm = ChatOpenAI(
            model=MODEL_NAME,
            api_key=FPT_API_KEY,
            base_url="https://mkp-api.fptcloud.com/v1",
            temperature=1.0,
            max_tokens=1024,
        )

        self.mcp_tools = []

    async def connect_to_server(self, server_script_path: str):
        """Connect to MCP server"""

        path = Path(server_script_path).resolve()

        server_params = StdioServerParameters(
            command=sys.executable,
            args=[path.name],
            env=None,
        )

        read, write = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self.session.initialize()

        # Discover tools
        tools = await self.session.list_tools()
        for tool in tools.tools:
            self.mcp_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                }
            })

        print("\nConnected to server with tools:",
              [t["function"]["name"] for t in self.mcp_tools])

    async def process_query(self, query: str) -> str:
        """Process a user query via LLM + MCP tools"""

        messages = [
            SystemMessage(
                content="Use tools when helpful. "
                        "If a tool is used, wait for its result before answering."
            ),
            HumanMessage(content=query),
        ]

        print("REACHED HERE @1")
        response = self.llm.invoke(messages, tools=self.mcp_tools)
        print("REACHED HERE @2")
        print(response)

        # OpenAI-style tool calls (LangChain)
        tool_calls = response.additional_kwargs.get("tool_calls")
        parsed_tool = None
        if not tool_calls:
            parsed_tool = try_parse_tool_call(response.content)

        if tool_calls or parsed_tool:

            print("REached here @3")

            calls = tool_calls or [{
                "id": "fallback",
                "function": {
                    "name": parsed_tool["name"],
                    "arguments": json.dumps(parsed_tool["arguments"]),
                }
            }]

            print("Reached here @4")

            for call in calls:
                tool_name = call["function"]["name"]
                tool_args = json.loads(call["function"]["arguments"])

                print(f"[Tool call detected] {tool_name}({tool_args})")

                result = await self.session.call_tool(tool_name, tool_args)
                print("Reached here @5")

                print(result.content)

                tool_text = "".join(
                    c.text for c in result.content if c.type == "text"
                )
                print("Reached here @6")


                messages.append(response)
                messages.append(
                    ToolMessage(
                        tool_call_id=call["id"],
                        content=tool_text,
                    )
                )

            final_response = self.llm.invoke(messages)
            return final_response.content

        print("REACHED HERE @3")
        return response.content


    
    '''
    # Process response and handle tool calls
    final_text = []

    assistant_message_content = []
    for content in response.content:
        if content.type == 'text':
            final_text.append(content.text)
            assistant_message_content.append(content)
        elif content.type == 'tool_use':
            tool_name = content.name
            tool_args = content.input

            # Execute tool call
            result = await self.session.call_tool(tool_name, tool_args)
            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

            assistant_message_content.append(content)
            messages.append({
                "role": "assistant",
                "content": assistant_message_content
            })
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": result.content
                    }
                ]
            })
            '''

    async def chat_loop(self):
        """Interactive CLI loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == "quit":
                    break

                answer = await self.process_query(query)
                print("\n" + answer)

            except Exception as e:
                print(f"\nError: {e}")

    async def cleanup(self):
        """Cleanup MCP resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
