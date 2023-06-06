# Env Vars, 12-Factor, and Config, Inside and Outside Containers
'''
The basic problem we’re trying to solve here is that we need
different config settings for the following:

    Running code or tests directly from your own dev machine,
    perhaps talking to mapped ports from Docker containers

    Running on the containers themselves, with "real" ports and hostnames

    Different container environments (dev, staging, prod, and so on)

Configuration through environment variables as suggested by the 12-factor manifesto
will solve this problem, but concretely, how do we implement it in our code and our containers?

1) Config.py

    Whenever our application code needs access to some config,
    it’s going to get it from a file called config.py.

    We use functions for getting the current config,
    rather than constants available at import time,
    because that allows client code to modify os.environ if it needs to.

    config.py also defines some default settings,
    designed to work when running the code from the developer’s local machine.

    An elegant Python package called environ-config is worth looking at if
    you get tired of hand-rolling your own environment-based config functions.

    Don’t let this config module become a dumping ground that is full
    of things only vaguely related to config and that is then imported all over the place.
    Keep things immutable and modify them only via environment variables.
    If you decide to use a bootstrap script (check chapter 13 of cosmic python book),
    you can make it the only place (other than tests) that config is imported to.

'''

import os


def get_postgres_uri():
    host = os.environ.get("DB_HOST", "localhost")
    port = 54321 if host == "localhost" else 5432
    password = os.environ.get("DB_PASSWORD", "abc123")
    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url():
    host = os.environ.get("API_HOST", "localhost")
    port = 5005 if host == "localhost" else 80
    return f"http://{host}:{port}"


def get_redis_host_and_port():
    host = os.environ.get("REDIS_HOST", "localhost")
    port = 63791 if host == "localhost" else 6379
    return dict(host=host, port=port)


def get_email_host_and_port():
    host = os.environ.get("EMAIL_HOST", "localhost")
    port = 11025 if host == "localhost" else 1025
    http_port = 18025 if host == "localhost" else 8025
    return dict(host=host, port=port, http_port=http_port)
