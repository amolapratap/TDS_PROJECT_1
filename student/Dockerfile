# Use an official lightweight Python image
FROM python:3.10-slim

# Create a non-root user for security
RUN useradd -m -u 1000 user
USER user

# Set working directory
WORKDIR /app

# Copy dependency file and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all other files (main.py, etc.)
COPY --chown=user . .

# Expose the Hugging Face required port
EXPOSE 7860

# Start the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
