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

class NullFileDisposible:
    def __enter__(self):
        return self
    def __exit__(self, type, value, traceback):
        pass
    @property
    def name(self):
        return None