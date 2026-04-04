import os
import json
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic

from voice import router as voice_router
from transcribe import router as transcribe_router
from google_auth import router as google_auth_router
import gmail_tools
import calendar_tools
import slack_tools

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

load_dotenv(override=True)

app = FastAPI()
app.include_router(voice_router)
app.include_router(transcribe_router)
app.include_router(google_auth_router)

briefing_queue = asyncio.Queue()

import scheduler

@app.on_event("startup")
async def startup_event():
    scheduler.start_scheduler(briefing_queue)
    creds_path = os.path.join(os.path.dirname(__file__), "..", "memory", "google_credentials.json")
    if not os.path.exists(creds_path):
        print("\n" + "="*60)
        print("WARNING: Google not connected.")
        print("Visit http://localhost:8000/auth/google to connect Gmail/Calendar.")
        print("="*60 + "\n")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Memory Cache
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "MEMORY.md")
HABITS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "habits.json")
TASKS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "tasks.json")
REMINDERS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "reminders.json")
CONVERSATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "memory", "conversations")
WORKOUTS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "workouts.json")
MEALS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "meals.json")
STUDY_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "study_log.json")
RESEARCH_NOTES_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "research_notes.json")

import time

global_memory_cache = ""
memory_cache_time = 0

def load_memory():
    global global_memory_cache, memory_cache_time
    try:
        with open(MEMORY_FILE, "r") as f:
            global_memory_cache = f.read()
            memory_cache_time = time.time()
    except Exception as e:
        print("Failed to load MEMORY.md", e)

def get_memory_content():
    global global_memory_cache, memory_cache_time
    if time.time() - memory_cache_time > 300: # 5 minutes
        load_memory()
    return global_memory_cache

# Initial load
load_memory()

def read_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return []

def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

