"""
docker entrypoint (converts envs to arguments)
"""
from env2cli import Argument, flag_argument_func, bulk_apply
from .app import main

argv = bulk_apply([
    Argument('REPOISOTRY_PATH', '--repo-path'),
    Argument('MAX_CONTENT_LENGTH', '--max-content-length'),
    Argument('CLEAN_ON_STRARTUP', '--clean', func=flag_argument_func),
    Argument('PRIV_KEY_PATH', '--priv-key-file'),
    Argument('INDEXER_PORT', '-p'),
    Argument('LOG_LEVEL', '--log-level'),
    Argument('DEFAULT_ARCH', '--default-arch'),
    Argument('REMOTE', '--remote', func=flag_argument_func),
    Argument('REMOTE_REPO_URL', '--remote-repo-url'),
    Argument('REMOTE_USERNAME', '--remote-username'),
    Argument('REMOTE_PASSWORD', '--remote-password')
])

main(argv)
