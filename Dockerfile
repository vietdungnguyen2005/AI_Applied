FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.13.6
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
RUN groupadd --gid 10001 ai && useradd --uid 10001 --gid ai --create-home ai
WORKDIR /app
COPY --from=builder --chown=ai:ai /app/.venv /app/.venv
COPY --chown=ai:ai alembic.ini ./
COPY --chown=ai:ai migrations ./migrations
RUN mkdir -p /app/.local && chown -R ai:ai /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
ENTRYPOINT ["vmarket-ai"]
CMD ["serve"]
