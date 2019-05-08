# Berth reservations

:boat: Bare-bones registration API for berth reservations :boat:

## Development with Docker

1. Create `.env` environment file

2. Set the `DEBUG` environment variable to `1`

3. Run `docker-compose up`

4. Run migrations if needed: 
    * `docker exec berth python manage.py migrate`

5. Create superuser if needed: 
    * `docker exec -it berth python manage.py createsuperuser`

The project is now running at [localhost:8000](http://localhost:8000)

## Development without Docker

Project uses following software verisons:

* Postgres 9.6
* Postgis 2.4
* Python 3.6

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


## Helsinki Harbors' data

There are some fixtures available, that contain basic data about public
harbors and winter areas of the City of Helsinki. If you don't have divisions of Helsinki 
imported yet through [`django-munigeo`](https://github.com/City-of-Helsinki/django-munigeo),
import them first:

    ./manage.py geo_import finland --municipalities
    ./manage.py geo_import helsinki --divisions

Then you can load the fixtures with the following commands:

    ./manage.py loaddata helsinki-harbors.json
    ./manage.py loaddata helsinki-winter-areas.json
    
You can also import default images for Helsinki harbors / winter storage areas:

    ./manage.py collectstatic  # make sure you have static files in place
    ./manage.py add_helsinki_harbors_images
    ./manage.py add_helsinki_winter_areas_images
