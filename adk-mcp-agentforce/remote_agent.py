import os
import httpx
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from auth import get_salesforce_token

def get_salesforce_agent():
    """Authenticates and initializes the Salesforce Remote Agent."""
    
    # 1. Get the token
    sf_token = get_salesforce_token()

    # 2. Construct the A2A endpoint using your domain
    sf_domain = os.getenv("SF_DOMAIN")
    sf_a2a_endpoint = f"https://{sf_domain}/services/a2a/v1"
    
    # 3. Create HTTPX client with Bearer token
    client = httpx.AsyncClient(
        headers={"Authorization": f"Bearer {sf_token}"}
    )

    # 4. Initialize and return the Remote Agent
    salesforce_specialist = RemoteA2aAgent(
        name="SFDC_Agent_1",
        agent_card=sf_a2a_endpoint,
        description="Specialist agent for handling CRM data, updating opportunities, and logging support cases.",
        httpx_client=client
    )
    
    return salesforce_specialist