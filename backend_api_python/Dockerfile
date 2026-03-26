# ZhiYiQuant Backend API Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create log and data directories
RUN mkdir -p logs data/memory

# Expose port
EXPOSE 5000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHON_API_HOST=0.0.0.0
ENV PYTHON_API_PORT=5000

# Start command
CMD ["python", "run.py"]
