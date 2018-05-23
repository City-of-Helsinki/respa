
FROM python:3

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN apt-get update && apt-get install -y libgdal1h

COPY requirements.txt .
COPY deploy/requirements.txt ./deploy/requirements.txt

RUN pip install --no-cache-dir -r deploy/requirements.txt

COPY . .

CMD deploy/server.sh
