FROM python:3.5

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN apt-get update && apt-get install -y libgdal1h postgresql-client-9.4

COPY requirements.txt ./requirements.txt
COPY dev-requirements.txt ./dev-requirements.txt

RUN pip install --no-cache-dir -r dev-requirements.txt

COPY . .

RUN echo 'alias rs="python manage.py runserver 0:8000"' >> ~/.bashrc
