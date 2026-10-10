FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir . && useradd --create-home chat
USER chat
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--no-access-log", "--ws-max-size", "65536"]
