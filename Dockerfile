# Using official Python 3.11 lightweight image
FROM python:3.11-slim

# Setting the working directory inside the container
WORKDIR /app

# Installing system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copying and installing Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copying the entire project code into the container
COPY . .

# Exposing the Django port
EXPOSE 8000

# Command to run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
