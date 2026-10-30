FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .
RUN addgroup --system voice_assist && adduser --system --ingroup voice_assist voice_assist
USER voice_assist

EXPOSE 8006
HEALTHCHECK --interval=10s --timeout=7s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8006/health/ready', timeout=6)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006", "--no-access-log"]
