# Dockerfile for Machine Learning Client
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY Pipfile* ./
RUN pip install pipenv && pipenv install --deploy --system

# Copy the rest of the code
COPY . .

# Set environment variables (optional, can be overridden by docker-compose or .env)
ENV PYTHONUNBUFFERED=1

# Default command (update as needed)
CMD ["python", "main.py"]
