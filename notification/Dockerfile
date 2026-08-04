FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./notification/app/

# Expose port (even though we only use it for health check right now)
EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["uvicorn", "notification.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
