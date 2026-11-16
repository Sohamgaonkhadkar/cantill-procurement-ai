FROM node:24-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev --ignore-scripts
COPY frontend ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY backend backend
COPY migrations migrations
COPY scripts scripts
COPY alembic.ini .
COPY --from=frontend-build /frontend/dist frontend/dist
RUN useradd --create-home corvo && mkdir -p /app/.private && chown -R corvo:corvo /app
USER corvo
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
