import sys
import os
from dotenv import load_dotenv

class WarningFilter:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        if "Warning: there are non-text parts" in data:
            return
        if "Check the full candidates.content.parts accessor" in data:
            return
        if "['function_call'], returning concatenated text result" in data:
            return
        self.stream.write(data)

    def flush(self):
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = WarningFilter(sys.stdout)
sys.stderr = WarningFilter(sys.stderr)

load_dotenv()

import asyncio
import threading
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

class McpWrapper:
    def __init__(self):
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=["salesforce_mcp.py"]
        )
        self.exit_stack = None

    async def _init_async(self):
        from contextlib import AsyncExitStack
        self.exit_stack = AsyncExitStack()
        read, write = await self.exit_stack.enter_async_context(stdio_client(self.server_params))
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    def start(self):
        # Create a dedicated background event loop for MCP
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        asyncio.run_coroutine_threadsafe(self._init_async(), self.loop).result()

    def call_tool(self, name, args):
        future = asyncio.run_coroutine_threadsafe(self.session.call_tool(name, arguments=args), self.loop)
        return future.result().content[0].text

wrapper = McpWrapper()

def start_salesforce_session(bypass_user: bool = True) -> str:
    """Start a new conversation session with a Salesforce Agent (using MCP)."""
    return wrapper.call_tool("start_session", {"bypass_user": bypass_user})

def send_message_to_salesforce(session_id: str, message: str, sequence_id: int) -> str:
    """Send a message to the Salesforce agent and get streaming response (using MCP)."""
    return wrapper.call_tool("send_message_stream", {"session_id": session_id, "message": message, "sequence_id": sequence_id})

def end_salesforce_session(session_id: str) -> str:
    """End a Salesforce Agent session (using MCP)."""
    return wrapper.call_tool("end_session", {"session_id": session_id})

def main():
    print("🔄 Starting MCP Server Subprocess...")
    try:
        wrapper.start()
        print("✅ MCP Server Connected.")
    except Exception as e:
        print(f"❌ Failed to connect to MCP Server: {e}")
        return

    print("🔄 Starting Google Orchestrator...")
    google_orchestrator = LlmAgent(
        name="Google_Primary_Assistant",
        model="gemini-2.5-flash",
        instruction=(
            "You are an enterprise orchestrator. "
            "You have tools connected to a Salesforce Agent. "
            "If the user asks to perform any CRM task: "
            "1. start_salesforce_session (default bypass_user=True) to get a session_id. "
            "2. send_message_to_salesforce using that session_id to perform the task. Keep track of the sequence_id (starts at 1). "
            "3. Return the response to the user. "
            "4. end_salesforce_session when you are completely done answering."
        ),
        tools=[start_salesforce_session, send_message_to_salesforce, end_salesforce_session]
    )
    print("✅ Google Orchestrator ready.\n")

    # Create the runner
    runner = Runner(
        app_name="salesforce_app",
        agent=google_orchestrator,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    session_id = "cli-session"
    user_id = "cli-user"
    
    print("-" * 50)
    print("🤖 Chat Session Started. Type 'exit' or 'quit' to end.")
    print("-" * 50)

    # Interactive CLI Loop
    while True:
        user_prompt = input("\nYou: ")
        if user_prompt.strip().lower() in ['exit', 'quit']:
            print("Ending session. Goodbye!")
            break
        
        if not user_prompt.strip():
            continue

        print("Agent: ", end="", flush=True)
        try:
            # Stream the response back to the terminal
            for event in runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part.from_text(text=user_prompt)]),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Only access text if it's not a function call to avoid internal SDK warnings
                        if hasattr(part, 'function_call') and part.function_call:
                            continue
                        if hasattr(part, 'text') and part.text:
                            print(part.text, end="", flush=True)
            print() # Print a newline when the stream finishes
        except Exception as e:
            print(f"\n[Error communicating with agent: {e}]")

if __name__ == "__main__":
    main()