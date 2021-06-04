import logging
from pathlib import Path
from typing import Dict, List

from alpine_repo.drivers import IDriver, register_driver
from alpine_repo.common import ARCHITECURES, ILoggerSettable
from alpine_repo.indexer import Indexer

from werkzeug.datastructures import FileStorage


@register_driver
class LocalDriver(IDriver, ILoggerSettable):
    _DRIVER_NAME = 'local'

    indexer = Indexer()

    def __init__(self, path, private_key=None):
        self.logger = logging.getLogger('LocalDriver')
        path = Path(path)
        if not path.is_dir():
            raise NotADirectoryError(path)
        self.path = path

        if private_key:
            private_key = Path(private_key)
            if not private_key.is_file():
                raise FileNotFoundError(self.private_key)
        self.private_key = private_key

    @classmethod
    def name(cls):
        return cls._DRIVER_NAME

    def index_file(self, architecture) -> Path:
        return self.path / architecture / 'APKINDEX.tar.gz'

    def _index_exists(self, architecture):
        return self.index_file(architecture).is_file()

    def _build_index(self, architecture):
        self.logger.info('Build index for "%s"', architecture)
        return self.indexer.build_index(self.path / architecture, architecture)

    def _update_index(self, packages, architecture):
        self.logger.info('Updating index for repository "%s" with new %d packages', architecture, len(packages))
        self.indexer.update_index(self.index_file(architecture), *packages, architecture)

    def _sign_index(self):
        self.indexer.sign_index(self.index_file, self.private_key)

    def add_package(self, filename: str, storage: FileStorage, architecture: str):
        return self.add_packages({filename: storage}, architecture)

    def add_packages(self, files: Dict[str, FileStorage], architecture: str):
        packages_paths: List[Path] = []
        repo_path = self.path / architecture
        for filename, file in files.items():
            package_path = repo_path / filename

            self.logger.info('Add package "%s" to "%s" repository', filename, architecture)
            file.save(package_path)

            packages_paths.append(package_path)

        try:
            if self._index_exists(architecture):
                self._update_index(packages_paths, architecture)
            else:
                self._build_index(architecture)

            if self.private_key:
                self._sign_index()
        except:
            # rollback
            for package_path in packages_paths:
                if package_path.is_file():
                    package_path.unlink()
            raise

    def rebuild_index(self, architecture=None):
        return self._build_index(architecture)

    def clean_repository(self):
        self.logger.info('Cleaning up repositories')
        # cleanup all files from repo
        for arch in ARCHITECURES:
            arch_dir = self.path / arch
            if arch_dir.is_dir():
                self.logger.info('Cleaning up repository "%s"', arch)
                for f in arch_dir.glob('**/*'):
                    self.logger.info('Unlink "%s"', f)
                    f.unlink()

    def set_logger(self, logger: logging.Logger):
        self.logger = logger
