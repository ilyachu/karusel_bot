import logging

from openai import AsyncOpenAI
from config import NEURALDEEP_API_KEY, NEURALDEEP_BASE_URL, OPENAI_API_KEY

client = AsyncOpenAI(
    api_key=NEURALDEEP_API_KEY or OPENAI_API_KEY,
    base_url=NEURALDEEP_BASE_URL,
)

async def transcribe_voice(file_path: str) -> str:
    try:
        with open(file_path, "rb") as audio_file:
            transcription = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcription
    except Exception as e:
        logging.error(f"Error in transcribe_voice: {e}")
        return ""
