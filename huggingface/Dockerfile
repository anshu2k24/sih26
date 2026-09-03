FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860 \
    HOME=/home/user \
    HF_HOME=/home/user/.cache/huggingface \
    PATH=/home/user/.local/bin:$PATH

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Hugging Face Spaces runs as user 1000)
RUN useradd -m -u 1000 user && \
    mkdir -p /home/user/app /home/user/.cache/huggingface && \
    chown -R user:user /home/user

WORKDIR /home/user/app

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Switch to non-root user
USER user

# Pre-cache the default embedding model in user's home directory
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY --chown=user:user app.py .

EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
