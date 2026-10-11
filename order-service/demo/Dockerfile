FROM python:3.13-slim
WORKDIR /simulator
RUN pip install --no-cache-dir 'fastapi>=0.115,<1.0' 'uvicorn>=0.32,<1.0' 'aio-pika>=9.5,<10.0' \
    && addgroup --system simulator && adduser --system --ingroup simulator simulator \
    && mkdir /data && chown simulator:simulator /data
COPY credit_stub.py ./
USER simulator
CMD ["uvicorn", "credit_stub:from_environment", "--factory", "--host", "0.0.0.0", "--port", "8010", "--no-access-log"]
