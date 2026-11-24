# syntax=docker/dockerfile:1

# ---------- Етап 1: збирання залежностей ----------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Компілятори потрібні лише тут (на випадок залежностей без готових wheel)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Етап 2: мінімальний робочий образ ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

# Звичайний користувач замість root
RUN groupadd --system app && useradd --system --gid app --home-dir /app app

# Лише готове віртуальне середовище: без компіляторів і кешів збирання
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/live', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
