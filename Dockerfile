
FROM python:3.8

ENV APP_NAME respa

USER root

RUN adduser respa --home /usr/src/app

WORKDIR /usr/src/app

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get update && apt-get install -y gdal-bin postgresql-client gettext nodejs

COPY --chown=respa:respa requirements.txt .

COPY --chown=respa:respa deploy/requirements.txt ./deploy/requirements.txt

RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r deploy/requirements.txt

COPY --chown=respa:respa . .

RUN ./build-resources

RUN mkdir -p www/media

RUN ./manage.py compilemessages

USER respa

CMD ./deploy/server.sh
