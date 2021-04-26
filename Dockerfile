
FROM python:3.6

WORKDIR /usr/src/app

ENV APP_NAME respa

RUN apt-get update && apt-get install -y gdal-bin postgresql-client npm gettext

COPY requirements.txt .

COPY deploy/requirements.txt ./deploy/requirements.txt

RUN pip install --no-cache-dir -r deploy/requirements.txt

COPY . .

RUN npm install -g npm && ./build-resources && apt-get remove -y npm && apt autoremove -y

RUN mkdir -p www/media

RUN ./manage.py compilemessages

CMD ./deploy/server.sh
