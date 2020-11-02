# Berth reservations

:boat: Bare-bones registration API for berth reservations :boat:

## Development with Docker

1. Create `.env` docker-compose environment file with default contents:

```
DEBUG=1
APPLY_MIGRATIONS=1    
ALLOWED_HOSTS=*
CORS_ORIGIN_ALLOW_ALL=1
VENE_PAYMENTS_BAMBORA_API_URL=https://fake-bambora-api-url/api
VENE_PAYMENTS_BAMBORA_API_KEY=dummy-key
VENE_PAYMENTS_BAMBORA_API_SECRET=dummy-secret
VENE_PAYMENTS_BAMBORA_PAYMENT_METHODS="dummy-bank"
```

2. Run `docker-compose up`

3. Run migrations if needed: 
    * `docker exec berth python manage.py migrate`

4. Create superuser if needed: 
    * `docker exec -it berth python manage.py createsuperuser`

The project is now running at [localhost:8000](http://localhost:8000)

## Development without Docker

Project uses following software verisons:

* Postgres 9.6
* Postgis 2.4
* Python 3.8

### Database

To setup a database compatible with default database settings:

Create user and database

    sudo -u postgres createuser -P -R -S berth_reservations  # use password `berth_reservations`
    sudo -u postgres createdb -O berth_reservations berth_reservations
    
Create extensions in the database
    
    sudo -u postgres psql berth_reservations -c "CREATE EXTENSION postgis;"

Allow user to create test database

    sudo -u postgres psql -c "ALTER USER berth_reservations CREATEDB;"

### Daily running

* Create `.env` file: `touch .env`
* Set the `DEBUG` environment variable to `1`.
* Run `python manage.py migrate`
* Run `python manage.py runserver 0:8000`

The project is now running at [localhost:8000](http://localhost:8000)

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

## Code format

This project uses [`black`](https://github.com/ambv/black) for Python code formatting.
We follow the basic config, without any modifications. Basic `black` commands:

* To let `black` do its magic: `black .`
* To see which files `black` would change: `black --check .`

## Releases

This project is following [GitHub flow](https://guides.github.com/pdfs/githubflow-online.pdf).
Release notes can be found from [GitHub tags/releases](https://github.com/City-of-Helsinki/berth-reservations/releases).

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

## Running tests

    pytest
    
In order to successfully run tests in ```applications/tests/test_applications_notifications.py``` you need to set env variable ```NOTIFICATIONS_ENABLED=1```
