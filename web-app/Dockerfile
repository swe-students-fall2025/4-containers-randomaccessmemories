# Dockerfile for Web App
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY Pipfile* ./
RUN pip install pipenv && pipenv install --deploy --system

# Copy the rest of the code
COPY . .

# Set environment variables (optional, can be overridden by docker-compose or .env)
ENV PYTHONUNBUFFERED=1

# Expose Flask default port
EXPOSE 5000

# Default command (run the app)
CMD ["python", "app.py"]
