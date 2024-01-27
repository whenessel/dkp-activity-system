FROM python:3.12.1-alpine as builder
MAINTAINER Artem Demidenko <ar.demidenko@gmail.com>

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf8 \
    GIT_PYTHON_REFRESH="quiet" \
    GIT_DISCOVERY_ACROSS_FILESYSTEM=1

RUN set -ex \
    && apk add --update --no-cache gcc musl-dev libffi-dev

RUN pip install poetry==1.7.1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without=dev,test


FROM python:3.12.1-alpine as runtime
MAINTAINER Artem Demidenko <ar.demidenko@gmail.com>

ENV PYTHONUNBUFFERED=1 \
    PYTHONHTTPSVERIFY=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING="utf8" \
    PYTHONPATH="/app/src:$PYTHONPATH" \
    VIRTUAL_ENV="/app/.venv" \
    PATH="/app/src:/app/.venv/bin:$PATH" \
    TZ="Europe/Moscow" \
    DATABASE_URL="" \
    DJANGO_ALLOW_ASYNC_UNSAFE="True" \
    DJANGO_SETTINGS_MODULE="system.settings"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY src /app/src

RUN mkdir -p /app/{storage,media,static,secret,logs}

WORKDIR /app

CMD ["runserver", "0.0.0.0:8000"]
ENTRYPOINT ["python", "src/manage.py"]
