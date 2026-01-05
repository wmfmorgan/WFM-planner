FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Copy .flaskenv if it exists
COPY .flaskenv* ./

# Create instance directory for SQLite database
RUN mkdir -p instance

# Set environment variables
ENV FLASK_APP=run.py
ENV FLASK_ENV=development

# Expose port
EXPOSE 5000

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
