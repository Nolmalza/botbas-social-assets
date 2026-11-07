FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libraqm0 libfribidi0 libharfbuzz0b \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ /app/
RUN python -c "from PIL import features; assert features.check('raqm'), 'raqm missing (Thai text layout)'"
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8090
# single worker on purpose: in-process job queue
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "1"]
