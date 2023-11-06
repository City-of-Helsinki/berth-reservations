# Build a base image for development and production stages.
# Note that this stage won't get thrown out so we need to think about
# layer sizes from this point on.
FROM helsinkitest/python:3.9-slim as appbase

# Copy requirement files.
COPY --chown=appuser:appuser requirements.txt /app/

# Install main project dependencies and clean up.
# Note that production dependencies are installed here as well since
# that is the default state of the image and development stages are
# just extras.
RUN apt-install.sh \
  build-essential \
  libpq-dev \
  netcat-traditional \
  gdal-bin \
  python3-gdal \
  gettext \
  pkg-config \
  && pip install -U pip \
  && pip install --no-cache-dir -r /app/requirements.txt \
  && apt-cleanup.sh build-essential pkg-config


# Copy and set the entrypoint.
COPY --chown=appuser:appuser docker-entrypoint.sh /app
ENTRYPOINT ["./docker-entrypoint.sh"]

ENV STATIC_ROOT /var/berth/static
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir -p /var/berth/static
RUN chown appuser:appuser /var/berth/static

# Build development image using the previous stage as base. This is used
# for local development with docker-compose.
FROM appbase as development

# Install additional dependencies.
COPY --chown=appuser:appuser requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir  -r /app/requirements-dev.txt \
  && apt-install.sh postgresql-client

# Set environment variables for development.
ENV DEV_SERVER=1

# Copy the application code.
COPY --chown=appuser:appuser . /app/

# required to make compilemessages command work in OpenShift
RUN chmod -R g+w /app/locale && chgrp -R root /app/locale

# Use a non-root user.
USER appuser

# Expose the port that the application is listening on. `EXPOSE` statement
# is actually a no-op but it works as an extra bit of documentation.
EXPOSE 8000/tcp


# Build production image using the appbase stage as base. This should always
# be the last stage of Dockerfile.
FROM appbase as production

# Copy application code.
COPY --chown=appuser:appuser . /app/

# OpenShift write access to email templates for generated -folder
USER root
RUN chgrp -R 0 /app/templates/email && chmod g+w -R /app/templates/email
RUN chgrp -R 0 /var/berth && chmod g+w -R /var/berth
# /app/data needs write access for Django management commands to work
RUN mkdir -p /app/data
RUN chgrp -R 0 /app/data && chmod g+w -R /app/data
# required to make compilemessages command work in OpenShift
RUN chmod -R g+w /app/locale && chgrp -R root /app/locale

# Set user and document the port.
USER appuser
EXPOSE 8000/tcp
