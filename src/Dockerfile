FROM python:3.8-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONIOENCODING UTF-8

WORKDIR /alpine-repo

ADD requirements.txt .

RUN apk update
RUN apk add abuild

RUN pip install -r requirements.txt

ENV REPOISOTRY_PATH /repo
# ENV UPLOADED_FILES_PATH /tmp
ENV PRIV_KEY_PATH ''
ENV MAX_CONTENT_LENGTH ''
ENV CLEAN_ON_STRARTUP FALSE

EXPOSE 80

RUN mkdir src
ADD *.py src/

CMD python -m src.docker_entrypoint