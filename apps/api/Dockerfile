FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /source

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml CMakeLists.txt CMakePresets.json README.md ./
COPY engine engine
COPY bindings bindings
COPY python python

RUN python -m pip wheel --wheel-dir /wheelhouse .

FROM python:3.12-slim AS runtime

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api/requirements.txt .
RUN python -m pip install --requirement requirements.txt

COPY --from=builder /wheelhouse /wheelhouse
RUN python -m pip install /wheelhouse/*.whl

COPY apps/api/app app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
