FROM python:3.11-slim

# Create a non-root user with UID 1000 required by Hugging Face Spaces
RUN useradd -m -u 1000 user

# Set working directory and environment variables
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0

WORKDIR $HOME/app

# Install dependencies first for optimal Docker layer caching
COPY --chown=user:user requirements.txt $HOME/app/requirements.txt
RUN pip install --no-cache-dir --user -r $HOME/app/requirements.txt

# Copy the rest of the application files
COPY --chown=user:user . $HOME/app

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Launch FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
