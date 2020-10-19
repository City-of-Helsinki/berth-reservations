# Build a base image for development and production stages.
# Note that this stage won't get thrown out so we need to think about
# layer sizes from this point on.
FROM helsinkitest/python:3.8-slim as appbase

# Copy requirement files.
COPY --chown=appuser:appuser requirements.txt /app/

# Install main project dependencies and clean up.
# Note that production dependencies are installed here as well since
# that is the default state of the image and development stages are
# just extras.
RUN apt-install.sh \
      gdal-bin \
      python-gdal \
      python3-gdal \
      gettext \
      build-essential \
      netcat \
      pkg-config \
    && pip install --no-cache-dir \
      -r /app/requirements.txt \
    && apt-cleanup.sh \
      build-essential \
      pkg-config

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
  && pip install --no-cache-dir prequ

# Set environment variables for development.
ENV DEV_SERVER=1

# Copy the application code.
COPY --chown=appuser:appuser . /app/

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

# Set user and document the port.
USER appuser
EXPOSE 8000/tcp
