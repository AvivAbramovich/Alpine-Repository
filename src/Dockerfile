FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONIOENCODING UTF-8

WORKDIR /alpine-repo

ADD requirements.txt .

RUN apk update
RUN apk add abuild

RUN pip install -r requirements.txt

ENV DEFAULT_ARCH x86_64
ENV REPOISOTRY_PATH ''
ENV PRIV_KEY_PATH ''
ENV MAX_CONTENT_LENGTH ''
ENV CLEAN_ON_STRARTUP FALSE
ENV INDEXER_PORT 80
ENV LOG_LEVEL INFO

# Remote repository server
ENV REMOTE FALSE
ENV REMOTE_REPO_URL ''
ENV REMOTE_USERNAME ''
ENV REMOTE_PASSWORD ''

EXPOSE 80

RUN mkdir src
ADD *.py src/

CMD python -m src.docker_entrypoint