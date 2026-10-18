FROM node:20.20.0-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

FROM python:3.12.10-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PORT=8000 RSS_ANALYSIS_ENABLED=false
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home --uid 10001 radar
COPY app/ ./app/
COPY reference/jev_requests.py reference/scoring.py ./reference/
COPY config/risk_policy.json config/rss_sources.json config/authorization.json config/geography.json ./config/
COPY contracts/ ./contracts/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY --from=frontend /build/dist ./frontend/dist/
USER radar
EXPOSE 8000
CMD ["python", "-m", "app.web"]
