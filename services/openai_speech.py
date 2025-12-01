from openai import AsyncOpenAI
import os
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def transcribe_voice(file_path: str) -> str:
    """
    Transcribes a voice file using OpenAI Whisper.
    """
    try:
        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        return transcription
    except Exception as e:
        print(f"Error in transcribe_voice: {e}")
        return ""
