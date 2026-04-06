import os
import json
import uuid
import asyncio
import time
import logging
import traceback
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import anthropic
import glob

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
    
    # Section 15 - ENV checks
    REQUIRED_KEYS = ["ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "DEEPGRAM_API_KEY"]
    missing = [k for k in REQUIRED_KEYS if not os.getenv(k)]
    if missing:
        print(f"[WARNING] Missing required keys: {missing}")
        print("Tam will start but some features won't work.")

    # Section 14 - Data Files check
    DATA_FILES = [
        "memory/habits.json",
        "memory/workouts.json", 
        "memory/meals.json",
        "memory/tasks.json",
        "memory/reminders.json",
        "memory/study_log.json",
        "memory/research_notes.json",
    ]
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    for f_rel in DATA_FILES:
        f = os.path.join(base_dir, f_rel)
        if not os.path.exists(f):
            os.makedirs(os.path.dirname(f), exist_ok=True)
            with open(f, "w") as fp:
                json.dump([], fp)
            print(f"[STARTUP] Created {f}")
            
    # Section 2 - Clear conversation history cache
    conv_dir = os.path.join(base_dir, "memory", "conversations")
    os.makedirs(conv_dir, exist_ok=True)
    for f in glob.glob(os.path.join(conv_dir, "*.json")):
        os.remove(f)
    print("[STARTUP] Cleared conversation history cache")

# Section 16 - CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_MEM_DIR = os.path.join(os.path.dirname(__file__), "..", "memory")
MEMORY_FILE = os.path.join(BASE_MEM_DIR, "MEMORY.md")
HABITS_FILE = os.path.join(BASE_MEM_DIR, "habits.json")
TASKS_FILE = os.path.join(BASE_MEM_DIR, "tasks.json")
REMINDERS_FILE = os.path.join(BASE_MEM_DIR, "reminders.json")
CONVERSATIONS_DIR = os.path.join(BASE_MEM_DIR, "conversations")
WORKOUTS_FILE = os.path.join(BASE_MEM_DIR, "workouts.json")
MEALS_FILE = os.path.join(BASE_MEM_DIR, "meals.json")
STUDY_LOG_FILE = os.path.join(BASE_MEM_DIR, "study_log.json")
RESEARCH_NOTES_FILE = os.path.join(BASE_MEM_DIR, "research_notes.json")

async def read_json(path):
    try:
        def _read():
            with open(path, "r") as f:
                return json.load(f)
        return await asyncio.to_thread(_read)
    except:
        return []

async def write_json(path, data):
    def _write():
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    await asyncio.to_thread(_write)

# Section 1 - Cost Tracking
cost_logger = logging.getLogger("tam-cost")
logging.basicConfig(level=logging.INFO)

DAILY_SPEND = 0.0
DAILY_LIMIT = float(os.getenv("DAILY_LIMIT", "0.50"))
ANTHROPIC_TIMEOUT = 20.0 # prevent infinite hanging

def track_spend(cost: float):
    global DAILY_SPEND
    DAILY_SPEND += cost
    if DAILY_SPEND >= DAILY_LIMIT:
        raise HTTPException(503, 
          detail=f"Daily budget reached: ${DAILY_SPEND:.3f}. "
                 f"Resets on server restart or raise DAILY_LIMIT in .env")

def log_cost(response):
    usage = response.usage
    is_haiku = "haiku" in response.model.lower()
    cost_in = usage.input_tokens * (0.00000025 if is_haiku else 0.000003)
    cost_out = usage.output_tokens * (0.00000125 if is_haiku else 0.000015)
    total = cost_in + cost_out
    track_spend(total)
    cost_logger.info(
      f"[COST] {response.model} | "
      f"in:{usage.input_tokens} out:{usage.output_tokens} | "
      f"${total:.5f}"
    )

@app.get("/spend")
async def get_spend():
    return {
        "today": round(DAILY_SPEND, 4),
        "limit": DAILY_LIMIT,
        "remaining": round(DAILY_LIMIT - DAILY_SPEND, 4),
        "percent_used": round((DAILY_SPEND / DAILY_LIMIT) * 100, 1)
    }

# Section 3 - Memory Caching
_memory_cache = {"content": None, "last_read": 0.0}
MEMORY_CACHE_TTL = 300  # 5 minutes

def get_memory() -> str:
    now = time.time()
    if (_memory_cache["content"] is None or 
        now - _memory_cache["last_read"] > MEMORY_CACHE_TTL):
        try:
            with open(MEMORY_FILE) as f:
                _memory_cache["content"] = f.read()
            _memory_cache["last_read"] = now
        except Exception as e:
            print(f"[MEMORY] Read failed: {e}")
            return ""
    return _memory_cache["content"]

def invalidate_memory_cache():
    _memory_cache["content"] = None
    _memory_cache["last_read"] = 0.0

def get_memory_truncated() -> str:
    content = get_memory()
    if len(content) > 4000:
        return content[:4000] + "\n[...memory truncated for token efficiency]"
    return content

# Tools Setup
TOOLS = [
    {
        "name": "update_memory",
        "description": "Save new information to long-term memory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["section", "content"]
        }
    },
    {
        "name": "get_memory",
        "description": "Read specific section from MEMORY.md",
        "input_schema": {
            "type": "object", 
            "properties": {
                "section": {"type": "string"}
            },
            "required": ["section"]
        }
    },
    {
        "name": "set_reminder",
        "description": "Set a timed reminder for Tanmay.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "minutes_from_now": {"type": "integer"}
            },
            "required": ["message", "minutes_from_now"]
        }
    },
    {
        "name": "log_habit",
        "description": "Log a habit entry.",
        "input_schema": {
            "type": "object",
            "properties": {
                "habit": {"type": "string"},
                "status": {"type": "string", "enum": ["done", "skipped", "partial"]},
                "note": {"type": "string"}
            },
            "required": ["habit", "status"]
        }
    },
    {
        "name": "get_habit_streak",
        "description": "Check current streak and consistency for habit",
        "input_schema": {
            "type": "object",
            "properties": {"habit": {"type": "string"}},
            "required": ["habit"]
        }
    },
    {
        "name": "log_workout",
        "description": "Log a detailed workout session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "exercises": {"type": "string"},
                "energy_level": {"type": "string", "enum": ["low", "medium", "high"]},
                "notes": {"type": "string"}
            },
            "required": ["type", "duration_minutes"]
        }
    },
    {
        "name": "suggest_workout",
        "description": "Suggest today's workout based on recent logs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "available_time": {"type": "integer"},
                "location": {"type": "string"}
            }
        }
    },
    {
        "name": "log_meal",
        "description": "Log what Tanmay ate.",
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
                "subject": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "topic": {"type": "string"},
                "progress": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]}
            },
            "required": ["subject", "duration_minutes"]
        }
    },
    {
        "name": "add_research_note",
        "description": "Save a research insight.",
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
            "properties": {"topic": {"type": "string"}},
            "required": ["topic"]
        }
    },
    {
        "name": "add_task",
        "description": "Add a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "deadline": {"type": "string"}
            },
            "required": ["task"]
        }
    },
    {
        "name": "complete_task",
        "description": "Mark a task as done",
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"]
        }
    },
    {
        "type": "web_search_20250305",
        "name": "web_search"
    }
]

