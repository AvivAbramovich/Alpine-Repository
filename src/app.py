import os
import tempfile
import logging
import uuid
import argparse
import requests
from os.path import join, isfile
from flask import Flask, flash, request, redirect, make_response
from flask.logging import create_logger
from werkzeug.utils import secure_filename
from functools import partial

from . import common
from .indexer import Indexer

ALLOWED_EXTENSIONS = {'apk'}

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _get_private_key_handle(key_file_path, key_value):
    if key_value:
        handler = tempfile.NamedTemporaryFile(suffix='.rsa')
        handler.write(key_value)
        return handler
    return common.NamedDisposible(key_file_path)

def configure_arguments_parser():
    args_parser = argparse.ArgumentParser(__package__)

    args_parser.add_argument('--repo-path', help='path of the repository root', default=None)
    
    args_parser.add_argument('--default-arch', help='repository architecture', choices=common.ARCHITECURES, default='x86_64')
    args_parser.add_argument('--command-timeout', help='timeout (in seconds) to each apk command in indexer', type=int, default=10)
    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)
    
    priv_key_group = args_parser.add_mutually_exclusive_group()
    priv_key_group.add_argument('--priv-key', help='private key (as text)', default=None)
    priv_key_group.add_argument('--priv-key-file', help='file contains the repository private key', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)
    args_parser.add_argument('--clean', help='clean all files from repository folder before begin listening', action='store_true', default=False)
    
    args_parser.add_argument('--proxy', help='serve as proxy to remote repository', action='store_true', default=False)
    args_parser.add_argument('--proxy-repo-url', help='url to the remote proxy', default=None)
    args_parser.add_argument('--proxy-credentials', help='credentials to proxy authentication (username:password)', default=None)

    args_parser.add_argument('--log-level', help='log level', choices=logging._levelToName.values(), default='INFO')

    return args_parser

def main(argv=None):
    args_parser = configure_arguments_parser()
    args = args_parser.parse_args(argv)

    logger = create_logger(app)

    logger.setLevel(getattr(logging, args.log_level))
    logger.debug(args)

    if args.max_content_length is not None:
        app.config['MAX_CONTENT_LENGTH'] = args.max_content_length
        
    if args.clean:
        if args.proxy:
            raise Exception('Cant clean index in proxy mode')
        for name in os.listdir(args.repo_path):
            file_path = os.path.join(args.repo_path, name)
            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.unlink(file_path)
    
    if args.proxy and not args.proxy_repo_url:
        raise Exception('--proxy-repo-url is required when using --proxy')
    
    if not args.proxy and not args.repo_path:
        raise Exception('at least one of --proxy (proxy mode) or --repo_path (local mode) must be set')
        
    def get_credentials():
        return tuple(args.proxy_credentials.split(':'))

    indexer = Indexer(logger)

    def get_directory_handle(rel_path):
        if args.proxy:
            t = tempfile.TemporaryDirectory()
            try:
                # try fetch index
                index_path = join(rel_path, 'APKINDEX.tar.gz')
                fetch_file_from_proxy(index_path, join(t.name, index_path))
            except FileNotFoundError:
                pass
            return t
        return common.NamedDisposible(join(args.repo_path, rel_path))
    
    def update_index(index_path, arch, *packages):
        indexer.update_index(index_path, *packages, architecture=arch)

    def get_arch():
        arch = request.args.get('arch', args.default_arch)
        if arch not in common.ARCHITECURES:
            return None, make_response('Invalid architecture! Options: %s. Default: %s'
                % (common.ARCHITECURES, args.default_arch),400)
        return arch, None    

    def fetch_file_from_proxy(file_path, dest_path):
        kwargs = {}
        if args.proxy_credentials:
            kwargs['auth'] = get_credentials()
        res = requests.get(os.path.join(args.proxy_repo_url, file_path), **kwargs)
        if not res.ok:
            if res.status_code == 404:
                raise FileNotFoundError(file_path)
            raise Exception('Failed to fetch "%s" from proxy. Reason: %s' % (file_path, res.reason))
        with open(dest_path, 'wb') as f:
            f.write(res.content.read())

    def put_file_to_proxy(file_path, dest_path):
        kwargs = {}
        if args.proxy_credentials:
            kwargs['auth'] = get_credentials()
        with open(file_path, 'rb') as f:
            kwargs['data'] = f
            res = requests.put(os.path.join(args.proxy_repo_url, dest_path), **kwargs)
        if not res.ok:
            raise Exception('Failed to put "%s" to proxy. Reason: %s' % (file_path, res.reason))

    with _get_private_key_handle(args.priv_key_file, args.priv_key) as priv_key_path:
        def build_index(dir_path, arch):
            indexer.build_index(dir_path, rewrite_architecture=arch)

        def rebuild_index(architecture=args.default_arch):
            if args.proxy:
                raise Exception('Cant rebuild index in proxy mode')
            indexer.build_index(join(args.repo_path, architecture), 
                rewrite_architecture=architecture, command_timeout=args.command_timeout)
            
        def check_arch_dir(base_dir, architecture=args.default_arch):
            arch_dir = os.path.join(dir, architecture)
            if not os.path.isdir(arch_dir):
                os.mkdir(arch_dir)
        
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
                    
                    if priv_key_path:
                        indexer.sign_index(index_path, priv_key_path)
                    
                    if args.proxy:
                        # upload all files from dir_path to proxied server
                        for name in os.listdir(dir_path):
                            put_file_to_proxy(join(dir_path, name), join(arch, name))
                
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
                    
                if priv_key_path:
                    indexer.sign_index(index_path, priv_key_path)
                
                if args.proxy:
                    # upload all files from dir_path to proxied server
                    for name in os.listdir(dir_path):
                        put_file_to_proxy(join(dir_path, name), join(arch, name))

            return make_response('OK', 200)

        @app.route('/rebuild', methods=['POST'])
        def _rebuild_index():
            arch, err = get_arch()
            if err:
                return err
            check_arch_dir(arch)
            rebuild_index(arch)            
            return make_response('OK', 200)

        if not args.proxy:
            rebuild_index()

        app.run(host='0.0.0.0', port=args.p)

if __name__ == '__main__':
    main()
