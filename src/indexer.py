from os import unlink
from os.path import isdir, isfile
from uuid import uuid4
from subprocess import Popen, PIPE
from .common import ARCHITECURES
import logging
import shutil


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


def index_repository(repository_path, architecture, private_key_file_path=None, command_timeout=10, logger=None):
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

            _run_command('abuild-sign -k {priv} {index}'.format(priv=private_key_file_path, index=index_path))
        
        logger.info('Replace old index with new one')
        shutil.move(index_path, '{repo}/APKINDEX.tar.gz'.format(repo=repository_path))
    finally:
        # remove tmp index if still exists
        logger.info('removing tmp index "%s"', index_path)
        if isfile(index_path):
            unlink(index_path)

