# syntax=docker/dockerfile:1.7
#
# ai-engineering LiteLLM bridge — strict isolation.
#
# WHY DOCKER: LiteLLM 1.82.7/8 (March 2026) was a supply chain compromise that
# leaked cloud creds. We pin upstream by version, run unprivileged, drop all
# caps, and bind only 127.0.0.1. ADR-0008 has the rationale.
#
# Build:   docker build -t ai-engineering/litellm-bridge:dev .
# Run:     docker run --rm -p 127.0.0.1:4848:4848 \
#            -e AI_ENGINEERING_BRIDGE_TOKEN=... \
#            -e AI_ENGINEERING_ROUTING_PATH=/etc/ai-eng/routes.toml \
#            -v $PWD/routes.toml:/etc/ai-eng/routes.toml:ro \
#            --read-only --cap-drop=ALL --security-opt=no-new-privileges \
#            ai-engineering/litellm-bridge:dev

FROM python:3.13-slim AS base

# Create unprivileged user EARLY so subsequent layers run with predictable
# ownership. Using --uid 1000 keeps host bind-mounts readable in dev.
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# --- dependency layer ------------------------------------------------------
# We install dependencies in two phases:
#   1. Hard-pinned LiteLLM (NOT 1.82.x — the compromised range).
#   2. The bridge package itself, with --no-deps to lock the LiteLLM pin.
#
# Build-time dependency lock: this layer is cached unless pyproject changes.
COPY pyproject.toml ./
COPY src/ ./src/

# Install runtime deps. The hard pin on litellm==1.51.0 is non-negotiable —
# do NOT widen the bound. See ADR-0008.
# hadolint ignore=DL3013,DL3042
RUN pip install --no-cache-dir --upgrade pip==24.3.1 \
 && pip install --no-cache-dir \
      "litellm==1.51.0" \
      "fastapi>=0.115.0,<0.120.0" \
      "uvicorn[standard]>=0.32.0,<0.40.0" \
      "httpx>=0.27.0,<0.30.0" \
      "pydantic>=2.9.0,<3.0.0" \
 && pip install --no-cache-dir --no-deps -e .

# Drop privileges, harden runtime.
USER appuser
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Loopback-only by convention; the publish flag at run-time enforces it.
EXPOSE 4848

ENTRYPOINT ["python", "-m", "ai_eng_litellm_bridge", "serve", "--port", "4848"]
