import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv(override=True)

def get_slack_client():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return None
    return WebClient(token=token)

def read_channel(channel_name: str, limit: int = 10):
    client = get_slack_client()
    if not client:
        return "Slack not connected."
        
    try:
        # Resolve channel name to ID
        response = client.conversations_list(types="public_channel,private_channel")
        channels = response.get("channels", [])
        channel_id = None
        for c in channels:
            if c["name"] == channel_name:
                channel_id = c["id"]
                break
                
        if not channel_id:
            return f"Error: Channel '{channel_name}' not found."
            
        history = client.conversations_history(channel=channel_id, limit=limit)
        messages = history.get("messages", [])
        if not messages:
            return f"No messages in #{channel_name}."
            
        formatted = []
        for m in messages:
            text = m.get("text", "")
            user = m.get("user", "Unknown")
            formatted.append(f"[{user}]: {text}")
            
        return "\n".join(formatted)
        
    except SlackApiError as e:
        return f"Slack Error: {e.response['error']}"

def post_message(channel_name: str, text: str):
    client = get_slack_client()
    if not client:
        return "Slack not connected."
        
    try:
        response = client.conversations_list(types="public_channel,private_channel")
        channels = response.get("channels", [])
        channel_id = None
        for c in channels:
            if c["name"] == channel_name:
                channel_id = c["id"]
                break
                
        if not channel_id:
            return f"Error: Channel '{channel_name}' not found."
            
        client.chat_postMessage(channel=channel_id, text=text)
        return f"Successfully posted to #{channel_name}."
        
    except SlackApiError as e:
        return f"Slack Error: {e.response['error']}"

def search_messages(query: str):
    client = get_slack_client()
    if not client:
        return "Slack not connected."
        
    try:
        response = client.search_messages(query=query, count=5)
        matches = response.get("messages", {}).get("matches", [])
        if not matches:
            return f"No messages found for '{query}'."
            
        formatted = []
        for m in matches:
            text = m.get("text", "")
            channel = m.get("channel", {}).get("name", "Unknown")
            formatted.append(f"[#{channel}]: {text}")
            
        return "\n".join(formatted)
        
    except SlackApiError as e:
        return f"Slack Error: {e.response['error']}"
