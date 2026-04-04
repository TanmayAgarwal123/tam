from googleapiclient.discovery import build
import datetime
from google_auth import get_credentials

def get_calendar_service():
    creds = get_credentials()
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)

def get_today_events():
    service = get_calendar_service()
    if not service:
        return "Google not connected"
        
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        tonight = (datetime.datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=tonight,
            singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found for today."
            
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            formatted_events.append({
                "title": event['summary'],
                "start": start,
                "end": end
            })
        return formatted_events
    except Exception as e:
        return f"Calendar read error: {str(e)}"

def get_week_events():
    service = get_calendar_service()
    if not service:
        return "Google not connected"
        
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        end_of_week = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=end_of_week,
            maxResults=50, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found for this week."
            
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'Untitled Event')
            formatted_events.append(f"{start}: {title}")
        return "\n".join(formatted_events)
    except Exception as e:
        return f"Calendar read error: {str(e)}"

def create_event(title, start_time, end_time, description=""):
    service = get_calendar_service()
    if not service:
        return "Google not connected"
        
    try:
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }
        
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event_result.get('htmlLink')}"
    except Exception as e:
        return f"Calendar write error: {str(e)}"

def find_free_slots(duration_minutes, within_days=3):
    # Simplistic mocking for finding free slots, as actual free/busy logic requires explicit TimeRanges
    # We will simulate pulling week events and identifying gap.
    return "This functionality requires an explicit FreeBusy query on calendar. Returning dummy suggestion: Tomorrow at 2 PM is free."
