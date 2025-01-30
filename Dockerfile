# Build a base image for development and production stages.
# Note that this stage won't get thrown out so we need to think about
# layer sizes from this point on.
FROM public.ecr.aws/docker/library/python:3.11-slim AS appbase

USER root
WORKDIR /app

# Make sure appuser group and user exist
COPY ./setup_user.sh /setup_user.sh
RUN chmod a+x /setup_user.sh && /bin/sh -c /setup_user.sh && rm -f /setup_user.sh

# Copy requirement files.
COPY --chown=appuser:appuser requirements.txt /app/

# Install main project dependencies and clean up.
# Note that production dependencies are installed here as well since
# that is the default state of the image and development stages are
# just extras.
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gdal-bin \
  gettext \
  libpq-dev \
  netcat-traditional \
  pkg-config \
  python3-gdal \
  && pip install -U pip \
  && pip install --no-cache-dir -r /app/requirements.txt \
  && apt-get remove -y build-essential pkg-config \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /var/cache/apt/archives

# Copy and set the entrypoint.
COPY --chown=appuser:appuser docker-entrypoint.sh /app
ENTRYPOINT ["./docker-entrypoint.sh"]

ENV STATIC_ROOT=/var/berth/static
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /var/berth/static && chown appuser:appuser /var/berth/static

# Build development image using the previous stage as base. This is used
# for local development with docker-compose.
FROM appbase AS development

# Install additional dependencies.
COPY --chown=appuser:appuser requirements-dev.txt /app/requirements-dev.txt
RUN pip install --no-cache-dir  -r /app/requirements-dev.txt \
  && apt-get update && apt-get install -y --no-install-recommends postgresql-client \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/* \
  && rm -rf /var/cache/apt/archives

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
FROM appbase AS production

# Copy application code.
COPY --chown=appuser:appuser . /app/

# OpenShift write access to email templates for generated -folder
USER root
RUN chgrp -R 0 /app/templates/email && chmod g+w -R /app/templates/email \
  && chgrp -R 0 /var/berth && chmod g+w -R /var/berth \
  # /app/data needs write access for Django management commands to work
  && mkdir -p /app/data \
  && chgrp -R 0 /app/data && chmod g+w -R /app/data \
  # required to make compilemessages command work in OpenShift
  && chmod -R g+w /app/locale && chgrp -R root /app/locale

# Set user and document the port.
USER appuser
EXPOSE 8000/tcp
