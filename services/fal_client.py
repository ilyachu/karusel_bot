import fal_client
import os
import logging
from config import FAL_KEY

# Ensure the key is set in environment for the library to pick up, 
# or pass it explicitly if the library supports it. 
# The fal-client library typically looks for FAL_KEY env var.
os.environ["FAL_KEY"] = FAL_KEY if FAL_KEY else ""

def generate_background(prompt: str) -> str:
    # ...
    try:
        # ...
        result = fal_client.submit(
            "fal-ai/nano-banana",
            arguments={"prompt": prompt}
        ).get()
        logging.info(f"Fal.ai result: {result}") # Debug log
        
        if result and "images" in result and len(result["images"]) > 0:
            return result["images"][0]["url"]
        logging.warning("Fal.ai returned no images.")
        return ""
    except Exception as e:
        logging.error(f"Error in generate_background: {e}")
        return ""
