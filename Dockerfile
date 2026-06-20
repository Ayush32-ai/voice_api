FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg required for dubbing pipeline)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create working directories
RUN mkdir -p uploads temp logs

EXPOSE 8000

CMD ["python", "railway_start.py"]