NTI App Environments
==============

Getting Started
---------------

- Change directory into your newly created project.

    cd nti.app.environments

- Create a Python virtual environment.

    python3 -m venv env

- Upgrade packaging tools.

    env/bin/pip install --upgrade pip setuptools

- Prerequisites for psycopg2 (MacOS)
    brew install postgresql (including libpq-dev and python-dev, which may be installed in other ways.)
    export DYLD_FALLBACK_LIBRARY_PATH=/Library/PostgreSQL/12/lib:$DYLD_FALLBACK_LIBRARY_PATH
    or install its binary version (https://www.psycopg.org/docs/install.html#binary-install-from-pypi)

- Install the project in editable mode with its testing requirements.

    env/bin/pip install -e ".[testing]"

- Run your project's tests.

    env/bin/pytest

- Run your project.

    env/bin/pserve development.ini
