FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY index.html .
COPY Procfile .
COPY README.md .
EXPOSE 8000
CMD ["hypercorn", "app:app", "--bind", "0.0.0.0:8000", "--worker-class", "asyncio"]
