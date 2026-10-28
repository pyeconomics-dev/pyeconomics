# Dockerfile
# Multi-stage hosted-service container (ROADMAP §4 4.7; ADR-0012 decision 19).
# Contains only the wheel and the [server], [mcp], [econometrics], [plot] and
# [sdmx] extras plus pyarrow (for hosted Parquet/Arrow downloads), all verified
# against uv.lock hashes. No library-only provider extra (yfinance), keyring,
# AI client or Bloomberg library is installed.

FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

FROM python:3.14-slim-bookworm@sha256:9974e24551f9e7ca172cf284d85b8ab3e031d22d945f7026ede7a8279118c9f1 AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /build

COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./

RUN uv export \
        --no-config \
        --frozen \
        --no-dev \
        --extra server \
        --extra mcp \
        --extra econometrics \
        --extra plot \
        --extra sdmx \
        --no-emit-project \
        --output-file /build/requirements.txt \
    && python -c "\
import pathlib, tomllib; \
req = pathlib.Path('/build/requirements.txt'); \
lock = tomllib.loads(pathlib.Path('uv.lock').read_text('utf-8')); \
pkg = next(p for p in lock['package'] if p['name'] == 'pyarrow'); \
sep = ' ' + chr(92) + chr(10) + '    --hash='; \
hashes = ''.join(sep + w['hash'] for w in pkg['wheels']); \
req.write_text(req.read_text('utf-8') + 'pyarrow==' + pkg['version'] + hashes + chr(10), encoding='utf-8')"

COPY src/ ./src/

RUN uv build --no-config --wheel --out-dir /build/dist


FROM python:3.14-slim-bookworm@sha256:9974e24551f9e7ca172cf284d85b8ab3e031d22d945f7026ede7a8279118c9f1 AS runtime

ARG GIT_SHA=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYECONOMICS_MODE=hosted \
    PYECONOMICS_CACHE_DIR=/tmp/pyeconomics-cache \
    PYECONOMICS_GIT_SHA=${GIT_SHA} \
    PORT=8080

RUN apt-get update \
    && apt-get dist-upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 pyeconomics \
    && useradd \
        --system \
        --uid 10001 \
        --gid 10001 \
        --home-dir /nonexistent \
        --no-create-home \
        --shell /usr/sbin/nologin \
        pyeconomics

COPY --from=build /build/requirements.txt /tmp/requirements.txt

RUN python -m pip install \
        --no-cache-dir \
        --require-hashes \
        --only-binary :all: \
        --no-deps \
        -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

COPY --from=build /build/dist/*.whl /tmp/

RUN python -m pip install \
        --no-cache-dir \
        --no-deps \
        /tmp/*.whl \
    && python -m pip uninstall -y pip \
    && rm -rf /tmp/*.whl /root/.cache

WORKDIR /app

USER pyeconomics:pyeconomics

EXPOSE 8080

CMD ["python", "-m", "pyeconomics.server"]
