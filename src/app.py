import os
import tempfile
import logging
import uuid
import argparse
from flask import Flask, flash, request, redirect, make_response
from flask.logging import create_logger
from werkzeug.utils import secure_filename

from . import common, indexer

ALLOWED_EXTENSIONS = {'apk'}

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_arch():
    arch = request.args.get('arch', app.config['DEFAULT_ARCH'])
    if arch not in common.ARCHITECURES:
        return None, make_response('Invalid architecture! Options: %s. Default: %s'
            % (common.ARCHITECURES, app.config['DEFAULT_ARCH']),400)
    return arch, None

def check_arch_dir(repo_root, arch):
    arch_dir = os.path.join(repo_root, arch)
    if not os.path.isdir(arch_dir):
        os.mkdir(arch_dir)

def _get_private_key_handle(key_file_path, key_value):
    if key_file_path:
        return open(key_file_path)
    elif key_value:
        handler = tempfile.NamedTemporaryFile(suffix='.rsa')
        handler.write(key_value)
        return handler

    return common.NullFileDisposible()

@app.route('/rebuild', methods=['POST'])
def build_index():
    arch, err = get_arch()
    if err:
        return err
    app.config['check_arch_dir'](arch)
    app.config['build_index'](arch)
    return make_response('OK', 200)

@app.route('/upload', methods=['POST'])
def upload_file():
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
        app.config['check_arch_dir'](arch)
        filename = secure_filename(file.filename)
        package_path = os.path.join(app.config['repo_path'], arch, filename)
        file.save(package_path)
        app.config['update_index'](package_path, architecture=arch)
        return make_response('OK', 200)

@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    # TODO: rebuild index option
    arch, err = get_arch()
    if err:
        return err
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    app.config['check_arch_dir'](arch)
    packages_paths = []
    for file in request.files.getlist('file'):
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            package_path = os.path.join(app.config['repo_path'], arch, filename) 
            file.save(package_path)
            packages_paths.append(package_path)
   
    #app.config['build_index'](arch)
    app.config['update_index'](*packages_paths, architecture=arch)
    return make_response('OK', 200)


def main(argv=None):
    args_parser = argparse.ArgumentParser(__package__)
    args_parser.add_argument('repo_path', help='path of the repository root')
    
    args_parser.add_argument('--default-arch', help='repository architecture', choices=common.ARCHITECURES, default='x86_64')
    args_parser.add_argument('--command-timeout', help='timeout (in seconds) to each apk command in indexer', type=int, default=10)
    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)
    
    priv_key_group = args_parser.add_mutually_exclusive_group()
    priv_key_group.add_argument('--priv-key', help='private key (as text)', default=None)
    priv_key_group.add_argument('--priv-key-file', help='file contains the repository private key', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)
    args_parser.add_argument('--clean', help='clean all files from repository folder before begin listening', action='store_true', default=False)
    
    args_parser.add_argument('--log-level', help='log level', choices=logging._levelToName.values(), default='INFO')
    
    args = args_parser.parse_args(argv)

    logger = create_logger(app)

    logger.setLevel(getattr(logging, args.log_level))
    logger.debug(args)

    if args.max_content_length is not None:
        app.config['MAX_CONTENT_LENGTH'] = args.max_content_length
        
    if args.clean:
        for name in os.listdir(args.repo_path):
            file_path = os.path.join(args.repo_path, name)
            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.unlink(file_path)

    with _get_private_key_handle(args.priv_key_file, args.priv_key) as priv_key_handle:
        def build_index(architecture=args.default_arch):
            return indexer.build_index(os.path.join(args.repo_path, architecture), architecture, 
                private_key_file_path=priv_key_handle.name, command_timeout=args.command_timeout)
        def update_index(*packages, architecture=args.default_arch):
            return indexer.update_index(os.path.join(args.repo_path, architecture), *packages, architecture=architecture)
        def _check_arch_dir(architecture=args.default_arch):
            return check_arch_dir(args.repo_path, architecture)

        app.config['DEFAULT_ARCH'] = args.default_arch
        app.config['repo_path'] = args.repo_path
        app.config['build_index'] = build_index
        app.config['update_index'] = update_index
        app.config['check_arch_dir'] = _check_arch_dir

        build_index()

        app.run(host='0.0.0.0', port=args.p)

if __name__ == '__main__':
    main()
