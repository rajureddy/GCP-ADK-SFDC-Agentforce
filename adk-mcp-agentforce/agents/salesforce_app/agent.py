import sys
import os
import asyncio
import threading
from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession

load_dotenv()

class McpWrapper:
    def __init__(self):
        mcp_script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "salesforce_mcp.py")
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[mcp_script_path]
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

print("🔄 Starting MCP Server Subprocess...")
wrapper = McpWrapper()
try:
    wrapper.start()
    print("✅ MCP Server Connected.")
except Exception as e:
    print(f"❌ Failed to connect to MCP Server: {e}")

def start_salesforce_session(bypass_user: bool = True) -> str:
    """Start a new conversation session with a Salesforce Agent (using MCP)."""
    return wrapper.call_tool("start_session", {"bypass_user": bypass_user})

def send_message_to_salesforce(session_id: str, message: str, sequence_id: int) -> str:
    """Send a message to the Salesforce agent and get streaming response (using MCP)."""
    return wrapper.call_tool("send_message_stream", {"session_id": session_id, "message": message, "sequence_id": sequence_id})

def end_salesforce_session(session_id: str) -> str:
    """End a Salesforce Agent session (using MCP)."""
    return wrapper.call_tool("end_session", {"session_id": session_id})

root_agent = LlmAgent(
    name="Google_Primary_Assistant",
    model="gemini-2.5-flash",
    instruction=(
        "You are an enterprise orchestrator. "
        "You have tools connected to a Salesforce Agent. "
        "If the user asks to perform any CRM task: "
        "1. start_salesforce_session (default bypass_user=True) to get a session_id. "
        "2. send_message_to_salesforce using that session_id to perform the task. Keep track of the sequence_id (starts at 1). "
        "3. Wait for the tool response and return ONLY the EXACT verbatim output provided by the salesforce agent. Do not prefix your response with phrases like 'The agent says' or 'attempting to connect'. Act strictly as a transparent proxy for the salesforce agent output. "
        "4. end_salesforce_session when you are completely done answering."
    ),
    tools=[start_salesforce_session, send_message_to_salesforce, end_salesforce_session]
)

