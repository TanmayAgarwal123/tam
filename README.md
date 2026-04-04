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
