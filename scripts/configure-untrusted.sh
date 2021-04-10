REPO_URL=$1

mv /etc/apk/repositories /etc/apk/repositories.backup
echo ${REPO_URL} > /etc/apk/repositories
apk update --allow-untrusted