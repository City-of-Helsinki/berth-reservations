FROM public.ecr.aws/docker/library/postgres:13-bullseye

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        postgis postgresql-13-postgis-3 postgresql-13-postgis-3-scripts \
    && localedef -i fi_FI -c -f UTF-8 -A /usr/share/locale/locale.alias fi_FI.UTF-8

ENV LANG=fi_FI.UTF-8

# Openshift 
ENV PGDATA=/opt/app-root
USER root
RUN chgrp -R 0 /opt && chmod a+rw -R /opt
USER postgres

COPY ./docker-entrypoint.sh /docker-entrypoint-initdb.d/docker-entrypoint.sh
