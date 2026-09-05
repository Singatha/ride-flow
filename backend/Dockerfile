FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

FROM base AS development
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir --editable '.[dev]'
COPY alembic.ini ./
COPY migrations ./migrations
COPY tests ./tests
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production
RUN addgroup --system rideflow && adduser --system --ingroup rideflow rideflow
COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations
USER rideflow
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

