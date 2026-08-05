FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV GATEWAY_URL=http://gateway:8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
