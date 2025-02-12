# Base stage
# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy


RUN mkdir -p /app/backend

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv venv /app/backend/.venv && uv sync --frozen --no-install-project --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT=/app/backend/.venv

WORKDIR /pyspur/backend

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Development stage
FROM base AS development
# Development-specific instructions here

# Production stage
FROM base AS production
# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
# Start of Selection
ADD ./app ./templates ./entrypoint.sh ./pyproject.toml ./uv.lock /pyspur/backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev
# Production-specific instructions here
