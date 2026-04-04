import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv(override=True)

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

REDIRECT_URI = "http://localhost:8000/auth/google/callback"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "google_credentials.json")

def get_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                creds_data = json.load(f)
                return Credentials.from_authorized_user_info(creds_data, SCOPES)
        except:
            return None
    return None

_global_flow = None

def get_flow():
    global _global_flow
    if _global_flow is None:
        client_secret_path = os.path.join(os.path.dirname(__file__), "client_secret.json")
        if not os.path.exists(client_secret_path):
            raise FileNotFoundError(f"Missing {client_secret_path}! Download from Google Cloud Console.")
            
        _global_flow = Flow.from_client_secrets_file(
            client_secret_path,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    return _global_flow

@router.get("/auth/google")
async def auth_google():
    try:
        flow = get_flow()
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )
        return RedirectResponse(auth_url)
    except Exception as e:
        return {"error": str(e)}

@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    # Get the full URL including query params securely without strict injection rules
    code = request.query_params.get("code")
    
    if not code:
        return {"error": "No code received", "params": dict(request.query_params)}
    
    try:
        # Reuse the exact same flow instance so the PKCE code_verifier is preserved!
        flow = get_flow()
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Save credentials to disk natively as parsed by SDK
        creds_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        os.makedirs(os.path.dirname(CREDENTIALS_FILE), exist_ok=True)
        with open(CREDENTIALS_FILE, "w") as f:
            json.dump(creds_data, f)
        
        return {"status": "Google connected successfully. Gmail and Calendar are now active."}
    except Exception as e:
        return {"error": str(e)}