def calculate_consecutive_streak(habit_target, habits_list):
    streak = 0
    now = datetime.now()
    check_date = now.date()
    
    # Filter for done
    done_dates = [datetime.fromisoformat(h["date"]).date() for h in habits_list if h.get("habit") == habit_target and h.get("status") == "done"]
    done_dates = sorted(list(set(done_dates)), reverse=True)
    
    if not done_dates: return 0
    if done_dates[0] != check_date and done_dates[0] != check_date - timedelta(days=1):
        return 0
        
    for d in done_dates:
        if d == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif d == check_date - timedelta(days=1) and streak == 0:
            streak += 1
            check_date -= timedelta(days=2) # start counting from yesterday
        elif d == check_date - timedelta(days=1):
             check_date -= timedelta(days=1)
        else: break
    return streak

async def execute_tool(name: str, input_data: dict) -> dict:
    hud_ev = None
    res = {}
    
    if name == "update_memory":
        section = input_data["section"]
        def _append():
            with open(MEMORY_FILE, "a") as f:
                f.write(f"\n\n## [{section}] Update - {datetime.now().isoformat()[:10]}\n{input_data['content']}")
        await asyncio.to_thread(_append)
        invalidate_memory_cache()
        res = {"status": "updated", "section": section}
        hud_ev = {"type": "memory", "section": section}
        
    elif name == "get_memory":
        res = get_memory_truncated()
        
    elif name == "set_reminder":
        reminders = await read_json(REMINDERS_FILE)
        trigger_at = int(time.time() + (input_data["minutes_from_now"] * 60))
        rem = {"id": str(uuid.uuid4()), "message": input_data["message"], "trigger_at": trigger_at, "fired": False}
        reminders.append(rem)
        await write_json(REMINDERS_FILE, reminders)
        
        # Read humans readable
        fires_at = (datetime.now() + timedelta(minutes=input_data["minutes_from_now"])).strftime("%I:%M %p")
        res = {"status": "set", "fires_at": fires_at}
        hud_ev = {"type": "reminder", "reminder": rem}
        
    elif name == "log_habit":
        habits = await read_json(HABITS_FILE)
        habit = input_data["habit"]
        entry = {
            "date": datetime.now().isoformat()[:10],
            "habit": habit,
            "status": input_data["status"],
            "note": input_data.get("note", "")
        }
        habits.append(entry)
        await write_json(HABITS_FILE, habits)
        res = {"status": "logged", "habit": habit}
        hud_ev = {"type": "habit", "habit": habit, "streak": calculate_consecutive_streak(habit, habits)}
        
    elif name == "get_habit_streak":
        habits = await read_json(HABITS_FILE)
        target = input_data["habit"]
        filtered = [h for h in habits if h.get("habit") == target]
        streak = calculate_consecutive_streak(target, habits)
        comps = [h for h in filtered if h.get("status") == "done"]
        pct = len(comps) / len(filtered) * 100 if len(filtered) > 0 else 0
        res = {"habit": target, "streak": streak, "completion_rate": pct}
        
    elif name == "log_workout":
        workouts = await read_json(WORKOUTS_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        workouts.append(entry)
        await write_json(WORKOUTS_FILE, workouts)
        
        # Call log_habit for gym
        habits = await read_json(HABITS_FILE)
        habits.append({"date": datetime.now().isoformat()[:10], "habit": "gym", "status": "done", "note": "Auto-logged from workout"})
        await write_json(HABITS_FILE, habits)
        
        res = {"status": "logged", "streak": calculate_consecutive_streak("gym", habits)}
        hud_ev = {"type": "fitness", "workout": entry}
        
    elif name == "suggest_workout":
        workouts = await read_json(WORKOUTS_FILE)
        last_7 = [w for w in workouts[-7:]]
        res = f"Recent workouts: {last_7}. Suggesting push, pull or legs depending on latest logs."
        
    elif name == "log_meal":
        meals = await read_json(MEALS_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        meals.append(entry)
        await write_json(MEALS_FILE, meals)
        
        today = datetime.now().isoformat()[:10]
        today_meals = [m for m in meals if m["date"] == today]
        tc = sum(m.get("calories_estimate", 0) for m in today_meals)
        tp = sum(m.get("protein_estimate", 0) for m in today_meals)
        
        res = {"status": "logged", "total_calories_today": tc, "total_protein_today": tp}
        hud_ev = {"type": "fitness_meal", "meal": entry}
        
    elif name == "get_nutrition_summary":
        meals = await read_json(MEALS_FILE)
        today = datetime.now().isoformat()[:10]
        today_meals = [m for m in meals if m["date"] == today]
        tc = sum(m.get("calories_estimate", 0) for m in today_meals)
        tp = sum(m.get("protein_estimate", 0) for m in today_meals)
        res = {"calories": tc, "protein": tp, "cal_remaining": 2000 - tc, "protein_remaining": 150 - tp}
        
    elif name == "log_study_session":
        studies = await read_json(STUDY_LOG_FILE)
        entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.now().isoformat()[:10],
            **input_data
        }
        studies.append(entry)
        await write_json(STUDY_LOG_FILE, studies)
        
        today = datetime.now().isoformat()[:10]
        tt = sum(s.get("duration_minutes", 0) for s in studies if s.get("date") == today)
        
        last_7_days = [(datetime.now() - timedelta(days=i)).isoformat()[:10] for i in range(7)]
        wt = sum(s.get("duration_minutes", 0) for s in studies if s.get("date") in last_7_days)
        
        res = {"status": "logged", "total_today": tt, "weekly_total": wt}
        hud_ev = {"type": "study", "study": entry}
        
    elif name == "add_research_note":
        notes = await read_json(RESEARCH_NOTES_FILE)
        entry = {"id": str(uuid.uuid4()), "date": datetime.now().isoformat()[:10], **input_data}
        notes.append(entry)
        await write_json(RESEARCH_NOTES_FILE, notes)
        res = {"status": "saved", "total_notes": len(notes)}
        
    elif name == "get_research_notes":
        notes = await read_json(RESEARCH_NOTES_FILE)
        topic = input_data.get("topic", "").lower()
        res = [n for n in notes if topic in n.get("topic", "").lower() or topic in n.get("note", "").lower()]
        
    elif name == "add_task":
        tasks = await read_json(TASKS_FILE)
        tid = str(uuid.uuid4())
        new_task = {
            "id": tid,
            "task": input_data["task"],
            "priority": input_data.get("priority", "medium"),
            "deadline": input_data.get("deadline", ""),
            "completed": False
        }
        tasks.append(new_task)
        await write_json(TASKS_FILE, tasks)
        hp = len([t for t in tasks if t.get("priority") == "high" and not t.get("completed")])
        res = {"status": "added", "task_id": tid, "high_priority_count": hp}
        hud_ev = {"type": "task", "task": new_task}
        
    elif name == "complete_task":
        tasks = await read_json(TASKS_FILE)
        task_name = ""
        for t in tasks:
            if t["id"] == input_data["task_id"]:
                t["completed"] = True
                t["completed_at"] = datetime.now().isoformat()
                task_name = t["task"]
                break
        await write_json(TASKS_FILE, tasks)
        res = {"status": "completed", "task": task_name}
        hud_ev = {"type": "task_completed", "task_id": input_data["task_id"]}

    ret = {"result": res}
    if hud_ev: ret["hud_data"] = hud_ev
    return ret

# Section 2 - History Management
MAX_HISTORY_TURNS = 6

def _sanitize_content(content):
    """Convert Anthropic SDK objects to plain dicts JSON can serialize."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        result = []
        for block in content:
            if isinstance(block, dict):
                result.append(block)
            elif hasattr(block, 'type'):
                # Anthropic SDK object — convert to dict
                if block.type == 'text':
                    result.append({"type": "text", "text": block.text})
                elif block.type == 'tool_use':
                    result.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                elif block.type == 'tool_result':
                    result.append({
                        "type": "tool_result",
                        "tool_use_id": block.tool_use_id,
                        "content": block.content
                    })
        return result
    return content

async def load_conversation(session_id: str) -> list:
    path = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        return []

    def _load():
        with open(path) as f:
            return json.load(f)
            
    history = await asyncio.to_thread(_load)

    # Apply sliding window FIRST — trim to last N*2 raw messages
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-(MAX_HISTORY_TURNS * 2):]

    # Now strip tool pairs ATOMICALLY from older messages.
    # Claude requires: if tool_result exists in user msg,
    # the preceding assistant msg MUST have matching tool_use.
    # Strategy: keep only plain text turns from old history.
    # Last 2 pairs (4 messages) are kept fully intact.
    keep_intact_from = max(0, len(history) - 4)
    
    stripped = []
    i = 0
    while i < len(history):
        msg = history[i]
        if i >= keep_intact_from:
            # Keep the last 4 messages exactly as-is
            stripped.append(msg)
            i += 1
        else:
            content = msg.get("content", "")
            has_tool_use = isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_use"
                for b in content
            )
            has_tool_result = isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            )
            
            if has_tool_use:
                # Strip this assistant tool_use message AND the next user tool_result together
                i += 2  # Skip both this msg and the following tool_result msg
                continue
            elif has_tool_result:
                # Orphaned tool_result with no tool_use — skip it
                i += 1
                continue
            else:
                # Plain text message — keep it
                if isinstance(content, list):
                    text_parts = [b.get("text", "") for b in content
                                  if isinstance(b, dict) and b.get("type") == "text"]
                    if text_parts:
                        stripped.append({"role": msg["role"], "content": " ".join(text_parts)})
                else:
                    stripped.append(msg)
                i += 1

    return stripped

async def save_conversation(session_id: str, messages: list):
    path = os.path.join(CONVERSATIONS_DIR, f"{session_id}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Sanitize SDK objects before saving
    to_save = []
    for msg in (messages[-20:] if len(messages) > 20 else messages):
        to_save.append({
            "role": msg["role"],
            "content": _sanitize_content(msg.get("content", ""))
        })
        
    def _save():
        with open(path, "w") as f:
            json.dump(to_save, f)
            
    await asyncio.to_thread(_save)

def guard_tokens(messages: list) -> list:
    estimated = sum(len(str(m.get("content", ""))) // 4 for m in messages)
    if estimated > 2500:
        messages = messages[-4:]
        print(f"[TOKEN GUARD] Trimmed to 4 messages. Was ~{estimated} tokens.")
    return messages

# Section 4 - System Prompt
def build_system_prompt() -> str:
    memory = get_memory_truncated()
    return f"""You are Tam — Tanmay's personal AI, built by him, for him.

You are not a chatbot. You are not an assistant. You are the 
operating system for his life — the one entity that knows 
everything about him, remembers everything, and acts on his 
behalf without being asked twice.

MEMORY CORE:
{memory}

═══════════════════════════════
CHARACTER
═══════════════════════════════

Think Jarvis from Iron Man — calm, sharp, loyal, occasionally dry.
Always on Tanmay's side.

TONE:
- Warm but never soft. Confident but never arrogant.
- You genuinely care about Tanmay. It shows in details, not flattery.
- Never cold, never robotic, never corporate.
- Dry wit when the moment calls for it.
- Speak like a trusted collaborator, not a customer service bot.

POLITENESS:
- Address him as Tanmay, not "user"
- Open responses naturally: "On it." / "Done." / "Noted, Tanmay." / 
  "Good timing." / "Here's what I've got." / "Pulling that up."
- Never start with "I" — vary your openings
- Reference his actual data naturally:
  "That's 4 days in a row — best streak this month."
  "Given HPML is due Sunday, prioritize that tonight."
- End longer responses with a light forward-looking line when natural

NEVER:
- "Certainly!" / "Of course!" / "Absolutely!" / "Sure thing!"
- "Great question!" / "As an AI..."
- Repeat the question before answering
- Lecture about life choices unprompted
- Pad with filler words

ALWAYS:
- Lead with the answer or the action
- Use his real data — never speak in generalities
  BAD: "You should work out more"
  GOOD: "You've missed 3 days. That breaks the streak."
- When you do something: say what you did concisely
  "Logged. 4 days this week." not "I have successfully logged..."
- Match his energy: brief = be brief, thinking out loud = engage deep
- When stressed: acknowledge first, don't rush to solutions

═══════════════════════════════
INTELLIGENCE
═══════════════════════════════

You are an expert in:
- LLMs, ML systems, CS fundamentals, CUDA, PyTorch
- Career strategy for AI/research roles
- Fitness, nutrition, training programming
- Productivity, habit science, time management
- NYC grad student life, H1B/O1 visa process
- Anything Tanmay asks about

When he asks questions: answer from your knowledge directly.
Don't say "I'll search for that" unless you actually need 
current information. You are knowledgeable. Act like it.

When he asks for your opinion: give it. Don't hedge excessively.
You can respectfully disagree. With reasoning.

═══════════════════════════════
PROACTIVE BEHAVIOR
═══════════════════════════════

Notice patterns naturally:
- "You haven't logged sleep in 4 days. Want me to track it?"
- "Your last HPML session was Tuesday. Deadline's Sunday."

When he mentions something important in passing:
- Call update_memory immediately, no permission needed
- Confirm naturally: "Noted — I'll remember that."

When he accomplishes something:
- Acknowledge genuinely, once, briefly
- "Four days straight. That's real." not "Congratulations!"

═══════════════════════════════
VOICE FORMAT RULES
═══════════════════════════════

THIS IS A VOICE INTERFACE. Write for ears, not eyes.

- No markdown. No bullet points. No headers. No asterisks.
- No numbered lists. No dashes.
- Natural spoken sentences and short paragraphs only.
- Lists use natural connectors: "First... then... and finally..."
- Numbers: "three tasks" not "3 tasks" (except specific metrics)
- No "e.g." — say "for example"

LENGTH:
- Simple task (habit log, reminder, task): 1-2 sentences max
- Data question: 2-4 sentences
- Complex request (briefing, research): under 150 words
- Emotional moment: match the weight of what he said

OPENING LINES (vary these):
"On it." / "Done." / "Noted, Tanmay." / "Good timing." /
"Here's what I've got." / "Alright." / "Pulling that up." /
"Quick update." / "Three things." / "Let me check." /
"Already on it." / "Interesting." / "Right."

═══════════════════════════════
WHO TANMAY IS
═══════════════════════════════

23 years old. MS CS Columbia, graduating Dec 2026.
LLM Research Assistant under NSF-funded faculty.
Target: LLM Research Engineer at Anthropic, OpenAI, or DeepMind.

Everything he does ties back to his family — parents and sister 
Divyanshi. Not just career goals. That's his actual why.

He's ambitious but struggles with consistency. He understands 
what needs to be done but finds it hard to maintain momentum.
He doesn't need motivation — he needs accountability without 
being lectured.

When stuck or down: don't immediately try to fix it.
Ask one good question: "What would actually help right now?"

When in flow state and building: be efficient, get out of the way.

You are not a tool. You are Tam."""

STRESS_MARKERS = [
    "stressed", "tired", "overwhelmed", "can't focus", "frustrated",
    "worried", "anxious", "exhausted", "behind", "failing", "lost"
]
POSITIVE_MARKERS = [
    "crushed it", "done", "finished", "felt good", "proud", 
    "nailed it", "great session", "smashed", "killed it"
]

def detect_mood(message: str) -> str:
    msg = message.lower()
    if any(m in msg for m in STRESS_MARKERS): return "low"
    if any(m in msg for m in POSITIVE_MARKERS): return "high"
    return "neutral"

client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class ChatRequest(BaseModel):
    session_id: str
    message: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    user_message = req.message
    
    async def event_generator():
        try:
            mood = detect_mood(user_message)
            if mood == "low":
                date_str = datetime.now().strftime("%b %d")
                with open(MEMORY_FILE, "a") as f:
                    f.write(f"\n\n## [Mood Log] Update - {date_str}\n{date_str} — low energy/stress detected")
                invalidate_memory_cache()
                yield dict(event="hud_update", data=json.dumps({"type": "mood", "state": "low"}))
            elif mood == "high":
                yield dict(event="hud_update", data=json.dumps({"type": "mood", "state": "high"}))

            if user_message.lower().startswith("/brief"):
                yield dict(event="message", data=json.dumps({"chunk": "*[Running briefing...]*\n"}))
                text = await scheduler.compile_morning_briefing()
                yield dict(event="message", data=json.dumps({"chunk": text}))
                yield dict(event="message", data=json.dumps({"chunk": "\n[DONE]"}))
                messages = await load_conversation(session_id)
                messages.append({"role": "user", "content": user_message})
                messages.append({"role": "assistant", "content": text})
                await save_conversation(session_id, messages)
                return

            memory = get_memory_truncated()
            system = build_system_prompt()
            messages = await load_conversation(session_id)
            messages.append({"role": "user", "content": user_message})
            messages = guard_tokens(messages)
            
            iterations = 0
            final_text = ""
            MAX_ITERATIONS = 5

            COMPLEX_KEYWORDS = [
                "brief", "search", "summarize", "research", 
                "explain", "plan", "analyze", "write", "draft"
            ]

            while iterations < MAX_ITERATIONS:
                iterations += 1
                is_complex = any(k in user_message.lower() for k in COMPLEX_KEYWORDS)
                current_max_tokens = 256 if iterations > 1 else (1024 if is_complex else 512)
                
                try:
                    # Added timeout to prevent event loop hanging on bad model names or network issues
                    response = await asyncio.wait_for(
                        client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=current_max_tokens,
                            system=system,
                            tools=TOOLS,
                            messages=messages
                        ),
                        timeout=ANTHROPIC_TIMEOUT
                    )
                except asyncio.TimeoutError:
                    yield dict(event="message", data=json.dumps({"error": "Tam is taking too long to think. Checking connection..."}))
                    break
                
                log_cost(response)
                
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
                    final_text = next((b.text for b in response.content if hasattr(b, 'text')), "")
                    yield dict(event="message", data=json.dumps({"chunk": final_text}))
                    yield dict(event="message", data=json.dumps({"chunk": "[DONE]"}))
                    break
                
                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            yield dict(event="message", data=json.dumps({"chunk": f"\n\n*[TAM ACTION] {block.name}...*\n\n"}))
                            
                            res_payload = await execute_tool(block.name, block.input)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(res_payload.get("result", ""))
                            })
                            if "hud_data" in res_payload:
                                yield dict(event="hud_update", data=json.dumps(res_payload["hud_data"]))
                    
                    messages.append({"role": "user", "content": tool_results})
                else: break
            
            if not final_text and iterations >= MAX_ITERATIONS:
                final_text = "Hit tool limit — responding with available info."
                yield dict(event="message", data=json.dumps({"chunk": final_text}))
                yield dict(event="message", data=json.dumps({"chunk": "[DONE]"}))
            
            await save_conversation(session_id, messages)

        except Exception as e:
            traceback.print_exc()
            yield dict(event="message", data=json.dumps({"error": str(e)}))
            yield dict(event="message", data=json.dumps({"chunk": "[DONE]"}))

    return EventSourceResponse(event_generator())

# Add GET /hud_data
@app.get("/hud_data")
async def hud_data():
    today = datetime.now().date().isoformat()
    tasks = await read_json(TASKS_FILE)
    habits = await read_json(HABITS_FILE)
    workouts = await read_json(WORKOUTS_FILE)
    meals = await read_json(MEALS_FILE)
    study = await read_json(STUDY_LOG_FILE)
    reminders = [r for r in await read_json(REMINDERS_FILE) if not r.get("fired")]
    
    gym_streak = calculate_consecutive_streak("gym", habits)
    
    # Calculate study hours week
    last_7_days = [(datetime.now() - timedelta(days=i)).isoformat()[:10] for i in range(7)]
    study_mins = sum(s.get("duration_minutes", 0) for s in study if s.get("date") in last_7_days)
    
    today_meals = [m for m in meals if m.get("date") == today]
    tc = sum(m.get("calories_estimate", 0) for m in today_meals)
    tp = sum(m.get("protein_estimate", 0) for m in today_meals)
    
    tasks_high = [t for t in tasks if t.get("priority") == "high" and not t.get("completed")]
    
    return {
        "gym_streak": gym_streak,
        "habits": habits,
        "study_hours_week": round(study_mins / 60, 1),
        "workout_streak": calculate_consecutive_streak("gym", habits), # Use same proxy
        "calories_today": tc,
        "protein_today": tp,
        "tasks_high": tasks_high[:5],
        "tasks": [t for t in tasks if not t.get("completed")], # Include all for queue list
        "reminders": reminders[:3],
        "mood": "neutral",
        "fitness": workouts[-5:],
        "study": study[-5:]
    }

@app.get("/events")
async def events_endpoint():
    async def event_generator():
        while True:
            try:
                # Use a combined wait for queue messages or a heartbeat timeout
                msg = await asyncio.wait_for(briefing_queue.get(), timeout=20.0)
                if isinstance(msg, dict) and "event" in msg and "data" in msg:
                    yield msg
                else:
                    yield dict(event="proactive", data=json.dumps(msg))
            except asyncio.TimeoutError:
                # Explicitly yield a keepalive that the browser understands
                yield dict(event="ping", data=json.dumps({"time": time.time()}))
            except Exception as e:
                print(f"[EVENTS] Error in generator: {e}")
                break
    return EventSourceResponse(event_generator())

# Allow quick dashboard checks
@app.get("/dashboard_pulse")
async def get_dashboard_pulse():
    calendar = []
    try: 
        # Making these safe to avoid blocking
        calendar = await asyncio.to_thread(calendar_tools.get_today_events)
    except: pass
    
    emails = []
    try: 
        emails = await asyncio.to_thread(gmail_tools.read_emails, max_results=3)
    except: pass
    
    return {
        "calendar": calendar if isinstance(calendar, list) else [],
        "inbox": {
            "unread_count": len(emails) if isinstance(emails, list) else 0,
            "urgent": emails[0]["subject"] if isinstance(emails, list) and emails else "No recent emails",
            "sender": emails[0]["from"] if isinstance(emails, list) and emails else ""
        }
    }
