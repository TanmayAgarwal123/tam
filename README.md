# Tam — Personal AI Life OS

> Not a chatbot. An operating system for your life.

Tam is a voice-first personal AI built on Claude Haiku, designed to act on your behalf — not just respond. Persistent memory, real tool use, proactive behavior, and a live mission control HUD. Built from scratch in 4 weeks by a 23-year-old MS CS student at Columbia.

**[Live Demo](https://tam-ai.vercel.app)** · **[Portfolio Page](https://tanmayresume.com)** · **[Watch the Demo Video](#)**

---
To always run TAM properly:- 
# Terminal 1 — Backend
cd "tam/backend" && uvicorn main:app --reload

# Terminal 2 — Frontend  
cd "tam/frontend" && npm run dev

---

## What makes Tam different from a chatbot

Most AI tools are reactive — you ask, they answer. Tam is different in three ways:

**Persistent memory.** Tam reads and writes `MEMORY.md` across every session. It knows your goals, your sister's name, your gym streak, your visa timeline. Tell it something once — it remembers forever.

**Real tool use.** Claude doesn't just talk about doing things. It calls Python functions that actually execute. Log a workout → `workouts.json` is updated. Set a reminder → it fires in 45 minutes and Tam speaks unprompted.

**Proactive behavior.** Morning briefing at 7:30 AM. Reminders that interrupt you. If you haven't logged gym in 2 days, Tam mentions it. It acts before you ask.

---

## Demo

```
You: "I just did 1 hour of weights at the gym."

[TAM ACTION] log_workout...
[TAM ACTION] log_habit...

Tam: "Logged. Four days this week — best streak this month.
      Protein's at 62 grams today, you need 88 more."

— 45 minutes later, unprompted —

Tam: "Tanmay — time to eat. You're still short on protein."
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| AI brain | Claude Haiku (`claude-haiku-4-5-20251001`) | Tool use, agentic loop, 5-iteration cap |
| Voice in | Deepgram Nova-2 (`en-IN`) | Indian English, keyword boosting |
| Voice out | ElevenLabs `eleven_turbo_v2_5` | Lowest latency TTS |
| Backend | FastAPI + SSE | Streaming, real-time HUD events |
| Frontend | React + Tailwind | Two-panel HUD, voice mode, barge-in |
| Memory | MEMORY.md + JSON files | Flat-file persistence, no database needed |
| Scheduler | APScheduler | 7:30 AM briefing, 10 PM nightly sync |

---

## Features

### Voice system
- Continuous hands-free loop — speak, Tam responds, Tam listens again
- Barge-in interruption — say something and Tam stops mid-sentence
- Silence detection — stops recording after 1.5s of silence automatically
- Accent-aware — Deepgram `en-IN` with custom keyword boosting for proper nouns

### Memory & intelligence
- Reads and writes `MEMORY.md` in real time across all sessions
- Emotional check-in — detects stress/energy from your words, adjusts tone
- Pattern awareness — flags if you haven't logged gym or HPML in 2+ days
- Mood log — appends emotional state entries with timestamps

### Tools (14 total)
```
update_memory    get_memory       log_habit        log_workout
suggest_workout  log_meal         get_nutrition_summary
log_study_session add_research_note get_research_notes
add_task         complete_task    set_reminder     get_habit_streak
```

### Live HUD (right panel, updates in real time)
- System status + mood indicator dot
- Today's calendar events
- Inbox pulse — unread count + most urgent email
- Habit streaks — gym, study, sleep
- Fitness today — calories, protein vs targets
- Study this week — hours by subject
- Priority queue — top 5 tasks with checkboxes
- Core memory pulse — last 3 things Tam learned

### Proactive features
- Morning briefing at 7:30 AM — calendar, emails, AI news, habit summary
- Nightly sync at 10 PM — day wrap-up, what rolls to tomorrow
- Reminders fire and Tam speaks without any user input
- Trigger manually: *"Tam, brief me"*

---

## Project Structure

```
tam/
├── backend/
│   ├── main.py              # FastAPI app, agentic loop, all tool handlers
│   ├── scheduler.py         # APScheduler — morning briefing, nightly sync
│   ├── voice.py             # ElevenLabs TTS endpoint
│   ├── transcribe.py        # Deepgram STT endpoint
│   ├── gmail_tools.py       # Gmail read/draft/send
│   ├── calendar_tools.py    # Google Calendar read/create
│   ├── slack_tools.py       # Slack read/post
│   ├── google_auth.py       # OAuth flow for Google APIs
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main app, SSE listener, voice mode
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── InputBar.tsx
│   │   │   ├── VoiceMode.tsx
│   │   │   ├── HUDPanel.tsx
│   │   │   └── StatusBar.tsx
│   └── package.json
├── memory/
│   ├── MEMORY.md            # Tam's long-term memory — edit this freely
│   ├── habits.json          # Habit log entries
│   ├── workouts.json        # Workout sessions
│   ├── meals.json           # Meal and nutrition log
│   ├── tasks.json           # Task list
│   ├── reminders.json       # Pending reminders
│   ├── study_log.json       # Study sessions by subject
│   ├── research_notes.json  # Saved research insights
│   └── conversations/       # Per-session conversation history
├── tam-portfolio/
│   └── index.html           # Standalone portfolio page
└── README.md
```

---

## Setup — Run Your Own Tam

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys (see below)

### 1. Clone and install

```bash
git clone https://github.com/tanmayagarwal/tam.git
cd tam

# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configure environment

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
DEEPGRAM_API_KEY=your_key_here

# Optional — for Gmail + Calendar
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Optional — for Slack
SLACK_BOT_TOKEN=your_bot_token

# Optional — for Spotify
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
```

**Getting API keys (all have free tiers):**
- Anthropic: [console.anthropic.com](https://console.anthropic.com) — Claude API
- ElevenLabs: [elevenlabs.io](https://elevenlabs.io) — 10k chars/month free
- Deepgram: [console.deepgram.com](https://console.deepgram.com) — 200 hours/month free

### 3. Personalize your memory

Edit `memory/MEMORY.md` to make Tam yours. The file is plain text — add your name, goals, context, rules. Tam reads it on every conversation.

### 4. Run

```bash
# Terminal 1 — backend
cd backend
uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Open `http://localhost:5173`. Click the microphone icon. Say hello to Tam.

### 5. Connect Google (optional)

```bash
# Visit in browser after backend starts
http://localhost:8000/auth/google
```

Follow the OAuth flow. Your Gmail and Calendar will be live in Tam.

---

## Cost

Tam is cheap to run. At normal daily usage:

| Usage | Monthly cost |
|---|---|
| Light (10 conversations/day) | ~$1–2 |
| Normal (30 conversations/day) | ~$3–5 |
| Heavy (80 conversations/day) | ~$8–12 |

Cost optimizations built in:
- Haiku for all API calls (20x cheaper than Sonnet)
- Tool-calling turns capped at 256 tokens
- Sliding window — last 6 conversation turns only
- MEMORY.md cached for 5 minutes, not re-read every request
- Daily spend tracker with configurable hard limit

---

## Teaching Tam Something New

Tam learns in two ways:

**In conversation** — just tell it:
> "My gym membership is at LA Fitness on 23rd Street, remember that."

Tam calls `update_memory` and writes it to MEMORY.md immediately.

**Directly in the file** — open `memory/MEMORY.md` and add anything. Tam reads it next conversation. You can add entire sections, correct facts, or delete outdated info.

---

## Extending Tam

Adding a new tool takes about 10 minutes:

1. Define the tool in the `TOOLS` array in `main.py`
2. Write the Python handler function
3. Add it to the `execute_tool()` switch statement
4. Tell Tam about it in the system prompt

That's it. Claude will start using it automatically.

---

## Roadmap

- [ ] Mobile app (React Native)
- [ ] Gmail integration (imaplib — no OAuth required)
- [ ] Slack via Incoming Webhooks
- [ ] Image input — show Tam a photo of your food for calorie estimation
- [ ] Deploy to Raspberry Pi — Tam runs on hardware in your room
- [ ] Multi-user support — run Tam for your whole family

---

## Built By

**Tanmay Agarwal** — MS Computer Science, Columbia University (Dec 2026)

LLM Research Assistant at Columbia · Swami Vivekanand Scholar · PDL Fellow

I built Tam because I wanted to understand what it actually takes to make AI that acts — not just responds. Every part of this was built from scratch: the voice pipeline, the agentic loop, the memory system, the HUD. No templates, no starter kits.

If you build your own Tam, I'd love to hear about it.

**[LinkedIn](https://linkedin.com/in/tanmayagarwal)** · **[tanmayresume.com](https://tanmayresume.com)** · **ta2830@columbia.edu**

---

## License

MIT — use it, modify it, make it yours.

If you build something cool with Tam, star the repo and let me know.


# Tam AI OS

Your intelligent life OS, built with React, Vite, Tailwind CSS v4, and FastAPI.

## How to Run Locally

### 1. Start the Backend
```bash
cd backend
uvicorn main:app --reload
```
The backend API and Memory Core reader will start on `http://localhost:8000`.

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```
The sci-fi glass-morphism interface will open at `http://localhost:5173`.

## Capabilities
- **Memory Core (`MEMORY.md`)**: Tam reads this file before every response. You don't need to restart the server when you edit this file.
- **Voice Input**: Click the microphone icon to transcribe your speech into the command line. It will not auto-send until you press Enter or click Send, allowing you to edit garbled text.
- **Voice Output**: Tam speaks response aloud using SpeechSynthesis TTS. Toggle mute via the speaker icon in the top right.

## Teaching Tam New Things
Because Tam is stateless across restarts but reads the Memory Core dynamically:
1. Open `tam/memory/MEMORY.md`.
2. Add facts under "Current Context" or "Rules".
3. The UI will automatically reflect the "last updated" time of the memory core on next load.

## Adding New MCP Servers (Week 2)
When you're ready to connect Tam to local tools via Model Context Protocol:
1. Install an MCP python host or client in `backend/`.
2. Set up the tools in `main.py` before calling the Anthropic API.
3. Supply those tools inside the `client.messages.stream` arguments.
