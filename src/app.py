'''
Main module, running indexer app
'''
from os.path import join, isfile
import os
import tempfile
import logging
import uuid
import argparse
import requests
from flask import Flask, flash, request, redirect, make_response
from flask.logging import create_logger
from werkzeug.utils import secure_filename

from . import common
from .indexer import Indexer

ALLOWED_EXTENSIONS = {'apk'}

class IndexerFlaskApp(Flask):
    '''
    Wrapper to Flask app with logger, indexer and secret key
    '''
    def __init__(self, name, secret_key):
        super().__init__(name)
        self.logger : logging.Logger = create_logger(self)
        self.indexer : Indexer = Indexer(self.logger)
        self.secret_key = secret_key

app = IndexerFlaskApp(__name__, str(uuid.uuid4()))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _get_private_key_handle(key_file_path, key_value):
    if key_value:
        handler = tempfile.NamedTemporaryFile(suffix='.rsa')
        handler.write(key_value)
        return handler
    return common.NamedDisposible(key_file_path)

def build_index(dir_path, arch):
    app.indexer.build_index(dir_path, rewrite_architecture=arch)

def rebuild_index(architecture=None):
    if not architecture:
        architecture = app.config['default_arch']
    if app.config['remote']:
        raise Exception('Cant rebuild index in remote mode')
    app.indexer.build_index(join(app.config['repo_path'], architecture), 
        rewrite_architecture=architecture, command_timeout=app.config['command_timeout'])

def check_arch_dir(architecture):
    arch_dir = os.path.join(app.config['repo_path'], architecture)
    if not os.path.isdir(arch_dir):
        os.mkdir(arch_dir)

def get_credentials():
    if app.config['remote_username'] and app.config['remote_password']:
        return (app.config['remote_username'], app.config['remote_password'])

def get_directory_handle(rel_path):
    if app.config['remote']:
        t = tempfile.TemporaryDirectory()
        try:
            # try fetch index
            index_path = join(rel_path, 'APKINDEX.tar.gz')
            fetch_file_from_remote(index_path, join(t.name, index_path))
        except FileNotFoundError:
            pass
        return t
    return common.NamedDisposible(join(app.config['repo_path'], rel_path))

def update_index(index_path, arch, *packages):
    app.indexer.update_index(index_path, *packages, architecture=arch)

def get_arch():
    arch = request.args.get('arch', app.config['default_arch'])
    if arch not in common.ARCHITECURES:
        return None, make_response('Invalid architecture! Options: %s. Default: %s'
            % (common.ARCHITECURES, app.config['default_arch']),400)
    return arch, None  

def fetch_file_from_remote(file_path, dest_path):
    res = requests.get(os.path.join(app.config['remote_repo_url'], file_path), auth=get_credentials())
    if not res.ok:
        if res.status_code == 404:
            raise FileNotFoundError(file_path)
        raise Exception('Failed to fetch "%s" from remote. Reason: %s' % (file_path, res.reason))
    with open(dest_path, 'wb') as f:
        f.write(res.content.read())

def put_file_to_remote(file_path, dest_path):
    with open(file_path, 'rb') as f:
        res = requests.put(os.path.join(app.config['remote_repo_url'], dest_path), 
                            auth=get_credentials(), data=f)
    if not res.ok:
        raise Exception('Failed to put "%s" to remote. Reason: %s' % (file_path, res.reason))

@app.route('/upload', methods=['POST'])
def _upload():
    arch, err = get_arch()
    if err:
        return err
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        with get_directory_handle(arch) as dir_path:
            filename = secure_filename(file.filename)

            package_path = join(dir_path, filename)
            file.save(package_path)

            index_path = join(dir_path, 'APKINDEX.tar.gz')
            if isfile(index_path):
                update_index(index_path, arch, package_path)
            else:
                build_index(dir_path, arch)

            if app.config['priv_key_path']:
                app.indexer.sign_index(index_path, app.config['priv_key_path'])

            if app.config['remote']:
                # upload all files from dir_path to remote server
                for name in os.listdir(dir_path):
                    put_file_to_remote(join(dir_path, name), join(arch, name))

        return make_response('OK', 200)

@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    arch, err = get_arch()
    if err:
        return err
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    packages_paths = []

    with get_directory_handle(arch) as dir_path:
        for file in request.files.getlist('file'):
            filename = secure_filename(file.filename)

            package_path = join(dir_path, filename)
            file.save(package_path)
            packages_paths.append(package_path)

        index_path = join(dir_path, 'APKINDEX.tar.gz')
        if isfile(index_path):
            update_index(index_path, arch, *packages_paths)
        else:
            build_index(dir_path, arch)
            
        if app.config['priv_key_path']:
            app.indexer.sign_index(index_path, app.config['priv_key_path'])
        
        if app.config['remote']:
            # upload all files from dir_path to proxied server
            for name in os.listdir(dir_path):
                put_file_to_remote(join(dir_path, name), join(arch, name))

    return make_response('OK', 200)

@app.route('/rebuild', methods=['POST'])
def _rebuild_index():
    arch, err = get_arch()
    if err:
        return err
    check_arch_dir(arch)
    rebuild_index(arch)
    return make_response('OK', 200)

def configure_arguments_parser():
    args_parser = argparse.ArgumentParser(__package__)

    meg = args_parser.add_mutually_exclusive_group()
    meg.add_argument('--repo-path', help='path of the local repository root', default=None)
    meg.add_argument('--remote', help='index to a remote repository', action='store_true', default=False)
    
    args_parser.add_argument('--default-arch', help='repository architecture', choices=common.ARCHITECURES, default='x86_64')
    args_parser.add_argument('--command-timeout', help='timeout (in seconds) to each apk command in indexer', type=int, default=10)
    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)
    
    priv_key_group = args_parser.add_mutually_exclusive_group()
    priv_key_group.add_argument('--priv-key', help='private key (as text)', default=None)
    priv_key_group.add_argument('--priv-key-file', help='file contains the repository private key', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)
    args_parser.add_argument('--clean', help='clean all files from repository folder before begin listening', action='store_true', default=False)
    
    args_parser.add_argument('--remote-repo-url', help='url to the remote proxy', default=None)
    args_parser.add_argument('--remote-username', help='username to access remote repository', default=None)
    args_parser.add_argument('--remote-password', help='password to authenticate to remote repository', default=None)

    args_parser.add_argument('--log-level', help='log level', choices=common.LOG_LEVELS, default='INFO')

    return args_parser

def main(argv=None):
    args_parser = configure_arguments_parser()
    args = args_parser.parse_args(argv)

    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log_level)


    app.logger.setLevel(numeric_level)
    app.logger.debug(args)

    if args.max_content_length is not None:
        app.config['MAX_CONTENT_LENGTH'] = args.max_content_length
    
    # copy arguments from args to app.config
    for arg_key in dir(args):
        if not arg_key.startswith('_') and not arg_key.endswith('_'):
            app.config[arg_key] = getattr(args, arg_key)
        
    if args.clean:
        if app.config['remote']:
            raise Exception('Cant clean index in remote mode')
        for name in os.listdir(app.config['repo_path']):
            file_path = os.path.join(app.config['repo_path'], name)
            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.unlink(file_path)
    
    if app.config['remote'] and not app.config['remote_repo_url']:
        raise Exception('--remote-repo-url is required when using --remote')

    with _get_private_key_handle(args.priv_key_file, args.priv_key) as priv_key_path:
        app.config['priv_key_path'] = priv_key_path

        app.run(host='0.0.0.0', port=args.p)

if __name__ == '__main__':
    main()