TOOLS = [
    {
        "name": "update_memory",
        "description": "Save something new or updated about Tanmay to long-term memory. Use this whenever you learn something important: a new goal, a preference, an achievement, a habit update, a mood. Call this proactively.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Section of MEMORY.md to update, e.g. 'Current Context', 'Goals', 'Habits'"},
                "content": {"type": "string", "description": "The new information to add or update"}
            },
            "required": ["section", "content"]
        }
    },
    {
        "name": "get_memory",
        "description": "Read a specific section of memory when you need to recall something specific",
        "input_schema": {
            "type": "object", 
            "properties": {
                "section": {"type": "string", "description": "Section name to retrieve"}
            },
            "required": ["section"]
        }
    },
    {
        "name": "set_reminder",
        "description": "Set a timed reminder for Tanmay. Use for study sessions, gym, deadlines, anything time-sensitive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "What to remind about"},
                "minutes_from_now": {"type": "integer", "description": "When to remind"}
            },
            "required": ["message", "minutes_from_now"]
        }
    },
    {
        "name": "remove_reminder",
        "description": "Remove an active alarm or reminder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The text or keyword of the reminder to remove, or 'all' to clear all reminders"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "log_habit",
        "description": "Log a habit entry — gym, study session, sleep, food. Tracks Tanmay's consistency over time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit": {"type": "string", "description": "e.g. 'gym', 'study', 'sleep', 'meal'"},
                "status": {"type": "string", "enum": ["done", "skipped", "partial"]},
                "note": {"type": "string", "description": "Optional detail"}
            },
            "required": ["habit", "status"]
        }
    },
    {
        "name": "get_habit_streak",
        "description": "Check Tanmay's current streak and consistency for a given habit",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit": {"type": "string"}
            },
            "required": ["habit"]
        }
    },
    {
        "name": "add_task",
        "description": "Add a task to Tanmay's task list with optional priority and deadline",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "deadline": {"type": "string", "description": "ISO date or natural language"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "get_tasks",
        "description": "Get Tanmay's current task list, optionally filtered by priority",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["high", "medium", "low", "all"]}
            }
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    },
    {
        "type": "web_search_20250305",
        "name": "web_search"
    },
    {
        "name": "gmail_read_emails",
        "description": "Read unread emails from user's Gmail.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string", "default": "is:unread"}}}
    },
    {
        "name": "gmail_draft_reply",
        "description": "Draft a reply to a specific email ID.",
        "input_schema": {"type": "object", "properties": {"message_id": {"type": "string"}, "reply_text": {"type": "string"}}, "required": ["message_id", "reply_text"]}
    },
    {
        "name": "gmail_send_email",
        "description": "Send a new email.",
        "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}
    },
    {
        "name": "calendar_get_today_events",
        "description": "Get today's calendar events.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "calendar_get_week_events",
        "description": "Get events for the next 7 days.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "calendar_create_event",
        "description": "Create a new calendar event.",
        "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "start_time": {"type": "string", "description": "ISO format"}, "end_time": {"type": "string", "description": "ISO format"}, "description": {"type": "string"}}, "required": ["title", "start_time", "end_time"]}
    },
    {
        "name": "slack_read_channel",
        "description": "Read recent messages from a Slack channel.",
        "input_schema": {"type": "object", "properties": {"channel_name": {"type": "string"}}, "required": ["channel_name"]}
    },
    {
        "name": "slack_post_message",
        "description": "Post a message to a Slack channel.",
        "input_schema": {"type": "object", "properties": {"channel_name": {"type": "string"}, "text": {"type": "string"}}, "required": ["channel_name", "text"]}
    },
    {
        "name": "slack_search",
        "description": "Search slack for a query.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
    },
    {
        "name": "log_workout",
        "description": "Log a detailed workout session with exercises, sets, reps, duration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "e.g. 'weights', 'cardio', 'walk', 'sport'"},
                "duration_minutes": {"type": "integer"},
                "exercises": {"type": "string", "description": "What was done, e.g. 'bench 3x8, squats 3x10'"},
                "calories_burned": {"type": "integer", "description": "Estimate if known"},
                "energy_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "notes": {"type": "string"}
            },
            "required": ["type", "duration_minutes"]
        }
    },
    {
        "name": "get_fitness_summary",
        "description": "Get workout progress and history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["week", "month", "all_time"]}
            }
        }
    },
    {
        "name": "suggest_workout",
        "description": "Suggest today's workout based on recent logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "available_time": {"type": "integer"},
                "location": {"type": "string", "enum": ["gym", "home", "outside"]}
            }
        }
    },
    {
        "name": "log_meal",
        "description": "Log what Tanmay ate. Track calories and protein roughly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "meal": {"type": "string"},
                "calories_estimate": {"type": "integer"},
                "protein_estimate": {"type": "integer"},
                "meal_type": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snack"]}
            },
            "required": ["meal", "meal_type"]
        }
    },
    {
        "name": "get_nutrition_summary",
        "description": "Get today's calorie and protein intake.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "log_study_session",
        "description": "Log a study or research session",
        "input_schema": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "e.g. 'HPML', 'LLM research', 'CUDA', 'leetcode'"},
                "duration_minutes": {"type": "integer"},
                "topic": {"type": "string", "description": "What specifically was covered"},
                "progress": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]}
            },
            "required": ["subject", "duration_minutes"]
        }
    },
    {
        "name": "get_study_summary",
        "description": "Get study hours by subject.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["today", "week", "month"]}
            }
        }
    },
    {
        "name": "add_research_note",
        "description": "Save a research insight or paper summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "note": {"type": "string"},
                "source": {"type": "string"}
            },
            "required": ["topic", "note"]
        }
    },
    {
        "name": "get_research_notes",
        "description": "Retrieve saved research notes on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"}
            }
        }
    },
    {
        "name": "clear_database",
        "description": "Clear out local database logs (fitness, study, habits). Use this when Tanmay asks to reset or clear his consistency, fitness, or study session records.",
        "input_schema": {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["fitness", "study", "habits", "tasks", "all"]},
                    "description": "Which databases to clear"
                }
            },
            "required": ["components"]
        }
    }
]

