FROM python:3.8-alpine

WORKDIR /code

RUN apk update
RUN apk add abuild

ADD requirements.txt .

RUN pip install -r requirements.txt

ENV UPLOADED_FILES_PATH /tmp
ENV PRIV_KEY_PATH ''
ENV MAX_CONTENT_LENGTH ''

EXPOSE 80

CMD python -m docker_entrypoint