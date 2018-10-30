FROM python:3.6

ENV PYTHONUNBUFFERED 0

RUN apt-get update \
    && apt-get install --no-install-recommends -y gdal-bin python-gdal python3-gdal

RUN mkdir /code

COPY requirements.txt /code/

WORKDIR /code

RUN pip install --upgrade pip \
    && pip install -r /code/requirements.txt \
    && pip install pip-tools

COPY . /code
