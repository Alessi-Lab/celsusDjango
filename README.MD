# Celsus-Django
Back-end architecture for Celsus and Curtain web applications.

## Installation instructions
The first step for installation is downloading the content of the following github repoes
1. https://github.com/noatgnu/netphos-web (wrapper for web usage of NetPhos 3.1)
2. https://github.com/noatgnu/celsusdjango (this repository)
3. https://github.com/noatgnu/curtain (curtain frontend)
4. https://github.com/noatgnu/curtainptm (curtainptm frontend)

Then, download NetPhos 3.1 linux version from this link https://services.healthtech.dtu.dk/service.php?NetPhos-3.1 and copy it into the location where the netphos-web repo had been downloaded.

The simplest method for installation of Celsus-Django is through `docker-compose`. In order to use docker please ensure that you have docker and docker-compose installed.

Copy and paste the content of the following `docker-compose.yml` file into the location where you want to store the backend application.

```yaml
version: "3.8"
services:
  db:
    image: postgres 
    volumes:
      - ./data/db:/var/lib/postgresql/data 
    environment:
      - POSTGRES_DB=postgres # This is the name of the postgres database
      - POSTGRES_USER=postgres # This is the username for the postgres database
      - POSTGRES_PASSWORD=postgres # This is the password for the postgres database user
    container_name: db
    networks:
      - celsus-net # This is the name of the network that will be used by the docker containers
  web:
    container_name: web
    build:
      context: .
      dockerfile: ./docker/Dockerfile 
    command: gunicorn celsusdjango.wsgi:application --bind 0.0.0.0:8000 
    ports:
      - "8000:8000"
    environment:
      - WORKDB_PROFILE=production
      - SECRET_KEY= # This is a secret key for django
      - POSTGRES_DB=postgres # This is the name of the postgres database
      - POSTGRES_USER=postgres # This is the username for the postgres database
      - POSTGRES_PASSWORD=postgres # This is the password for the postgres datqabase user
      - POSTGRES_HOST=db # This is the hostname of the postgres database host
      - DJANGO_CORS_WHITELIST= # This is a list of frontend url that are allowed to access our backend delimited by commas
      - DJANGO_ALLOWED_HOSTS= # This is a list of hostname that can be used to access our backend
      - DJANGO_MEDIA_ROOT=/app/media/ # This is the location of the media folder
      - ORCID_OAUTH_CLIENT_ID= # This is the clientid registered from orcid.org
      - ORCID_OAUTH_SECRET= # This is the secret registered from orcid.org
      - CURTAIN_ALLOW_NON_STAFF_DELETE=0 # This is to whether or not allow non_staff Curtain user to delete a Curtain entry.
      - CURTAIN_ALLOW_NON_USER_POST=1 # This is to whether or not allow not yet authenticated user to save a new Curtain session.
      - CURTAIN_DEFAULT_USER_CAN_POST=1 # This is to whether or not allow user to be able to save session by default
      - CURTAIN_DEFAULT_USER_LINK_LIMIT=0 # This is to limit the number of session one user can own or 0 to set it to be infinite
    depends_on:
      - db # This is to ensure that the database is up and running before the web application is started
    volumes:
      - ./data/media:/app/media # This is the location of the media folder
    networks:
      - celsus-net # This is to ensure that the web application can access the database
  netphos:
    build:
      context: /usr/path/to/netphos/web/git/clone
      dockerfile: /usr/path/to/netphos/web/git/clone/Dockerfile
    container_name: netphos
    networks:
      - celsus-net
    volumes:
      - ./data/netphos:/app/netphos-archive
  # uncomment below to enable frontend within this docker-compose 
#  curtain: # curtain frontend
#    build:
#      context: /usr/path/to/curtain/git/clone
#      dockerfile: /usr/path/to/curtain/git/clone/Dockerfile
#      args:
#        API_HOST: https://celsus.muttsu.xyz/
#        ORCID_APPID: APP-5RXLC3W1MS2MOW0F
#    container_name: curtain
#    ports:
#      - "8002:80"
#  curtainptm: # curtainptm frontend
#    build:
#      context: /usr/path/to/curtainPTM/git/clone
#      dockerfile: /usr/path/to/curtainPTM/git/clone/Dockerfile
#      args:
#        API_HOST: https://celsus.muttsu.xyz/
#        ORCID_APPID: APP-5RXLC3W1MS2MOW0F
#    container_name: curtainptm
#    ports:
#      - "8001:80"
networks:
  celsus-net:
```

Replace environmental variables in the docker-compose file content with the appropriate value for applications where
1. `SECRET_KEY` is your DJANGO secret key.
2. `DJANGO_CORS_WHITELIST` is a list of frontend url that are allowed to access our backend delimited by commas
3. `DJANGO_ALLOWED_HOSTS` is a list of hostname that can be used to access our backend
4. `ORCID_OAUTH_CLIENT_ID` is your application clientid registered from orcid.org
5. `ORCID_OAUTH_SECRET` is your application secret registered from orcid.org
6. `CURTAIN_ALLOW_NON_STAFF_DELETE` value `1` or `0` is to whether or not allow non_staff Curtain user to delete a Curtain entry.
7. `CURTAIN_ALLOW_NON_USER_POST` value `1` or `0` is to whether or not allow not yet authenticated user to save a new Curtain session.
8. `CURTAIN_DEFAULT_USER_CAN_POST` value `1` or `0` is to whether or not allow user to be able to save session by default
9. `CURTAIN_DEFAULT_USER_LINK_LIMIT` value `1` or higher to limit the number of session one user can own or `0` to set it to be infinite
10. `context` is the folder path of each of the repository that you have downloaded from above
11. `dockerfile` is the location of the file `Dockerfile` within each of the `context` above
12. `API_HOST` is the url for the backend
13. `ORCID_APPID` is the `ORCID_OAUTH_CLIENT_ID` but used in the frontend instead

From the location of the `docker-compose.yml` file, execute

```shell
docker-compose up -d
```

Then execute the following command to perform initial database tables creation in django

```shell
docker-compose exec -it web python manage.py migrate
```
Copy the `netphos-3.1.Linux.tar.Z` file downloaded earlier into the `./data/netphos` folder then run the following to install netphos.

```shell
docker-compose exec -it netphos uncompress /app/netphos-archive/netphos-3.1.Linux.tar.Z
docker-compose exec -it netphos tar -xvf /app/netphos-archive/netphos-3.1.Linux.tar && yes
docker-compose exec -it netphos cp -rf /app/ape.docker /app/ape-1.0/ape
```

The following commands to download the initial fixtures for disease and taxonomy data and add them into our data table. These are optional and only if you are running Celsus data management application.

```shell
docker-compose exec -it web curl -o /app/celsus/fixtures/diseases.json https://nextcloud1.muttsu.xyz/s/dBnT8tGxjneB4AR/download/diseases.json
docker-compose exec -it web curl -o /app/celsus/fixtures/organisms.json https://nextcloud1.muttsu.xyz/s/saKLFYRj4RqXaDa/download/organisms.json
docker-compose exec -it web curl -o /app/celsus/fixtures/kinase_library.json https://nextcloud1.muttsu.xyz/s/eL6Y3tQWJcArEzR/download/kinase_library.json
docker-compose exec -it web python manage.py loaddata diseases.json
docker-compose exec -it web python manage.py loaddata organisms.json
docker-compose exec -it web python manage.py loaddata kinase_library.json
```

Then create your admin account

```shell
docker-compose exec -it web python manage.py createsuperuser
```

Then, visit `https://orcid.org/developer-tools` with your login information and enable public api and enter the uri of the frontend you want to access the data.