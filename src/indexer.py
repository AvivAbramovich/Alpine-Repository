
import logging
import shutil
import tarfile
from os import unlink, listdir, mkdir
from os.path import isdir, isfile, join
from uuid import uuid4
from subprocess import Popen, PIPE
from .common import ARCHITECURES
from io import BytesIO


class Indexer:
    def __init__(self, logger : logging.Logger = None):
        self.logger = logger if logger else logging.getLogger(__package__)

    def _run_command(self, cmdline, timeout=10, logger=None):
        self.logger.debug('run subprocess: "%s"', cmdline)
        p = Popen(cmdline, shell=True, stdout=PIPE, stderr=PIPE)
        status_code = p.wait(timeout=timeout)
        stdout, stderr = p.communicate()
        self.logger.debug('stdout: %s', stdout.decode('utf-8'))
        if status_code != 0:
            raise Exception('Command "%s" failed: %s' % (cmdline, stderr.decode('utf-8')))
    
    @staticmethod
    def extract_index(index_tar_path):
        with tarfile.open(index_tar_path, 'r:gz') as f:
            with f.extractfile(f.getmember('APKINDEX')) as orig_index_f:
                return orig_index_f.read().decode('utf-8')

    def update_index(self, index_path, *new_package_paths, architecture='x86_64'):
        # get original APKINDEX from the .tar.gz
        index = self.extract_index(index_path)

        for package in new_package_paths:
            index_path = index_path = 'APKINDEX-%s.tar.gz' % uuid4()
            try:
                self._run_command('apk index -o {index_path} {package} --rewrite-arch {arch}'.format(
                    index_path=index_path, package=package, arch=architecture))
                # extract index
                package_index = self.extract_index(index_path)

                # TODO: look if already in index

                # Appnd to index
                index += package_index + '\n\n'
            finally:
                # remove tmp index if still exists
                if isfile(index_path):
                    unlink(index_path)

        # tar the index
        unlink(index_path)
        with tarfile.open(index_path, 'w:gz') as f:
            data = index.encode('utf-8')
            io = BytesIO(data)
            info = tarfile.TarInfo(name="APKINDEX")
            info.size=len(data)
            f.addfile(tarinfo=info, fileobj=io)

    def add_directory_to_index(self, directory, architecture='x86_64'):
        packages = [join(directory, name) for name in listdir(directory) if name.endswith('.apk')]
        self.update_index(*packages, architecture=architecture)

    def sign_index(self, index_path, private_key_path):
        if not isfile(private_key_path):
            raise Exception('%s is not a file' % private_key_path)
        self._run_command('abuild-sign -k {priv} {index}'.format(priv=private_key_path, index=index_path))

    def build_index(self, repository_path, rewrite_architecture=None, command_timeout=10):
        '''
        Create/Update APKINDEX.tar.gz for the repository
        :param repository_path: the local path of the repository
        :param rewrite_architecture: use --rewrite-arch option
        :param architecture: architecture to rewrite
        '''
        if rewrite_architecture and rewrite_architecture not in ARCHITECURES:
            raise Exception('Invalid archtecture "%s"' % rewrite_architecture)
        if not isdir(repository_path):
            mkdir(repository_path)
        
        # TODO: create it in some tmp directory
        index_path = 'APKINDEX-%s.tar.gz' % uuid4()

        try:
            self.logger.info('Creating temp index file: %s', index_path)
            cmdline = 'apk index -o {index_path} {repo}/*.apk'
            if rewrite_architecture:
                cmdline += ' --rewrite-arch ' + rewrite_architecture
            self._run_command(cmdline.format(index_path=index_path, repo=repository_path))
                        
            self.logger.info('Replace old index with new one')
            shutil.move(index_path, '{repo}/APKINDEX.tar.gz'.format(repo=repository_path))
        finally:
            # remove tmp index if still exists
            self.logger.info('removing tmp index "%s"', index_path)
            if isfile(index_path):
                unlink(index_path)
