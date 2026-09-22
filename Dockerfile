# Stage 1: build opencode binary
FROM node:22-slim@sha256:83f487e0a63425e5b4d146fb5e5be574bcbe1b7b843d3ebafdd95eaf7767a7e5 AS opencode
RUN npm install -g opencode-ai@1.18.8

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy opencode binary (self-contained, no node needed at runtime)
COPY --from=opencode /usr/local/bin/opencode /usr/local/bin/opencode
COPY --from=opencode /usr/local/lib/node_modules/opencode-ai /usr/local/lib/node_modules/opencode-ai

# Copy application code
COPY . .

# Create directories for SQLite
RUN mkdir -p /app/data /app/dbdata

# Run as non-root
RUN useradd -m botuser && chown -R botuser:botuser /app \
    && mkdir -p /home/botuser/.local/share /home/botuser/.local/state /home/botuser/.config \
    && chown -R botuser:botuser /home/botuser/.local /home/botuser/.config
USER botuser

CMD ["python", "main.py"]
