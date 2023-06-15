FROM python:3.8-bullseye

ENV APP_NAME respa

USER root

RUN adduser respa --home /usr/src/app

WORKDIR /usr/src/app

RUN curl -sL https://deb.nodesource.com/setup_14.x | bash -
RUN apt-get update && apt-get install -y gdal-bin postgresql-client gettext nodejs

COPY --chown=respa:respa requirements.txt ./requirements.txt
COPY --chown=respa:respa dev-requirements.txt ./dev-requirements.txt

COPY --chown=respa:respa . .

RUN pip install --no-cache-dir -r dev-requirements.txt

USER respa

RUN echo 'alias rs="python manage.py runserver 0:8000"' >> ~/.bashrc
