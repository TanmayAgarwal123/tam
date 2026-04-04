import os
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from elevenlabs.client import ElevenLabs

router = APIRouter()

class SpeakRequest(BaseModel):
    text: str

@router.post("/speak")
async def speak(req: SpeakRequest):
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key or api_key == "your_elevenlabs_api_key_here":
        return StreamingResponse(iter([]), media_type="audio/mpeg")
        
    client = ElevenLabs(api_key=api_key)
    def generate():
        try:
            audio_stream = client.text_to_speech.convert(
                text=req.text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_turbo_v2_5"
            )
            for chunk in audio_stream:
                if chunk:
                    yield chunk
        except Exception as e:
            print("ElevenLabs Error:", e)

    return StreamingResponse(generate(), media_type="audio/mpeg")
