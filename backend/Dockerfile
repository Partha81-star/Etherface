FROM node:22.13-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential cmake libgl1 libglib2.0-0 python3 python3-dev python3-venv \
    && python3 -m venv /opt/venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY backend/requirements.txt backend/requirements-dlib.txt ./backend/
RUN python -m pip install -r backend/requirements-dlib.txt \
    || python -m pip install -r backend/requirements.txt

COPY chain/package.json chain/package-lock.json ./chain/
RUN cd chain && npm ci

COPY chain ./chain
COPY backend ./backend
COPY scripts/backend-entrypoint.sh ./scripts/backend-entrypoint.sh
RUN chmod +x ./scripts/backend-entrypoint.sh \
    && cd chain && npm run compile

WORKDIR /workspace/backend
EXPOSE 8000
ENTRYPOINT ["/workspace/scripts/backend-entrypoint.sh"]
