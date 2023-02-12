FROM python:3.10-alpine
MAINTAINER Artem Demidenko <ar.demidenko@gmail.com>

ENV DEBIAN_FRONTEND 'noninteractive'

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONIOENCODING 'utf-8'

ENV DJANGO_SETTINGS_MODULE 'system.settings'
ENV DJANGO_ALLOW_ASYNC_UNSAFE True
ENV DATABASE_URL ''

ENV PYTHONPATH "/opt/app/python:$PYTHONPATH"
ENV PATH "/opt/app/bin:$PATH"

ENV TZ=Europe/Moscow

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY ./requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm -rf /tmp/requirements.txt

RUN mkdir -p /opt/app/bin /opt/app/python /opt/app/pids /opt/app/logs /opt/app/storage
COPY ./src /opt/app/python

WORKDIR /opt/app/python

CMD ["runserver", "0.0.0.0:8000"]
ENTRYPOINT ["python", "manage.py"]
