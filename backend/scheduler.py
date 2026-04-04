import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import anthropic
import os
import json
import datetime
from dotenv import load_dotenv

import calendar_tools
import gmail_tools
import slack_tools

load_dotenv()
client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

async def compile_morning_briefing():
    calendar_data = calendar_tools.get_today_events()
    email_data = gmail_tools.read_emails(max_results=5)
    slack_data = slack_tools.read_channel("general", limit=5)
    
    # Read memory if it exists
    memory_path = os.path.join(os.path.dirname(__file__), "..", "memory", "MEMORY.md")
    memory_content = ""
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory_content = f.read()

    system_prompt = "You are Tam, Tanmay's life OS."
    briefing_context = f"""
    CALENDAR TODAY: {calendar_data}
    UNREAD EMAILS: {email_data}  
    SLACK RECENT: {slack_data}
    MEMORY: {memory_content}
    
    Generate a sharp, encouraging 150-word spoken morning briefing covering the above. 
    Start with "Good morning Tanmay."
    Don't use formatting like bold or lists, as this will be read aloud. 
    """

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": briefing_context}]
    )
    
    return next((b.text for b in response.content if b.type == 'text'), "Briefing could not be generated.")

async def scheduled_morning_briefing(queue: asyncio.Queue):
    print("Initiating scheduled morning briefing...")
    text = await compile_morning_briefing()
    await queue.put({"event": "proactive_speak", "data": json.dumps({"autoSpeak": True, "text": text})})

def start_scheduler(queue: asyncio.Queue):
    scheduler = AsyncIOScheduler()
    # Schedule for 7:30 AM daily
    scheduler.add_job(scheduled_morning_briefing, 'cron', hour=7, minute=30, args=[queue])
    scheduler.start()
    print("Scheduler started!")
