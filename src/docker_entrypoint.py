from env2cli import Argument, positional_argument_func, flag_argument_func, bulk_apply
from .app import main

argv = bulk_apply([
    # Argument('UPLOADED_FILES_PATH', func=positional_argument_func, required=True),
    Argument('REPOISOTRY_PATH', func=positional_argument_func),
    Argument('MAX_CONTENT_LENGTH', '--max-content-length'),
    Argument('CLEAN_ON_STRARTUP', '--clean', func=flag_argument_func)
])

main(argv)