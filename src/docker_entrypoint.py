from env2cli import Argument, positional_argument_func, flag_argument_func, bulk_apply
from .app import main

argv = bulk_apply([
    Argument('REPOISOTRY_PATH', '--repo-path'),
    Argument('MAX_CONTENT_LENGTH', '--max-content-length'),
    Argument('CLEAN_ON_STRARTUP', '--clean', func=flag_argument_func),
    Argument('PRIV_KEY_PATH', '--priv-key-file'),
    Argument('INDEXER_PORT', '-p'),
    Argument('LOG_LEVEL', '--log-level'),
    Argument('DEFAULT_ARCH', '--default-arch'),
    Argument('PROXY', '--proxy', func=flag_argument_func),
    Argument('PROXY_REPO_URL', '--proxy-repo-url'),
    Argument('PROXY_CREDENTIALS', '--proxy-credentials')
])

main(argv)