FROM postgres:11-buster

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        postgis postgresql-11-postgis-2.5 postgresql-11-postgis-2.5-scripts

RUN localedef -i fi_FI -c -f UTF-8 -A /usr/share/locale/locale.alias fi_FI.UTF-8

ENV LANG fi_FI.UTF-8

# Openshift 
USER root
RUN usermod -a -G 0 postgres
RUN chgrp -R 0 /var/lib/pgsql && chmod g+rw -R /var/lib/pgsql
RUN chgrp -R 0 /var/run/postgresql && chmod g+rw -R /var/run/postgresql
RUN chgrp -R 0 /var/lib/postgresql/data && chmod g+rw -R /var/lib/postgresql/data
#USER postgres

#    find "$dir" -exec chown "$uid:0" {} \;
#    find "$dir" -exec chmod "g+r$write" {} \;
#    find "$dir" -type d -exec chmod g+x {} +

COPY ./docker-entrypoint.sh /docker-entrypoint-initdb.d/docker-entrypoint.sh
