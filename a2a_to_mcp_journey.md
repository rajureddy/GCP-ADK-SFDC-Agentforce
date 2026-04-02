# Architectural Journey: From A2A to MCP for Salesforce Integration

This document outlines our technical journey in building the Agent orchestration between the Google Agent Development Kit (ADK) and the Salesforce Einstein AI Agent. It details why we initially started with the Agent-to-Agent (A2A) pattern, the specific hurdles we encountered, and the rationale behind switching to the Model Context Protocol (MCP).

## 1. Initial Approach: The A2A Pattern (A@A)

Our initial architecture attempted to leverage a direct **Agent-to-Agent (A2A)** pattern. We tried to integrate the Salesforce Agent by utilizing the native `RemoteA2aAgent` construct from the Google ADK framework. 

**The Vision:**
The orchestrator would seamlessly route user intents directly to a remote agent without needing intermediate application logic, relying entirely on the ADK's native sub-agent routing capabilities.

## 2. Challenges Faced with A2A

### Dependency and Import Errors
The most immediate roadblock was toolchain stability. We encountered persistent `ModuleNotFoundError` issues pertaining to missing `a2a` dependencies when attempting to import and initialize the `RemoteA2aAgent` inside our Python project. 

### Salesforce API Nuances
Integrating directly inside the A2A runner obfuscated our control over the HTTP requests. When calling the Salesforce Einstein AI Agent (`/v1/agents/{agent_id}/sessions`) endpoint, we encountered a `400 BadRequestException` error:
```json
"error":"BadRequestException","message":"Empty force-config endpoint"
```
Because the connection layer was abstracted by the A2A runner, it was difficult to cleanly inject environment-specific instance configurations (specifically passing the `instanceConfig.endpoint` referencing the `SF_DOMAIN`).

### Handling Streaming Responses (SSE)
The Salesforce API returns responses as Server-Sent Events (SSE) streams (`text/event-stream`). Parsing custom chunk events (like `TextChunk`, `Inform`, `EndOfTurn`) and mapping them into the ADK's expected format on the fly proved complex within the constrained `RemoteA2aAgent` interface without writing very brittle glue code.

### Resource Limits and Throttling
During testing, we experienced API rate limits. This necessitated a shift from a higher-tier model to a more accessible model (`gemini-2.5-flash`), which required rapid configuration updates that were cumbersome to weave into the black-box A2A runner setup.

## 3. The Pivot: Transitioning to the Model Context Protocol (MCP)

To overcome the friction of the A2A implementation, we pivoted to an **MCP-based architecture**. 

Instead of forcing a native A2A link, we decoupled the systems:
1. **MCP Server (`salesforce_mcp.py`)**: We built a dedicated, lightweight `FastMCP` server. This server acts as an adapter, translating standard MCP tool calls into Salesforce-specific HTTP/SSE requests.
2. **Standard LLM Orchestrator (`main.py`)**: We reverted the orchestrator back to a standard `LlmAgent` that acts as a client connected to the MCP server via `stdio`.

## 4. Why We Stick with MCP Over A2A

Our shift to MCP provided immediate architectural benefits:

* **Separation of Concerns:** The MCP Server isolates all the "messy" integration logic. We were able to explicitly manage Salesforce authentication tokens, handle the complex SSE streaming ingestion (using `httpx_sse`), and cleanly pass the required `instanceConfig.endpoint` without polluting the orchestrator.
* **Resiliency & Debuggability:** Because tools are discrete (`start_session`, `send_message_stream`, `end_session`), debugging became incredibly straightforward. We could inspect standard JSON-RPC payloads crossing the `stdio` boundary. 
* **Model Agnostic Flexibility:** The MCP server doesn't care what model or tier the orchestrator is using. When we needed to drop to `gemini-2.5-flash` to mitigate rate limits, we did it purely in the orchestrator layer without touching the Salesforce integration logic.
* **No Obscure Dependencies:** We bypassed the unstable `a2a` module completely. The MCP setup relies on well-supported, standard Python libraries (`mcp`, `httpx`), eliminating the import failures that initially blocked us.

### Conclusion
While A2A promised a native, config-driven agent-to-agent integration, the realities of third-party API nuances (SSE, strict payload requirements) and unstable library dependencies made it impractical. MCP successfully bridged this gap by treating the remote Salesforce Agent as a set of highly reliable, sandboxed tools rather than a native ADK framework entity.
