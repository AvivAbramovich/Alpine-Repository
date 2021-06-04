import os.path
from abc import ABCMeta, abstractmethod
from typing import Dict

from werkzeug.datastructures import FileStorage


REGISTERED_DRIVERS = {}


class IDriver:
    __metaclass__ = ABCMeta

    @classmethod
    @abstractmethod
    def name(cls):
        pass

    @abstractmethod
    def add_package(self, filename: str, data: FileStorage, architecture: str):
        pass

    @abstractmethod
    def add_packages(self, files: Dict[str, FileStorage], architecture: str):
        pass

    @abstractmethod
    def rebuild_index(self, architecture):
        pass

    @abstractmethod
    def clean_repository(self):
        pass


def register_driver(driver_cls):
    if not issubclass(driver_cls, IDriver):
        raise Exception(f'Class {driver_cls} does not implementing IDriver interface')
    REGISTERED_DRIVERS[driver_cls.name()] = driver_cls


def import_modules(drivers_dir=None):
    import importlib
    if not drivers_dir:
        drivers_dir = os.path.dirname(__file__)
    # check drivers dir is in sys.path
    for module_name in os.listdir(drivers_dir):
        if module_name.startswith('_'):
            continue
        if '.' in module_name:
            module_name = module_name[:module_name.index('.')]
        importlib.import_module(f'alpine_repo.drivers.{module_name}')