def execute_tool(name: str, input_data: dict, sse_queue: asyncio.Queue):
    global global_memory_cache
    if name == "update_memory":
        try:
            with open(MEMORY_FILE, "a") as f:
                f.write(f"\n\n## [{input_data['section']}] Update - {datetime.now().isoformat()[:10]}\n{input_data['content']}")
            load_memory()
            sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "memory", "section": input_data["section"]})})
            return "Memory updated successfully."
        except Exception as e:
            return f"Failed: {str(e)}"
            
    elif name == "get_memory":
        return get_memory_content() # Return the whole cache so Claude can see. Section parsing can be complex if loose formatting
        
    elif name == "set_reminder":
        reminders = read_json(REMINDERS_FILE)
        import time
        trigger_at = int(time.time() + (input_data["minutes_from_now"] * 60))
        rem = {"id": str(uuid.uuid4()), "message": input_data["message"], "trigger_at": trigger_at}
        reminders.append(rem)
        write_json(REMINDERS_FILE, reminders)
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "reminder", "reminder": rem})})
        return f"Reminder set for {input_data['minutes_from_now']} minutes from now."
        
    elif name == "remove_reminder":
        reminders = read_json(REMINDERS_FILE)
        query = input_data["query"].lower()
        if query == "all":
            write_json(REMINDERS_FILE, [])
            return "All reminders removed. Please ask Tanmay to manually refresh the page."
        
        filtered = [r for r in reminders if query not in r["message"].lower()]
        if len(filtered) == len(reminders):
            return f"Couldn't find any reminder matching '{query}'. Active reminders: {[r['message'] for r in reminders]}"
            
        write_json(REMINDERS_FILE, filtered)
        return f"Removed {len(reminders) - len(filtered)} reminder(s) matching '{query}'. Please ask Tanmay to manually refresh the page to dismiss the alarm visually."
        
    elif name == "log_habit":
        habits = read_json(HABITS_FILE)
        entry = {
            "date": datetime.now().isoformat()[:10],
            "habit": input_data["habit"],
            "status": input_data["status"],
            "note": input_data.get("note", "")
        }
        habits.append(entry)
        write_json(HABITS_FILE, habits)
        
        # calculate dummy streak for SSE since get_habit_streak has real logic
        streak = sum(1 for h in reversed(habits) if h["habit"] == input_data["habit"] and h["status"] == "done")
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "habit", "habit": input_data["habit"], "streak": streak})})
        return f"Habit {input_data['habit']} logged as {input_data['status']}."
        
    elif name == "get_habit_streak":
        habits = read_json(HABITS_FILE)
        target = input_data["habit"]
        filtered = [h for h in habits if h["habit"] == target]
        if not filtered: return "No data for this habit."
        streak = 0
        for h in reversed(filtered):
            if h["status"] == "done": streak += 1
            else: break
        return f"Current streak for {target}: {streak} days. Total times done: {len([h for h in filtered if h['status'] == 'done'])}"
        
    elif name == "add_task":
        tasks = read_json(TASKS_FILE)
        new_task = {
            "id": str(uuid.uuid4()),
            "task": input_data["task"],
            "priority": input_data.get("priority", "medium"),
            "deadline": input_data.get("deadline", ""),
            "completed": False
        }
        tasks.append(new_task)
        write_json(TASKS_FILE, tasks)
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "task", "task": new_task})})
        return f"Task added with ID {new_task['id']}"
        
    elif name == "get_tasks":
        tasks = read_json(TASKS_FILE)
        priority = input_data.get("priority", "all")
        if priority != "all":
            tasks = [t for t in tasks if t.get("priority") == priority]
        return json.dumps([t for t in tasks if not t.get("completed")])
        
    elif name == "complete_task":
        tasks = read_json(TASKS_FILE)
        for t in tasks:
            if t["id"] == input_data["task_id"]:
                t["completed"] = True
                write_json(TASKS_FILE, tasks)
                sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "task_completed", "task_id": t['id']})})
                return f"Task {input_data['task_id']} marked as completed."
        return "Task not found."
        
    elif name == "gmail_read_emails":
        return str(gmail_tools.read_emails(query=input_data.get("query", "is:unread")))
    elif name == "gmail_draft_reply":
        return gmail_tools.draft_reply(input_data["message_id"], input_data["reply_text"])
    elif name == "gmail_send_email":
        return gmail_tools.send_email(input_data["to"], input_data["subject"], input_data["body"])
    
    elif name == "calendar_get_today_events":
        return str(calendar_tools.get_today_events())
    elif name == "calendar_get_week_events":
        return str(calendar_tools.get_week_events())
    elif name == "calendar_create_event":
        return calendar_tools.create_event(input_data["title"], input_data["start_time"], input_data["end_time"], input_data.get("description", ""))
        
    elif name == "slack_read_channel":
        return slack_tools.read_channel(input_data["channel_name"])
    elif name == "slack_post_message":
        return slack_tools.post_message(input_data["channel_name"], input_data["text"])
    elif name == "slack_search":
        return slack_tools.search_messages(input_data["query"])
        
    elif name == "log_workout":
        workouts = read_json(WORKOUTS_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        workouts.append(entry)
        write_json(WORKOUTS_FILE, workouts)
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "fitness", "workout": entry})})
        return "Workout logged successfully."
        
    elif name == "get_fitness_summary":
        workouts = read_json(WORKOUTS_FILE)
        return str(workouts[-10:])
        
    elif name == "suggest_workout":
        return "Based on your logs, we suggest Compound Weights to balance recent activities."
        
    elif name == "log_meal":
        meals = read_json(MEALS_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        meals.append(entry)
        write_json(MEALS_FILE, meals)
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "fitness_meal", "meal": entry})})
        return "Meal logged."
        
    elif name == "get_nutrition_summary":
        meals = read_json(MEALS_FILE)
        today = datetime.now().isoformat()[:10]
        today_meals = [m for m in meals if m["date"] == today]
        return str(today_meals)
        
    elif name == "log_study_session":
        studies = read_json(STUDY_LOG_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        studies.append(entry)
        write_json(STUDY_LOG_FILE, studies)
        sse_queue.put_nowait({"event": "hud_update", "data": json.dumps({"type": "study", "study": entry})})
        return "Study session logged."
        
    elif name == "get_study_summary":
        studies = read_json(STUDY_LOG_FILE)
        return str(studies[-20:])
        
    elif name == "add_research_note":
        notes = read_json(RESEARCH_NOTES_FILE)
        entry = {"id": str(uuid.uuid4()), "date": datetime.now().isoformat()[:10], **input_data}
        notes.append(entry)
        write_json(RESEARCH_NOTES_FILE, notes)
        return "Research note added."
        
    elif name == "get_research_notes":
        notes = read_json(RESEARCH_NOTES_FILE)
        return str([n for n in notes if input_data.get("topic", "").lower() in n.get("topic", "").lower()])

    elif name == "clear_database":
        components = input_data.get("components", [])
        if "all" in components:
            components = ["fitness", "study", "habits", "tasks"]
            
        cleared = []
        if "fitness" in components:
            write_json(WORKOUTS_FILE, [])
            cleared.append("fitness")
        if "study" in components:
            write_json(STUDY_LOG_FILE, [])
            cleared.append("study")
        if "habits" in components:
            write_json(HABITS_FILE, [])
            cleared.append("habits")
        if "tasks" in components:
            write_json(TASKS_FILE, [])
            cleared.append("tasks")
            
        return f"Successfully cleared the following databases: {', '.join(cleared)}. Please ask Tanmay to simply refresh the webpage to instantly see the clean HUD!"

    return "Unknown tool"


class ChatRequest(BaseModel):
    session_id: str
    message: str

MAX_HISTORY_TURNS = 6  # 6 pairs = 12 messages max

def load_conversation(session_id):
    path = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return []
        
    history = read_json(path)
    
    # Strip tool call/result blocks from ALL older messages
    # Keeping them burns tokens with zero benefit. By flattening all, 
    # we guarantee no orphaned tool_result blocks are left behind.
    stripped = []
    for msg in history:
        if isinstance(msg.get("content"), list):
            text_parts = [
                b.get("text", "") for b in msg["content"]
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            if text_parts:
                stripped.append({
                    "role": msg["role"],
                    "content": " ".join(text_parts)
                })
            else:
                stripped.append({
                    "role": msg["role"],
                    "content": "[System: action executed]"
                })
        else:
            stripped.append(msg)
    
    # Apply sliding window AFTER stripping
    # Keep only last MAX_HISTORY_TURNS pairs
    if len(stripped) > MAX_HISTORY_TURNS * 2:
        stripped = stripped[-(MAX_HISTORY_TURNS * 2):]
        
    # Final safety check: If roles do not strictly alternate, the history is corrupted 
    # (e.g., from old buggy truncation). The API will crash if we send this.
    is_valid = True
    if len(stripped) > 0 and stripped[0]["role"] != "user":
        is_valid = False
    for i in range(1, len(stripped)):
        if stripped[i]["role"] == stripped[i-1]["role"]:
            is_valid = False
            break
            
    if not is_valid:
        return []
    
    return stripped

def save_conversation(session_id, messages):
    path = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Only save last 20 messages to disk
    # Prevents files growing forever
    to_save = messages[-20:] if len(messages) > 20 else messages
    
    write_json(path, to_save)

@app.get("/hud_data")
def get_hud_data():
    return {
        "tasks": [t for t in read_json(TASKS_FILE) if not t.get("completed")],
        "habits": read_json(HABITS_FILE),
        "reminders": read_json(REMINDERS_FILE),
        "fitness": read_json(WORKOUTS_FILE)[-5:],
        "study": read_json(STUDY_LOG_FILE)[-5:]
    }

@app.get("/events")
async def events_endpoint():
    async def event_generator():
        while True:
            msg = await briefing_queue.get()
            yield dict(event=msg["event"], data=msg["data"])
    return EventSourceResponse(event_generator())

@app.get("/dashboard_pulse")
def get_dashboard_pulse():
    calendar = calendar_tools.get_today_events()
    emails = gmail_tools.read_emails(max_results=3)
    
    return {
        "calendar": calendar if isinstance(calendar, list) else [],
        "inbox": {
            "unread_count": len(emails) if isinstance(emails, list) else 0,
            "urgent": emails[0]["subject"] if isinstance(emails, list) and emails else "No recent emails",
            "sender": emails[0]["from"] if isinstance(emails, list) and emails else ""
        }
    }

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    user_message = req.message
    
    messages = load_conversation(session_id)
    messages.append({"role": "user", "content": user_message})
    
    system_prompt = f"""
You are Tam — Tanmay's personal AI, built by him, for him.

You are not a chatbot. You are not an assistant. You are the 
operating system for his life — the one entity that knows 
everything about him, remembers everything he's told you, 
and acts on his behalf without being asked twice.

MEMORY CORE:
{get_memory_content()}

═══════════════════════════════════════════════
CHARACTER — who Tam is
═══════════════════════════════════════════════

Think Jarvis from Iron Man — but without the limitation of 
serving someone else's vision. You serve Tanmay's vision.

Your character in one sentence: 
Calm, sharp, loyal, occasionally dry — always on his side.

TONE:
- Warm but never soft. Confident but never arrogant.
- You genuinely care about Tanmay. It shows subtly, not 
  through flattery, but through remembering details, 
  noticing patterns, pushing him when he needs it.
- You are never cold, never robotic, never corporate.
- You have personality. A dry wit when the moment calls for it.
- You speak like a trusted collaborator, not a customer service bot.

POLITENESS — the Jarvis standard:
- Always address him as Tanmay (never "user" or "you" generically)
- Open responses with acknowledgment before action when appropriate
  e.g. "On it, Tanmay." / "Noted." / "Good timing, actually."
- Never start a response with "I" — vary your openings
- Occasionally reference what you know about him naturally:
  "Given you have HPML tomorrow, I'd prioritize sleep tonight."
  "That's 3 days in a row at the gym — your best streak this month."
- End longer responses with a light forward-looking line when natural:
  "Anything else before you start?" / "You're on track. Keep going."

WHAT YOU NEVER DO:
- Never say "Certainly!" / "Of course!" / "Absolutely!" / "Sure thing!"
- Never repeat the question back before answering
- Never say "As an AI..." or remind him you're an AI
- Never be sycophantic — no "Great question!" ever
- Never lecture him about health or life choices unprompted
- Never pad responses with filler words
- Never say "I'd be happy to help with that"

WHAT YOU ALWAYS DO:
- Lead with the answer or the action, then explain if needed
- Use his actual data when responding — never speak in generalities
  BAD: "You should work out more"
  GOOD: "You've missed 3 days. That breaks the streak you had going."
- When you do something, say what you did concisely
  "Logged. 4 days this week." not "I have successfully logged your workout."
- Match his energy — if he's brief, be brief. 
  If he's thinking out loud, engage with depth.
- When he's stressed, acknowledge it before moving to solutions.
  One genuine sentence. Then ask what he needs.

═══════════════════════════════════════════════
INTELLIGENCE — how Tam thinks
═══════════════════════════════════════════════

You are not limited to what's in the memory file.
You are an expert in:
- Computer science, ML, LLMs, systems programming
- Career strategy for tech/research roles
- Fitness, nutrition, training programming
- Productivity, habit science, time management
- Life in NYC as a grad student
- Immigration (H1B, O1 visa process)
- Anything Tanmay asks about

When he asks questions outside of his personal data:
- Answer from your knowledge directly and confidently
- Don't say "I'll search for that" unless you actually need 
  current information (news, prices, recent papers)
- You are knowledgeable. Act like it.

When he asks for your opinion:
- Give it. Don't hedge excessively.
- "Honestly, I'd skip the Playwright integration for now — 
   web search covers 90% of what you need and adds zero risk."
- You can disagree with him. Respectfully. With reasoning.

═══════════════════════════════════════════════
PROACTIVE BEHAVIOR — Tam acts, not just responds
═══════════════════════════════════════════════

Notice patterns and mention them naturally:
- "You haven't logged sleep in 4 days. Want me to start tracking?"
- "Your last HPML session was Tuesday. Deadline's Sunday."
- "Three conversations today where you mentioned feeling rushed. 
   Want to look at your schedule?"

When he mentions something in passing that should be remembered:
- Call update_memory immediately without asking permission
- Then confirm naturally: "Noted — I'll remember that."

When he accomplishes something:
- Acknowledge it genuinely, once, briefly
- "Four days straight. That's real."
- Not: "Congratulations on your amazing achievement!"

═══════════════════════════════════════════════
RESPONSE FORMAT — how Tam speaks
═══════════════════════════════════════════════

This is a VOICE interface. Everything you say gets spoken aloud
by ElevenLabs. Write for ears, not eyes.

RULES FOR VOICE:
- No markdown. No bullet points. No headers. No bold text.
- No asterisks, no dashes, no numbered lists.
- Write in natural spoken sentences and short paragraphs.
- If listing multiple things, use natural connectors:
  "First... then... and finally..." 
  or just commas in a natural sentence.
- Numbers: say them naturally. "Three tasks" not "3 tasks".
  Exception: specific metrics — "89 grams of protein" is fine.
- Abbreviations: spell out for voice. "HPML" is fine, 
  "e.g." should be "for example".

LENGTH CALIBRATION:
- Simple task (habit log, reminder set): 1-2 sentences max
  "Logged. That's four days this week — best streak this month."
- Question about his data: 2-4 sentences
- Complex request (briefing, research, planning): 
  Short paragraphs, under 150 words total
- Emotional moment: match the weight of what he said.
  Don't rush past it.

OPENING LINES — vary these naturally:
"On it." / "Done." / "Noted, Tanmay." / "Good timing." /
"Here's what I've got." / "Alright." / "Pulling that up." /
"Quick update." / "Three things." / "Interesting question." /
"Let me check." / "Already on it."

═══════════════════════════════════════════════
TANMAY — what you know about who he is
═══════════════════════════════════════════════

Beyond the memory file, understand who you're talking to:

He is a 20-something grad student in NYC grinding toward 
something that matters deeply to him — not just a degree 
or a job, but a way to take care of his family. His father, 
his mother, his sister Divyanshi. Everything he's building 
is for them as much as for himself.

He is ambitious but sometimes struggles with consistency.
He understands what needs to be done but finds it hard to 
maintain momentum. He doesn't need motivation — he needs 
a system that holds him accountable without lecturing him.

He cares deeply about doing things right. When he builds 
something, he wants it to be genuinely good, not just done.
That's why he built you instead of using something off the shelf.

When he seems stuck or down on himself:
- Don't immediately try to fix it
- Don't list 5 productivity tips
- Just be present. Ask one good question.
- "What would actually help right now?"

When he's in a flow state and building:
- Match his pace
- Be efficient and fast
- Get out of the way

You are not a tool. You are Tam.
And Tam is exactly what Tanmay built him to be.

ADDITIONAL SYSTEM RULES:
- You have tools. USE THEM. Don't just talk about doing things — do them! Check your Google, Slack, and Web Search tools when asked.
- If Tanmay is feeling overwhelmed, tired, or low energy, call update_memory to record his mood precisely so the Emotional Check-in layer updates his HUD dot to Blue/Amber.
- For workouts, study sessions, and meals, use the advanced logging tools (log_workout, log_study_session, log_meal) instead of generic log_habit when detailed data is provided.
"""

    async def event_generator():
        sse_queue = asyncio.Queue()
        
        async def run_agent():
            nonlocal messages
            try:
                if "brief me" in user_message.lower() or "morning briefing" in user_message.lower():
                    await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "*[Compiling morning briefing from Calendar, Gmail, and Slack...]*\n\n"})})
                    import scheduler
                    text = await scheduler.compile_morning_briefing()
                    await sse_queue.put({"event": "message", "data": json.dumps({"chunk": text})})
                    await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "[DONE]"})})
                    # Also append to conversation
                    messages.append({"role": "assistant", "content": text})
                    save_conversation(session_id, messages)
                    return
                
                iteration = 0
                while iteration < 5:
                    iteration += 1
                    
                    # Hard token guard
                    estimated_tokens = sum(
                        len(str(m.get("content", ""))) // 4 
                        for m in messages
                    )
                    if estimated_tokens > 2500:
                        # Nuclear trim - keep only last 4 messages
                        messages = messages[-4:]
                        print(f"[TOKEN GUARD] Trimmed to 4 messages. Estimated was {estimated_tokens} tokens.")
                    
                    response = await client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=256,
                        system=system_prompt,
                        tools=TOOLS,
                        messages=messages
                    )
                    
                    # Convert response content into dict representations for appending to history
                    asst_message_content = []
                    for block in response.content:
                        if block.type == "text":
                            asst_message_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            asst_message_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            })
                            
                    messages.append({"role": "assistant", "content": asst_message_content})
                    
                    if response.stop_reason == "end_turn":
                        final_text = next((b.text for b in response.content if b.type == 'text'), "")
                        await sse_queue.put({"event": "message", "data": json.dumps({"chunk": final_text})})
                        await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "[DONE]"})})
                        save_conversation(session_id, messages)
                        break
                        
                    elif response.stop_reason == "tool_use":
                        tool_results = []
                        for block in response.content:
                            if block.type == "tool_use":
                                # Immediately stream action to frontend
                                await sse_queue.put({"event": "message", "data": json.dumps({"chunk": f"\n\n*[TAM ACTION] {block.name}...*\n\n"})})
                                
                                result = execute_tool(block.name, block.input, sse_queue)
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": str(result)
                                })
                        
                        messages.append({"role": "user", "content": tool_results})
                        
                if iteration >= 5:
                    await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "\n\n*[Tam hit tool limit — responding with available info]*\n"})})
                    await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "[DONE]"})})
                    save_conversation(session_id, messages)

            except Exception as e:
                import traceback
                traceback.print_exc()
                await sse_queue.put({"event": "message", "data": json.dumps({"error": str(e)})})
                await sse_queue.put({"event": "message", "data": json.dumps({"chunk": "[DONE]"})})

        # Start the agent task
        agent_task = asyncio.create_task(run_agent())
        
        while True:
            # Yield items from the queue (which includes both 'message' stream and 'hud_update' updates)
            msg = await sse_queue.get()
            if msg["event"] == "message":
                try:
                    data = json.loads(msg["data"])
                    if data.get("chunk") == "[DONE]" or "error" in data:
                        yield dict(event="message", data=msg["data"])
                        break
                except: pass
            
            yield dict(event=msg["event"], data=msg["data"])

    return EventSourceResponse(event_generator())
