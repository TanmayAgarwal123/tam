import os, sys
from dotenv import load_dotenv
load_dotenv(override=True)

api_key = os.environ.get("ELEVENLABS_API_KEY")
print("API KEY length:", len(api_key) if api_key else "None")

from elevenlabs.client import ElevenLabs
client = ElevenLabs(api_key=api_key)
try:
    print("Converting...")
    audio_stream = client.text_to_speech.convert(
        text="Hello test",
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_turbo_v2_5"
    )
    for i, chunk in enumerate(audio_stream):
        if chunk:
            print("Got chunk", i)
            break
except Exception as e:
    print("ElevenLabs Error:", e)
    
