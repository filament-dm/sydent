# This Dockerfile installs Sydent from source, which is assumed to be in the current
# working directory. The resulting image contains a single "sydent" user, and populates
# their home area with "src" and "venv" directories. The entrypoint runs Sydent,
# listening on port 8090.
#
# Users must provide a persistent volume available to the container as `/data`. This
# will contain Sydent's configuration and database. A blank configuration and database
# file is created the first time Sydent runs.

# Step 1: install dependencies
FROM docker.io/python:3.8-slim-bookworm as builder

# Add user sydent
RUN addgroup --system --gid 993 sydent \
    && useradd -m --system --uid 993 -g sydent sydent
USER sydent:sydent

# Install poetry
RUN pip install --user poetry==1.2.2

# Copy source code and resources
WORKDIR /home/sydent/src
COPY --chown=sydent:sydent ["res", "res"]
COPY --chown=sydent:sydent ["scripts", "scripts"]
COPY --chown=sydent:sydent ["sydent", "sydent"]
COPY --chown=sydent:sydent ["README.rst", "pyproject.toml", "poetry.lock", "./"]

# Install dependencies
RUN python -m poetry install -vv --no-dev --no-interaction --extras "prometheus sentry"

# Record dependencies for posterity
RUN python -m poetry export -o requirements.txt

# Make the virtualenv accessible for the final image
RUN ln -s $(python -m poetry env info -p) /home/sydent/venv

# Nuke bytecode files to keep the final image slim.
RUN find /home/sydent/venv -type f -name '*.pyc' -delete

# Step 2: Create runtime image
FROM docker.io/python:3.8-slim-bookworm

# Add user sydent and create /data directory
RUN addgroup --system --gid 993 sydent \
    && useradd -m --system --uid 993 -g sydent sydent \
    && mkdir /data \
    && chown sydent:sydent /data

RUN pip install -U litecli
RUN apt-get update
RUN apt-get install -y sqlite3

# Copy sydent and the virtualenv
COPY --from=builder ["/home/sydent/src", "/home/sydent/src"]
COPY --from=builder ["/home/sydent/venv", "/home/sydent/venv"]

ENV SYDENT_CONF=/data/sydent.conf
ENV SYDENT_PID_FILE=/data/sydent.pid
ENV SYDENT_DB_PATH=/data/sydent.db

WORKDIR /home/sydent
USER sydent:sydent
VOLUME ["/data"]
EXPOSE 8090/tcp
CMD [ "venv/bin/python", "-m", "sydent.sydent" ]
