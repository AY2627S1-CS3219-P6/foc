FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install .

RUN groupadd --system supplier_service \
    && useradd --system --gid supplier_service supplier_service
USER supplier_service

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
