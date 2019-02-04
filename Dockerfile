
FROM python:3.6

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN apt-get update && apt-get install -y gdal-bin postgresql-client

COPY requirements.txt .
COPY deploy/requirements.txt ./deploy/requirements.txt

RUN pip install --no-cache-dir -r deploy/requirements.txt

COPY . .

RUN mkdir -p www/media

CMD deploy/server.sh
