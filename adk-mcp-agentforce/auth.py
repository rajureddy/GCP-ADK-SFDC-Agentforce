import os
import requests
from dotenv import load_dotenv

# Load variables from the .env file
load_dotenv()

SF_CLIENT_ID = os.getenv("SF_CLIENT_ID")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET")
SF_DOMAIN = os.getenv("SF_DOMAIN")
SF_TOKEN_URL = f"https://{SF_DOMAIN}/services/oauth2/token"

def get_salesforce_token():
    """Fetches the OAuth token using the Client Credentials flow."""
    if not SF_CLIENT_ID or not SF_CLIENT_SECRET or not SF_DOMAIN:
        raise ValueError("Missing Salesforce credentials in .env file.")

    payload = {
        'grant_type': 'client_credentials',
        'client_id': SF_CLIENT_ID,
        'client_secret': SF_CLIENT_SECRET
    }
    
    response = requests.post(SF_TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json().get('access_token')