# Alpine-Repository

Deploy your own Alpine Linux packages repository with uploading server and auto indexing!

[Github](https://github.com/AvivAbramovich/Alpine-Repository)

## Supported tags
* `latest`, `indexer-0.1`, `indexer`
* `httpd-0.1`, `0.1` **Not available yet**

## Image Variants
- `inderxer` - Only the `indexer`, description below in [Indexer](#Indexer)
- `httpd` - Both the indexer and [httpd](https://hub.docker.com/_/httpd) to server the repository


## Indexer
This images contain only the indexer services, which listening on these endpoints:

- `POST /upload` - upload a single alpine package and rebuild index
- `POST /bulk_upload` - upload multiple alpine packages and rebuild index
- `POST /build` - rebuild index
  
**Usage examples:**

Run the indexer:

    docker run -p 80:80 -p /path/to/repo/x86_64:/repo avivabramovich/alpine-repository:indexer

And serve the repository files (in this example, using httpd):

    docker run -p 8080:80 -v /path/to/repo:/usr/local/apache2/htdocs/:ro httpd

Now, upload some packages to your repo

```sh
    apk fetch -R bash
    # fetched 6 packages

    # upload a single package
    curl -X POST -F "file=@bash-5.1.0-r0.apk http://your_repo/upload"

    # use bulk_upload to upload all packages in  directory
    curl -X POST $(for f in *.apk; do echo -F "file=@$f"; done) http://your_repo/bulk_upload
```

Now, configure your alpine machine/container to use your new repository

```sh
    echo http://your_repo > /etc/apk/repositories

    # add --allow-untrusted if you don't use the trusted options in the indexer
    apk update

    # add --allow-untrusted if you don't use the trusted options in the indexer
    apk add bash
```

## Indexer's Configurations

- `REPOISOTRY_PATH` - path inside the container to repository (include the architecture), e.g. `/repo/x86_64`. default: `/repo` in indexer. In the httpd variant, it should be fixed to `/usr/local/apache2/htdocs/${ARCH}`
- `PRIV_KEY_PATH` - path to private key file. Add this option to sign the `APKINDEX.tar.gz` the indexer crates and make the repository trusted.
- `ARCH` - Architecture of the repository. default: `x86_64`
- `CLEAN_ON_STRARTUP` - Set to `TRUE` to remove all files from repository directory when starting the `indexer`. Mainly for debugging.
- `MAX_CONTENT_LENGTH` - the maximum file content size of upcoming requests for the indexer.
- `INDEXER_PORT` - a port which the indexer app listens on. default: 80 in only `indexer` variant, 5000 in `indexer + httpd`

## Docker-Compose examples

### Untrusted variant

```yaml
version: '3.8'
services: 
  indexer:
    image: avivabramovich/alpine-repository:indexer
    ports:
    - '8080:80'
    volumes:
    - '/path/to/repo/x86_64:/repo'
  repo-httpd:
    image: httpd:2.4-alpine
    ports: 
    - '80:80'
    volumes: 
    - '/path/to/repo:/usr/local/apache2/htdocs/:ro'
```

### Trusted

```yaml
version: '3.8'
services: 
  indexer:
    image: avivabramovich/alpine-repository:indexer
    ports:
    - '8080:80'
    volumes:
    - '/path/to/repo/x86_64:/repo'
    - '/path/to/keys@your.email@gmail.com.rsa:/mnt/keys@your.email@gmail.com.rsa'
    environment:
    - PRIV_KEY_PATH=/mnt/keys@your.email@gmail.com.rsa
  repo-httpd:
    image: httpd:2.4-alpine
    ports: 
    - '80:80'
    volumes: 
    - '/path/to/repo:/usr/local/apache2/htdocs/:ro'
```

### Indexer+httpd variant

```yaml
version: '3.8'
services: 
  indexer:
    image: avivabramovich/alpine-repository:httpd
    ports:
    - '80:80'
    - '5000:5000'
    volumes:
    - '/path/to/repo:/repo'
```