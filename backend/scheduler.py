import asyncio
import os
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import anthropic
import calendar_tools
import gmail_tools

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

_queue = None

def start_scheduler(queue: asyncio.Queue):
    global _queue
    _queue = queue
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_morning_briefing, 'cron', hour=7, minute=30)
    scheduler.add_job(nightly_sync, 'cron', hour=22, minute=0)
    scheduler.add_job(check_reminders, 'interval', seconds=5)
    scheduler.start()
    print("[STARTUP] Scheduler running — briefing at 7:30AM, sync at 10PM")

def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_base_dir():
    return os.path.join(os.path.dirname(__file__), "..")

def get_memory_truncated():
    memory_path = os.path.join(get_base_dir(), "memory", "MEMORY.md")
    content = ""
    try:
        with open(memory_path, "r") as f:
            content = f.read()
    except: pass
    if len(content) > 4000:
        return content[:4000] + "\\n[...memory truncated for token efficiency]"
    return content

async def compile_morning_briefing():
    memory = get_memory_truncated()
    try: calendar_data = calendar_tools.get_today_events()
    except: calendar_data = "Calendar not connected"
    try: email_data = gmail_tools.read_emails(max_results=5, query="is:unread")
    except: email_data = "Gmail not connected"
    
    tasks = read_json(os.path.join(get_base_dir(), "memory", "tasks.json"))
    high_priority = [t for t in tasks if t.get("priority") == "high" and not t.get("completed")]
    
    habits = read_json(os.path.join(get_base_dir(), "memory", "habits.json"))
    yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
    yesterday_habits = [h for h in habits if h.get("date") == yesterday]
    
    briefing_prompt = f"""Generate Tanmay's morning briefing.
    
MEMORY: {memory}
CALENDAR TODAY: {calendar_data}
UNREAD EMAILS: {email_data}
HIGH PRIORITY TASKS: {[t['task'] for t in high_priority[:3]]}
YESTERDAY'S HABITS: {yesterday_habits}

Deliver a sharp spoken briefing under 150 words covering:
- Today's schedule
- Most important email if any
- Top task priority for today
- Yesterday's habit consistency
- One motivational line tied to his goals

Voice format only — no markdown, no bullets, natural speech.
Start with: "Good morning Tanmay. Here's your day."
Be direct. Be Tam."""
    
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system="You are Tam. Generate the morning briefing.",
        messages=[{"role": "user", "content": briefing_prompt}]
    )
    
    return next((b.text for b in response.content if hasattr(b, 'text')), "")

async def scheduled_morning_briefing():
    global _queue
    if not _queue: return
    text = await compile_morning_briefing()
    await _queue.put({"event": "proactive", "data": json.dumps({"type": "morning_briefing", "text": text, "autoSpeak": True})})

async def nightly_sync():
    global _queue
    if not _queue: return
    
    base = get_base_dir()
    tasks = read_json(os.path.join(base, "memory", "tasks.json"))
    workouts = read_json(os.path.join(base, "memory", "workouts.json"))
    study = read_json(os.path.join(base, "memory", "study_log.json"))
    
    today = datetime.now().date().isoformat()
    today_workouts = [w for w in workouts if w.get("date","").startswith(today)]
    today_study = [s for s in study if s.get("date","").startswith(today)]
    today_tasks_done = [t for t in tasks if t.get("completed") and t.get("completed_at","").startswith(today)]
    rolling_tasks = [t for t in tasks if not t.get("completed")]
    
    sync_prompt = f"""Generate Tanmay's end-of-day summary.
    
Today's workouts: {today_workouts}
Today's study: {today_study}
Tasks completed today: {today_tasks_done}
Tasks rolling to tomorrow: {[t['task'] for t in rolling_tasks[:3]]}

Give a brief spoken wrap-up under 100 words:
- What got done today (honest assessment)
- What rolls to tomorrow
- One closing line — real, not generic

Voice format. No markdown. Be Tam."""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system="You are Tam delivering the nightly sync.",
        messages=[{"role": "user", "content": sync_prompt}]
    )
    
    text = next((b.text for b in response.content if hasattr(b, 'text')), "")
    await _queue.put({"event": "proactive", "data": json.dumps({"type": "nightly_sync", "text": text, "autoSpeak": True})})

async def check_reminders():
    global _queue
    if not _queue: return
    
    path = os.path.join(get_base_dir(), "memory", "reminders.json")
    reminders = read_json(path)
    now = datetime.now().timestamp()
    updated = False
    
    for r in reminders:
        if not r.get("fired") and r.get("trigger_at", 0) <= now:
            r["fired"] = True
            updated = True
            await _queue.put({
                "event": "proactive",
                "data": json.dumps({
                    "type": "reminder",
                    "text": f"Tanmay — {r['message']}",
                    "autoSpeak": True,
                    "urgent": True
                })
            })
            
    if updated:
        write_json(path, reminders)
