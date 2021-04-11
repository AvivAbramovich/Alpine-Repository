from os import unlink, listdir
from os.path import isdir, isfile, join
from uuid import uuid4
from subprocess import Popen, PIPE
from .common import ARCHITECURES
import logging
import shutil
import tarfile
from io import BytesIO


__all__ = ['index_repository']

_logger = None

def _get_logger(logger=None):
    if not logger:
        if _logger:
            return _logger
        else:
            return logging.getLogger(__package__)
    return logger

def _run_command(cmdline, timeout=10, logger=None):
    logger = _get_logger(logger)
    logger.debug('run subprocess: "%s"', cmdline)
    p = Popen(cmdline, shell=True, stdout=PIPE, stderr=PIPE)
    status_code = p.wait(timeout=timeout)
    stdout, stderr = p.communicate()
    logger.debug('stdout: %s', stdout.decode('utf-8'))
    if status_code != 0:
        raise Exception('Command "%s" failed: %s' % (cmdline, stderr.decode('utf-8')))


def extract_index(index_tar_path):
    with tarfile.open(index_tar_path, 'r:gz') as f:
        with f.extractfile(f.getmember('APKINDEX')) as orig_index_f:
            return orig_index_f.read().decode('utf-8')

def update_index(orig_index_path, *new_package_paths, architecture='x86_64'):
    # get original APKINDEX from the .tar.gz
    index = extract_index(orig_index_path)
    for package in new_package_paths:
        index_path = index_path = 'APKINDEX-%s.tar.gz' % uuid4()
        try:
            _run_command('apk index -o {index_path} {package} --rewrite-arch {arch}'.format(
                index_path=index_path, package=package, arch=architecture))
            # extract index
            package_index = extract_index(index_path)

            # TODO: look if already in index

            # Appnd to index
            index += package_index + '\n\n'
        finally:
            # remove tmp index if still exists
            if isfile(index_path):
                unlink(index_path)


    # tar the index
    unlink(orig_index_path)
    with tarfile.open(orig_index_path, 'w:gz') as f:
        data = index.encode('utf-8')
        io = BytesIO(data)
        info = tarfile.TarInfo(name="APKINDEX")
        info.size=len(data)
        f.addfile(tarinfo=info, fileobj=io)

def add_directory_to_index(orig_index_path, directory, architecture='x86_64'):
    packages = [join(directory, name) for name in listdir(directory) if name.endswith('.apk')]
    update_index(orig_index_path, *packages, architecture=architecture)

def sign_index(index_path, private_key_path):
    _run_command('abuild-sign -k {priv} {index}'.format(priv=private_key_path, index=index_path))

def build_index(repository_path, architecture, private_key_file_path=None, command_timeout=10, logger=None):
    '''
    Create/Update APKINDEX.tar.gz for the repository
    :param repository_path: the local path of the repository
    :param architecture: architecture to rewrite
    :param private_key_file_path:
    '''
    logger = _get_logger(logger)
    global _logger
    _logger = logger

    if not isdir(repository_path):
        raise Exception('%s is not a dir' % repository_path)
    if private_key_file_path and not isfile(private_key_file_path):
        raise Exception('%s is not a file' % private_key_file_path)
    if architecture not in ARCHITECURES:
        raise Exception('Invalid archtecture "%s"' % architecture)
    
    # TODO: create it in some tmp directory
    index_path = 'APKINDEX-%s.tar.gz' % uuid4()

    try:
        logger.info('Creating temp index file: %s', index_path)
        _run_command('apk index -o {index_path} {repo}/*.apk --rewrite-arch {arch}'.format(
            index_path=index_path, repo=repository_path, arch=architecture))
        
        if private_key_file_path:
            logger.info('Signing index %s with %s', index_path, private_key_file_path)
            sign_index(index_path, private_key_file_path)
        
        logger.info('Replace old index with new one')
        shutil.move(index_path, '{repo}/APKINDEX.tar.gz'.format(repo=repository_path))
    finally:
        # remove tmp index if still exists
        logger.info('removing tmp index "%s"', index_path)
        if isfile(index_path):
            unlink(index_path)

