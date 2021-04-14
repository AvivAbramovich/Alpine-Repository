from abc import ABCMeta, abstractmethod


ARCHITECURES = [
    'x86',
    'x86_64',
    'aarch64'
    'armhf'
    'armv7'
    'mips64',
    'ppc64le',
    's390x'
]

LOG_LEVELS = ['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']

class NamedDisposible:
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        return self.name
    def __exit__(self, _, __, ___):
        pass
