PACKAGE=$1
INDEXER_URL=$2

apk update
apk add curl
apk fetch -R $PACKAGE
curl -X POST $(for f in *.apk; do echo -F "file=@$f"; done) ${INDEXER_URL}/bulk_upload