# Berth reservations

![Continuous integration](https://github.com/City-of-Helsinki/berth-reservations/workflows/Continuous%20integration/badge.svg)

:boat: Bare-bones registration API for berth reservations :boat:

**Contents**
* [Development with Docker](#development-with-docker)
* [Development without Docker](#development-without-docker)
  * [Database](#database)
  * [Daily running](#daily-running)
  * [Install geospatial libraries](#install-geospatial-libraries)
* [Keeping Python requirements up to date](#keeping-python-requirements-up-to-date)
* [Code format](#code-format)
* [Version Control](#version-control)
  * [Commits and pull requests](#commits-and-pull-requests)
  * [Releases](#releases)
* [Running tests](#running-tests)
* [Helsinki Harbors' data](#helsinki-harbors-data)


<a name="development-with-docker"></a>
## Development with Docker

1. Create `.env` docker-compose environment file with default contents:

```
DEBUG=1
APPLY_MIGRATIONS=1
ALLOWED_HOSTS=*
CORS_ORIGIN_ALLOW_ALL=1
NOTIFICATIONS_ENABLED=1

VENE_PAYMENTS_BAMBORA_API_URL=https://fake-bambora-api-url/api
VENE_PAYMENTS_BAMBORA_API_KEY=dummy-key
VENE_PAYMENTS_BAMBORA_API_SECRET=dummy-secret
VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS="dummy-bank"

PROFILE_API_URL=https://profiili-api.test.kuva.hel.ninja/graphql/
PROFILE_TOKEN_SERVICE=https://api.hel.fi/auth/helsinkiprofile
```

2. Run `docker-compose up`

3. Run migrations if needed: 
    * `docker exec berth python manage.py migrate`

4. Create superuser if needed: 
    * `docker exec -it berth python manage.py createsuperuser`

The project is now running at [localhost:8000](http://localhost:8000)

<a name="development-without-docker"></a>
## Development without Docker

Project uses following software versions:

* Postgres 11
* Postgis 2.5
* Python 3.8

<a name="database"></a>
### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S berth_reservations  # use password `berth_reservations`
    sudo -u postgres createdb -O berth_reservations berth_reservations
    
Create extensions in the database
    
    sudo -u postgres psql berth_reservations -c "CREATE EXTENSION postgis;"

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER berth_reservations CREATEDB;"

<a name="install-geospatial-libraries"></a>
### Install Geospatial libraries

For Debian/Ubuntu:

    apt-get install binutils libproj-dev gdal-bin

For more information, see
https://docs.djangoproject.com/en/3.1/ref/contrib/gis/install/geolibs/

<a name="daily-running"></a>
### Daily running

* Create `.env` file: `touch .env`
* Set the `DEBUG` environment variable to `1`.
* Run `python manage.py migrate`
* Run `python manage.py runserver 0:8000`

The project is now running at [localhost:8000](http://localhost:8000)

<a name="keeping-python-requirements-up-to-date"></a>
## Keeping Python requirements up to date

1. Install `pip-tools`:
    
    * `pip install pip-tools`

2. Add new packages to `requirements.in` or `requirements-dev.in`

3. Update `.txt` file for the changed requirements file:
 
    * `pip-compile requirements.in`
    * `pip-compile requirements-dev.in`

4. If you want to update dependencies to their newest versions, run:

    * `pip-compile --upgrade requirements.in`

5. To install Python requirements run:

    * `pip-sync requirements.txt`

<a name="code-format"></a>
## Code format

This project uses [`black`](https://github.com/ambv/black) for Python code formatting.
We follow the basic config, without any modifications. Basic `black` commands:

* To let `black` do its magic: `black .`
* To see which files `black` would change: `black --check .`

The project also has [`pre-commit`](https://pre-commit.com/) setup with few hooks to avoid having "style fixing" commits.

To install it, run:

    pre-commit install

This will setup three pre-commit hooks: `black`, `flake8`, and `isort`.

<a name="version-control"></a>
## Version control
<a name="commits-and-pull-requests"></a>
### Commits and pull requests
We try to keep a clean git commit history. For that:
* Keep your commits as simple as possible
* Always rebase your PRs, **don't merge** the latest `master` into your branch
* Don't be afraid to `push --force` once you have fixed your commits 
* Avoid using the GitHub merge/rebase buttons

<a name="releases"></a>
### Releases

This project is following [GitHub flow](https://guides.github.com/pdfs/githubflow-online.pdf).
Release notes can be found from [GitHub tags/releases](https://github.com/City-of-Helsinki/berth-reservations/releases).

<a name="running-tests"></a>
## Running tests

    pytest

In order to successfully run tests in ```applications/tests/test_applications_notifications.py``` you need to set env variable ```NOTIFICATIONS_ENABLED=1```

<a name="helsinki-harbors-data"></a>
## Helsinki Harbors' data

There are some fixtures available, that contain basic data about public
harbors and winter areas of the City of Helsinki. If you don't have divisions of Helsinki 
imported yet through [`django-munigeo`](https://github.com/City-of-Helsinki/django-munigeo),
import them first:

    ./manage.py geo_import finland --municipalities
    ./manage.py geo_import helsinki --divisions

Then load the fixtures with the following commands:

    ./manage.py loaddata helsinki-harbors.json
    ./manage.py loaddata helsinki-ws-resources.json
    ./manage.py loaddata helsinki-winter-areas.json
    ./manage.py loaddata helsinki-harbor-resources.json

And assign the corresponding region to areas:

    ./manage.py assign_area_regions

Create WS sticker sequences:

    ./manage.py create_ws_lease_sticker_sequences
    
Point harbor and ws images to customer ui images:

    ./manage.py harbors_add_helsinki_harbors_images
    ./manage.py harbors_add_helsinki_winter_areas_images
    ./manage.py add_helsinki_harbors_images
    ./manage.py add_helsinki_winter_areas_images
    
Load the fixtures with reasons for berth switch:

    ./manage.py loaddata switch-reasons.json

Lastly, load the User Groups:

    ./manage.py loaddata groups.json

And install the model permissions:

    ./manage.py set_group_model_permissions
