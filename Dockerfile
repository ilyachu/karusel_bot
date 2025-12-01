FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if any needed for Pillow or others)
# libgl1-mesa-glx is often needed for cv2, but for Pillow usually not unless specific codecs.
# We'll install curl just in case.
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create volume mount points if they don't exist (optional, but good practice)
# We expect assets/fonts to be present from the copy

# Run the bot
CMD ["python", "main.py"]
