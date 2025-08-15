# Build + runtime in one stage
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BVSIM_WEB_HOST=0.0.0.0 \
    BVSIM_WEB_PORT=8000 \
    BVSIM_WEB_DEBUG=0

# System deps (add more if needed by libs)
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC apt-get update \
 && apt-get install -y --no-install-recommends \
     build-essential tzdata ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Build/install app
WORKDIR /app

# Install runtime deps via requirements.txt (cache-friendly)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install -r /app/requirements.txt

# Then copy package sources and install the package
COPY setup.py README.md /app/
COPY src/ /app/src/
RUN pip install .

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
