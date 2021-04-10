Alpine-Repository
=================

Deploy your own Alpine Linux packages repository with uploading server and auto indexing! 

Supported tags
--------------
* latest, 0.1
* indexer-0.1, indexer


Indexer tags
------------
This images contain only the indexer services, which listening on these endpoints:

- `POST /upload` - upload a single alpine package and rebuild index
- `POST /bulk_upload` - upload multiple alpine packages and rebuild index
- `POST /build` - rebuild index
  
**Usage examples:**

Run the indexer:

.. code-block:: sh

    docker run -p 80:80 -p /path/to/repo/x86_64:/repo avivabramovich/alpine-repository:indexer

And serve the repository files (in this example, using httpd):

.. code-block:: sh

    docker run -p 8080:80 -v /path/to/repo:/usr/local/apache2/htdocs/:ro httpd

Now, upload some packages to your repo

.. code-block:: sh

    apk fetch -R bash
    # fetched 6 packages

    # upload a single package
    curl -X POST -F "file=@bash-5.1.0-r0.apk http://your_repo/upload

    # use bulk_upload to upload all packages in  directory
    curl -X POST $(for f in *.apk; do echo -F "file=@$f"; done) http://your_repo/bulk_upload

Now, configure your alpine machine/container to use your new repository

TODO!