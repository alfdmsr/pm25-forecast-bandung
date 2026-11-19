FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/appuser \
    PORT=7860 \
    LAYANAN=ui

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout 180 --retries 10 -r requirements.txt

COPY . .

RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser \
    && chown -R 1000:1000 /app

USER 1000

EXPOSE 7860
CMD ["bash", "start.sh"]
