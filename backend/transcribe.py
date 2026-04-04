import os
from fastapi import APIRouter, File, UploadFile
from deepgram import DeepgramClient, PrerecordedOptions

router = APIRouter()

@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        return {"transcript": ""}

    client = DeepgramClient(api_key)
    audio_data = await audio.read()

    options = PrerecordedOptions(
        model="nova-2",
        language="en-IN",
        smart_format=True,
        punctuate=True,
        keywords=["Tam:5", "HPML:3", "Divyanshi:3", "Columbia:2", "Anthropic:3"]
    )

    try:
        response = client.listen.rest.v("1").transcribe_file(
            {"buffer": audio_data}, 
            options
        )
        return {"transcript": response.results.channels[0].alternatives[0].transcript}
    except Exception as e:
        print("Deepgram error:", str(e))
        return {"transcript": ""}
