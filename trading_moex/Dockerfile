FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps "git+https://github.com/Tinkoff/invest-python.git@main"

COPY . .

RUN mkdir -p /app/data/candles \
    && useradd -m botuser && chown -R botuser:botuser /app

USER botuser

EXPOSE 8081

CMD ["python", "main.py"]
