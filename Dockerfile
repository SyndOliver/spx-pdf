FROM python:3.11-slim

# Cài font cho Linux (dùng cho bold text trong PDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-liberation fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY spx.py bot.py ./

CMD ["python", "bot.py"]
