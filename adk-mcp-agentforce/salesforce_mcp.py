import os
from dotenv import load_dotenv
load_dotenv()

import json
import httpx
import httpx_sse
import uuid
import sys
from mcp.server.fastmcp import FastMCP
from auth import get_salesforce_token

mcp = FastMCP("Salesforce Agent API Server")

# The standard Einstein Agent API endpoint
def get_base_url():
    sfApiHost = os.getenv("SF_API_HOST_URL", "api.salesforce.com")
    return f"https://{sfApiHost}/einstein/ai-agent/v1"

def get_org_domain():
    domain = os.getenv("SF_DOMAIN")
    if not domain:
        raise ValueError("SF_DOMAIN environment variable is missing.")
    return f"https://{domain}"

@mcp.tool()
async def start_session(bypass_user: bool = True) -> str:
    """
    Start a new conversation session with a Salesforce Agent.
    
    Args:
        bypass_user: True to use the agent-assigned user, False to use token's user.
        
    Returns:
        JSON string containing the new session ID.
    """
    agent_id = os.getenv("AGENT_ID") or os.getenv("Agent_Id")
    if not agent_id:
        raise ValueError("AGENT_ID environment variable is missing. Please set it in your .env")
    token = get_salesforce_token()
    base_url = get_base_url()
    org_domain = get_org_domain()
    
    url = f"{base_url}/agents/{agent_id}/sessions"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "externalSessionKey": str(uuid.uuid4()),
        "instanceConfig": {
            "endpoint": org_domain
        },
        "bypassUser": bypass_user,
        "streamingCapabilities": {
            "chunkTypes": ["Text"]
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return json.dumps({"session_id": data.get("sessionId"), "raw_response": data})

@mcp.tool()
async def send_message_stream(session_id: str, message: str, sequence_id: int) -> str:
    """
    Send a message to an active Salesforce Agent session and stream the response.
    Returns the concatenated output from the Agent.
    
    Args:
        session_id: The ID of the active session.
        message: The user's input message to send to the CRM agent.
        sequence_id: Message sequence number (incremented for each turn).
        
    Returns:
        The final aggregated string response from the Agent.
    """
    token = get_salesforce_token()
    base_url = get_base_url()
    
    url = f"{base_url}/sessions/{session_id}/messages/stream"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    payload = {
        "message": {
            "sequenceId": sequence_id,
            "type": "Text",
            "text": message
        },
        "variables": []
    }
    
    full_response = []
    
    async with httpx.AsyncClient() as client:
        # Use httpx_sse to consume the streaming Server-Sent Events from Salesforce
        async with httpx_sse.aconnect_sse(client, "POST", url, headers=headers, json=payload) as event_source:
            async for event in event_source.aiter_sse():
                # Salesforce returns 'ProgressIndicator', 'TextChunk', 'Inform', 'EndOfTurn'
                event_type = event.event
                
                if event_type == "TextChunk":
                    try:
                        chunk_data = json.loads(event.data)
                        text = chunk_data.get("text", "")
                        if text:
                            full_response.append(text)
                            # Print to stderr to show it's streaming (MCP uses stdout for json-rpc)
                            print(text, end="", flush=True, file=sys.stderr)
                    except json.JSONDecodeError:
                        pass
                elif event_type == "END_OF_TURN":
                    print("\n[Salesforce Agent Turn Ended]", file=sys.stderr)
                    break
                elif event_type == "INFORM":
                    try:
                        info_data = json.loads(event.data)
                        msg_type = info_data.get("message", {}).get("type", "")
                        if msg_type == "Inform":
                            msg_text = info_data.get("message", {}).get("message", "")
                            if not full_response and msg_text:
                                full_response.append(msg_text)
                                print(msg_text, end="", flush=True, file=sys.stderr)
                    except json.JSONDecodeError:
                        pass
                elif event_type == "PROGRESS_INDICATOR":
                    pass
                
    return "".join(full_response)

@mcp.tool()
async def end_session(session_id: str) -> str:
    """
    Ends an active Salesforce Agent interaction session.
    
    Args:
        session_id: The session ID to terminate.
    """
    token = get_salesforce_token()
    base_url = get_base_url()
    
    url = f"{base_url}/sessions/{session_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "x-session-end-reason": "UserRequest"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
        response.raise_for_status()
        return json.dumps({"status": "success", "session_id": session_id})

if __name__ == "__main__":
    # We use stdio to communicate with the orchestrator
    mcp.run("stdio")
