FROM postgres:9.5

RUN apt-get update && apt-get install --no-install-recommends -y \
        postgis postgresql-9.5-postgis-2.4 postgresql-9.5-postgis-2.4-scripts

RUN localedef -i fi_FI -c -f UTF-8 -A /usr/share/locale/locale.alias fi_FI.UTF-8

ENV LANG fi_FI.UTF-8

COPY ./docker-entrypoint.sh /docker-entrypoint-initdb.d/docker-entrypoint.sh
