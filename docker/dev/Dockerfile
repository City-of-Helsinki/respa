FROM python:3.8

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get update && apt-get install -y gdal-bin postgresql-client gettext nodejs

COPY requirements.txt ./requirements.txt
COPY dev-requirements.txt ./dev-requirements.txt

RUN pip install --no-cache-dir -r dev-requirements.txt

COPY . .

RUN echo 'alias rs="python manage.py runserver 0:8000"' >> ~/.bashrc
