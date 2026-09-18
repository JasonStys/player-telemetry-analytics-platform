# File: Dockerfile
# Purpose: Build a reproducible non-root Python API image with the SQL assets required at runtime.
FROM python:3.13.15-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
RUN addgroup --system telemetry && adduser --system --ingroup telemetry telemetry
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY sql ./sql
RUN python -m pip install --no-cache-dir .
RUN mkdir -p /data && chown -R telemetry:telemetry /app /data

USER telemetry
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["uvicorn", "telemetry_platform.api:app", "--host", "0.0.0.0", "--port", "8000"]
