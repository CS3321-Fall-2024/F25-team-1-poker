# Use the official lightweight Python 3.11 base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements first for efficient Docker caching
COPY requirements.txt .

# Install Python dependencies without caching to keep the image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the container
COPY app.py .
COPY index.html .
COPY Procfile .
COPY README.md .

# Expose port 8000 so the app can be accessed externally
EXPOSE 8000

# Run the app using Hypercorn with asyncio worker class
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8000", "--worker-class", "asyncio"]
