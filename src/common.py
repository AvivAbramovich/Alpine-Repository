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

class NamedDisposible:
    def __init__(self, name=None):
        self.name = None

    def __enter__(self):
        return self.name
    def __exit__(self, type, value, traceback):
        pass
