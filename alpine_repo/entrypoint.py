from env2cli import Argument, positional_argument_func, flag_argument_func, bulk_apply
from .app import main


def split_by_semicolon(key, val):
    res = []
    if val:
        for v in val.split(';'):
            res.extend([key, v])
    return res


argv = bulk_apply([
    Argument('ALPINE_REPO_DEFAULT_ARCH', '--default-arch'),
    Argument('ALPINE_REPO_DRIVER', func=positional_argument_func),
    Argument('ALPINE_REPO_DRIVER_OPTIONS', '--driver-opt', func=split_by_semicolon),
    Argument('ALPINE_REPO_MAX_CONTENT_LENGTH', '--max-content-length'),
    Argument('ALPINE_REPO_CLEAN_ON_STARTUP', '--clean', func=flag_argument_func),
    Argument('ALPINE_REPO_INDEXER_PORT', '-p'),
    Argument('LOG_LEVEL', '--log-level'),
])

main(argv)
