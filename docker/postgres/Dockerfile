FROM postgres:12

RUN apt-get update && apt-get install --no-install-recommends -y postgis postgresql-12-postgis-3 postgresql-12-postgis-3-scripts

RUN localedef -i fi_FI -c -f UTF-8 -A /usr/share/locale/locale.alias fi_FI.UTF-8

ENV LANG fi_FI.UTF-8

RUN psql template1 -c "create extension hstore;"

COPY ./docker-entrypoint.sh /docker-entrypoint-initdb.d/docker-entrypoint.sh
