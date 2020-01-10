# syntax=docker/dockerfile:1.0.0-experimental

FROM python:3
EXPOSE 8000

ENV PYTHONUNBUFFERED 1

RUN apt-get install git openssh-client
RUN pip install --upgrade pip setuptools

# Always accept github host key...
RUN mkdir -p /root/.ssh/ \
 && touch /root/.ssh/known_hosts \
 && ssh-keyscan github.com >> /root/.ssh/known_hosts
RUN cat /root/.ssh/known_hosts

WORKDIR /app
RUN mkdir var
COPY . .

RUN --mount=type=ssh pip install -e ".[testing]"

CMD pserve development.ini