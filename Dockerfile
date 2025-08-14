# Build + runtime in one stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BVSIM_WEB_HOST=0.0.0.0 \
    BVSIM_WEB_PORT=8000 \
    BVSIM_WEB_DEBUG=0

# System deps (add more if needed by libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Build/install app
WORKDIR /app
COPY setup.py README.md /app/
COPY src/ /app/src/

# Runtime deps, then install package
RUN pip install --upgrade pip \
 && pip install "flask>=2.2" gunicorn pyyaml \
 && pip install .

# Bake templates and entrypoint; data dir used at runtime
COPY templates/ /opt/bvsim-templates/
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
RUN mkdir -p /data
WORKDIR /data

# Bake demo data (can be overridden with -v /path/to/data:/data)
COPY data/ /data/

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
