# GCP ADK MCP Agentforce Integration

This project demonstrates a powerful integration between the **Google Agent Development Kit (ADK)** and the **Salesforce Einstein AI Agent (Agentforce)** using the **Model Context Protocol (MCP)**. 

By leveraging MCP, we decouple the complex Salesforce API nuances (such as HTTP Server-Sent Events, authentication, and endpoint configuration) from the underlying orchestrator, providing a flexible and stable environment for multi-agent interaction.

## Architecture Highlights
- **Google ADK Orchestrator (`agents/salesforce_app/agent.py`)**: A standard `LlmAgent` orchestrator utilizing `gemini-2.5-flash` that routes intents and actions.
- **FastMCP Server (`salesforce_mcp.py`)**: A dedicated Model Context Protocol server exposing specific Salesforce Agent capabilities as standardized tools (`start_session`, `send_message_stream`, and `end_session`).
- **Standardized IO**: The orchestrator communicates securely with the MCP server over `stdio`.
- **OAuth Integration (`auth.py`)**: Uses the Salesforce OAuth2 Client Credentials flow for secure, headless authentication.

## Prerequisites
- Python 3.9+
- A valid Google Gemini API key
- A Salesforce instance with an Agentforce/Einstein AI Agent configured
- A Salesforce Connected App configured for the Client Credentials OAuth flow

## Installation

1. **Clone the repository and navigate to the directory**
   ```bash
   cd adk-mcp-agentforce
   ```

2. **Install the dependencies**
   Install the required libraries listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the root directory modeled after your setup. It requires the following keys:
   ```env
   # Google GenAI Key
   GEMINI_API_KEY=your_gemini_api_key

   # Salesforce Connected App Credentials (Client Credentials Flow)
   SF_CLIENT_ID=your_salesforce_client_id
   SF_CLIENT_SECRET=your_salesforce_client_secret
   SF_DOMAIN=your-domain.my.salesforce.com

   # Salesforce Einstein AI Agent ID
   AGENT_ID=your_agentforce_agent_id

   # (Optional) API Host URL, defaults to api.salesforce.com
   # SF_API_HOST_URL=api.salesforce.com
   ```

## Usage

Start the Google ADK Web Dashboard by running the ADK CLI:

```bash
py -m google.adk.cli web agents
```

### What happens under the hood?
1. The agent initialization automatically boots up the FastMCP server (`salesforce_mcp.py`) as a subprocess.
2. The Google Orchestrator binds to the MCP server.
3. When you submit a request (e.g., *"I want to talk to a CRM expert"*), the Gemini orchestrator detects that CRM context is required.
4. Gemini seamlessly calls the dynamic MCP tools to open a session with Agentforce, pass your messages, stream back the responses (Server-Sent Events), and wrap up the session gracefully.

## Troubleshooting

- **Empty force-config endpoint error**: Ensure `SF_DOMAIN` is correctly configured in your `.env` file without the `https://` prefix (e.g. `example.my.salesforce.com`).
- **Auth Errors**: Verify that your Salesforce Connected App allows the "Client Credentials Flow", has the correct profile permissions, and that the `Client Secret` is accurate.
- **Missing Tools / Undefined Responses**: Ensure that `salesforce_mcp.py` is successfully starting on `stdio`. Terminal logs at the boot of the web server should say `✅ MCP Server Connected.`

## License
MIT License
