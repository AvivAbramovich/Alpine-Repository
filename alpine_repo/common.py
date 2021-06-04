import logging
from abc import ABCMeta, abstractmethod


ARCHITECURES = [
    'x86',
    'x86_64',
    'aarch64',
    'armhf',
    'armv7',
    'mips64',
    'ppc64le',
    's390x'
]

LOG_LEVELS = ['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']


class ILoggerSettable:
    __metaclass__ = ABCMeta

    @abstractmethod
    def set_logger(self, logger: logging.Logger):
        pass
