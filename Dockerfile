# Use a slim Python image to reduce size
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only necessary files first to leverage Docker caching
COPY requirements.txt .

# Install dependencies without cache to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose API port
EXPOSE 8000

# Set environment variables (handled via .env file in docker-compose.yml)
ENV SQLITE_DB_PATH=/app/f1_data_full_2025.db
ENV FASTF1_CACHE_DIR=/app/fastf1_cache

# Ensure the database and cache directories exist
RUN mkdir -p /app/fastf1_cache && touch /app/f1_data_full_2025.db

# Set the default command to start FastAPI with Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
