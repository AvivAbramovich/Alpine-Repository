import os
import tempfile
import logging
from uuid import uuid4
from argparse import ArgumentParser
from flask import Flask, flash, request, redirect, make_response
from werkzeug.utils import secure_filename

from . import common, indexer

ALLOWED_EXTENSIONS = {'apk', 'txt'}

app = Flask(__name__)
app.secret_key = str(uuid4())

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def _get_private_key_handle(key_file_path, key_value):
    if key_file_path:
        return open(key_file_path)
    elif key_value:
        handler = tempfile.NamedTemporaryFile(suffix='.rsa')
        handler.write(key_value)
        return handler

    return common.NullFileDisposible()

@app.route('/build', methods=['POST'])
def build_index():
    app.config['index_repo']()
    return make_response('OK', 200)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['repo_path'], filename))
        app.config['index_repo']()
        return make_response('OK', 200)

@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    for file in request.files.getlist('file'):
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['repo_path'], filename))
            
    app.config['index_repo']()
    return make_response('OK', 200)


def main(argv=None):
    args_parser = ArgumentParser(__package__)
    # args_parser.add_argument('uploaded_folder', help='folder to uploading files')
    args_parser.add_argument('repo_path', help='path of the repository')
    
    args_parser.add_argument('--arch', help='repository architecture', choices=common.ARCHITECURES, default='x86_64')
    args_parser.add_argument('--command-timeout', help='timeout (in seconds) to each apk command in indexer', type=int, default=10)
    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)
    
    priv_key_group = args_parser.add_mutually_exclusive_group()
    priv_key_group.add_argument('--priv-key', help='private key (as text)', default=None)
    priv_key_group.add_argument('--priv-key-file', help='file contains the repository private key', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)
    args_parser.add_argument('--clean', help='clean all files from repository folder before begin listening', action='store_true', default=False)
    
    args_parser.add_argument('--log-level', help='log level', choices=logging._levelToName.keys(), default='INFO')
    
    args = args_parser.parse_args(argv)

    # app.logger.setLevel(getattr(logging, args.log_level))
    # app.logger.debug(args)

    # app.config['UPLOAD_FOLDER'] = args.uploaded_folder
    if args.max_content_length is not None:
        app.config['MAX_CONTENT_LENGTH'] = args.max_content_length
    
    if args.clean:
        for name in os.listdir(args.repo_path):
            file_path = os.path.join(args.repo_path, name)
            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.unlink(file_path)

    with _get_private_key_handle(args.priv_key_file, args.priv_key) as priv_key_handle:

        index_repo = lambda: indexer.index_repository(args.repo_path, args.arch, logger=app.logger,
            private_key_file_path=priv_key_handle.name, command_timeout=args.command_timeout)

        app.config['repo_path'] = args.repo_path
        app.config['index_repo'] = index_repo

        index_repo()

        app.run(host='0.0.0.0', port=args.p)

if __name__ == '__main__':
    main()
