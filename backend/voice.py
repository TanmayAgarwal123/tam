from elevenlabs.client import ElevenLabs
from fastapi.responses import StreamingResponse
import os, io
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak")
async def speak(request: SpeakRequest):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return StreamingResponse(iter([]), media_type="audio/mpeg")
    
    eleven = ElevenLabs(api_key=api_key)
    try:
        audio = eleven.text_to_speech.convert(
            text=request.text,
            voice_id="JBFqnCBsd6RMkjVDRZzb",  # George — clear, neutral
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128"
        )
        audio_bytes = b"".join(audio)
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_bytes))}
        )
    except Exception as e:
        print("ElevenLabs Error:", e)
        return StreamingResponse(iter([]), media_type="audio/mpeg")
