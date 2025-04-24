- first of all, get the dump from railway. Use the following command to do so:
```bash
pg_dump <db-url> tawjeeh_db_dump.sql.tar -F t
```
  - repolace the db url with your db url that you can get from the `conect` settings.
  - make sure not to use a network with restrictions (KFUPM network is restricted).

- untar the file:
```bash
tar -xf tawjeeh_db_dump.sql.tar -C db_dump_extracted 
```

- run the postgres docker container:
```bash
# make sure nothing is listening on port 5432\
docker run --name tawjeeh-postgres \
 -e POSTGRES_PASSWORD=<put-your-pass-here> \
 -e PGDATA=/var/lib/postgresql/data/pgdata \
 -v /home/magedsaeed/Projects/tawjeeh/data/postgres:/var/lib/postgresql/data \
 -p 5432:5432 \
 -d postgres
```

- railway creates a special database called `railway`. create your own here on your container:
```bash
docker exec -it tawjeeh-postgres psql -U postgres -c "CREATE DATABASE railway;"
```

- copy the extracted files to the container:
```bash
docker cp db_dump_extracted/ tawjeeh-postgres:/tmp/
```

- use `pg_restore`:
```bash
docker exec -it tawjeeh-postgres bash -c "cd /tmp/db_dump_extracted && pg_restore -U postgres -d railway ."
```
