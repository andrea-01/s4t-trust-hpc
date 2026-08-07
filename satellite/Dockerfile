FROM python:3.12-slim

WORKDIR /app

COPY satellite/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto directory and satellite app
COPY proto/ /app/proto/
COPY satellite/app/ /app/app/

# Generate Python stubs
RUN python -m grpc_tools.protoc -I/app/proto --python_out=/app/app --grpc_python_out=/app/app /app/proto/pipeline.proto

ENV PYTHONPATH=/app/app
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
