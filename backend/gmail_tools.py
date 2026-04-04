from googleapiclient.discovery import build
from email.message import EmailMessage
import base64
from google_auth import get_credentials

def get_gmail_service():
    creds = get_credentials()
    if not creds:
        return None
    return build('gmail', 'v1', credentials=creds)

def read_emails(max_results=10, query="is:unread"):
    service = get_gmail_service()
    if not service:
        return "Google not connected"
        
    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No messages found matching query."
            
        formatted_emails = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            
            headers = msg_data.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "Unknown Date")
            snippet = msg_data.get("snippet", "")
            
            formatted_emails.append({
                "id": msg['id'],
                "from": sender,
                "subject": subject,
                "date": date,
                "snippet": snippet
            })
            
        return formatted_emails
    except Exception as e:
        return f"Gmail read error: {str(e)}"

def draft_reply(message_id, reply_text):
    service = get_gmail_service()
    if not service:
        return "Google not connected"
        
    try:
        # Get original message to find thread ID and sender
        orig_msg = service.users().messages().get(userId='me', id=message_id, format='metadata', metadataHeaders=['From', 'Subject', 'Message-ID']).execute()
        headers = orig_msg.get('payload', {}).get('headers', [])
        
        orig_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        orig_from = next((h['value'] for h in headers if h['name'] == 'From'), "")
        orig_msg_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), "")
        
        if not orig_subject.startswith("Re:"):
            orig_subject = "Re: " + orig_subject
            
        message = EmailMessage()
        message.set_content(reply_text)
        message['To'] = orig_from
        message['Subject'] = orig_subject
        message['In-Reply-To'] = orig_msg_id
        message['References'] = orig_msg_id
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'message': {
                'raw': encoded_message,
                'threadId': orig_msg.get('threadId')
            }
        }
        
        draft = service.users().drafts().create(userId='me', body=create_message).execute()
        return f"Draft created successfully. ID: {draft['id']}"
    except Exception as e:
        return f"Gmail draft error: {str(e)}"

def send_email(to, subject, body):
    service = get_gmail_service()
    if not service:
        return "Google not connected"
        
    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'raw': encoded_message
        }
        
        sent = service.users().messages().send(userId='me', body=create_message).execute()
        return f"Email sent successfully to {to}. ID: {sent['id']}"
    except Exception as e:
        return f"Gmail send error: {str(e)}"
