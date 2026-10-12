FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py judge.py storage.py ./
ENV FLASK_ENV=production
ENV RESULTS_PATH=/data/results.json
CMD ["python", "app.py"]
