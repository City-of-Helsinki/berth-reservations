FROM postgres:11-buster

#ENV HOME=/var/lib/pgsql \
#    PGUSER=postgres \
#    HOME=/var/lib/pgsql \
#    APP_DATA=/opt/app-root \
ENV PGDATA=/opt/app-root

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        postgis postgresql-11-postgis-2.5 postgresql-11-postgis-2.5-scripts

RUN localedef -i fi_FI -c -f UTF-8 -A /usr/share/locale/locale.alias fi_FI.UTF-8

ENV LANG fi_FI.UTF-8

#RUN mkdir -p /var/lib/pgsql/data
#RUN mkdir -p $APP_DATA

# Openshift 
USER root
#RUN usermod -a -G 0 postgres
#RUN chgrp -R 0 /var/lib/pgsql && chmod g+rw -R /var/lib/pgsql
#RUN chgrp -R 0 /var/run/postgresql && chmod 777 -R /var/run/postgresql
#RUN chgrp -R 0 /var/lib/postgresql && chmod 777 -R /var/lib/postgresql
#RUN chgrp -R 0 /var/lib/pgsql && chmod 777 -R /var/lib/pgsql
RUN chgrp -R 0 /opt && chmod a+rw -R /opt
#RUN chown "26:0" $APP_DATA
#USER postgres

#chmod: changing permissions of '/var/lib/postgresql/data': Toiminto ei ole sallittu
#chmod: changing permissions of '/var/run/postgresql': Toiminto ei ole sallittu
#    find "$dir" -exec chown "$uid:0" {} \;
#    find "$dir" -exec chmod "g+r$write" {} \;
#    find "$dir" -type d -exec chmod g+x {} +

USER postgres

COPY ./docker-entrypoint.sh /docker-entrypoint-initdb.d/docker-entrypoint.sh
