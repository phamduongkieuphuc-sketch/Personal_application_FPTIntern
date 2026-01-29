# 1. Use an official Python image
FROM python:3.11-slim

# 2. Set working directory inside container
WORKDIR /app

# 3. Copy dependency list first (better caching)
COPY requirement.txt .

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirement.txt

# 5. Copy application code
COPY db_extract_sample.py .

# 6. Expose the port FastAPI runs on
EXPOSE 8000

# 7. Command to run the app
CMD ["uvicorn", "db_extract_sample:app", "--host", "0.0.0.0", "--port", "8000"]
