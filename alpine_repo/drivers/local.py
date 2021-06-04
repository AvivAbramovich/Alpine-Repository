import logging
from pathlib import Path
from typing import Optional, Dict, List

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

    @property
    def index_file(self) -> Path:
        return self.path / 'APKINDEX.tar.gz'

    def _index_exists(self):
        return self.index_file.is_file()

    def _build_index(self, repo_path, architecture):
        self.logger.info('Build index for "%s" (arch: %s)', repo_path, architecture)
        return self.indexer.build_index(repo_path, architecture)

    def _update_index(self, packages, architecture):
        self.indexer.update_index(self.index_file, *packages, architecture)

    def _sign_index(self):
        self.indexer.sign_index(self.index_file, self.private_key)

    def add_package(self, filename: str, storage: FileStorage, architecture: str):
        return self.add_packages({filename: storage}, architecture)

    def add_packages(self, files: Dict[str, FileStorage], architecture: str):
        packages_paths: List[Path] = []
        repo_path = self.path / architecture
        for filename, file in files.items():
            package_path = repo_path / filename

            file.save(package_path)

            packages_paths.append(package_path)

        try:
            if self._index_exists():
                self._update_index(packages_paths, architecture)
            else:
                self._build_index(repo_path, architecture)

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
        # cleanup all files from repo
        for arch in ARCHITECURES:
            arch_dir = self.path / arch
            if arch_dir.is_dir():
                for f in arch_dir.glob('**/*'):
                    f.unlink()

    def set_logger(self, logger: logging.Logger):
        self.logger = logger
