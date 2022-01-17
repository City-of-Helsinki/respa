
FROM python:3.6

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt-get update && apt-get install -y gdal-bin postgresql-client gettext nodejs

COPY requirements.txt .

COPY deploy/requirements.txt ./deploy/requirements.txt

RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r deploy/requirements.txt

COPY . .

RUN ./build-resources

RUN mkdir -p www/media

RUN ./manage.py compilemessages

CMD ./deploy/server.sh
