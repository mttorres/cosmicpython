FROM python:3.10-slim-buster

# RUN apt install gcc libpq (no longer needed bc we use psycopg2-binary)

# Installing our Python dependencies
# (you may want to split out your dev from prod dependencies; we haven’t here, for simplicity)
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

# Copying and installing our source
RUN mkdir -p /src
COPY src/ /src/
RUN pip install -e /src
COPY tests/ /tests/


# Optionally configuring a default startup command
# (you’ll probably override this a lot from the command line)
WORKDIR /src
ENV PYTHONPATH "${PYTHONPATH}:/${pwd}"
#ENV FLASK_APP=allocation/entrypoints/flask_app.py FLASK_DEBUG=1 PYTHONUNBUFFERED=1
#CMD flask run --host=0.0.0.0 --port=80

# tips on building python containers: https://pythonspeed.com/docker

