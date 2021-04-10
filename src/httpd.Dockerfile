FROM httpd:2.4-alpine

ENV PYTHONUNBUFFERED 1
ENV PYTHONIOENCODING UTF-8

WORKDIR /alpine-repo

RUN apk update && apk add python3 py3-pip

ADD requirements.txt .

RUN apk update
RUN apk add abuild

RUN pip install -r requirements.txt

ENV ARCH x86_64
ENV PRIV_KEY_PATH ''
ENV MAX_CONTENT_LENGTH ''
ENV CLEAN_ON_STRARTUP FALSE
ENV INDEXER_PORT 5000
ENV REPOISOTRY_PATH /usr/local/apache2/htdocs/${ARCH}

EXPOSE 80
EXPOSE 5000

RUN mkdir src
ADD *.py src/

CMD httpd-foreground & python3 -m src.docker_entrypoint