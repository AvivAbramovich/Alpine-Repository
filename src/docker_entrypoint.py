from env2cli import *
from app import main

argv = bulk_apply([
    Argument('UPLOADED_FILES_PATH', func=positional_argument_func, required=True),
    Argument('MAX_CONTENT_LENGTH', '--max-content-length')
])

main(argv)