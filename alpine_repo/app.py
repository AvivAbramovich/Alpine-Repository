import re
import logging
import uuid
import argparse
from typing import List, Dict, Tuple


from flask import Flask, flash, request, redirect, make_response
from flask.logging import create_logger
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from alpine_repo import common
from alpine_repo import drivers

ALLOWED_EXTENSIONS = {'apk'}


class IndexerFlaskApp(Flask):
    """
    Wrapper to Flask app with logger, indexer and secret key
    """
    def __init__(self, name, secret_key, driver=None):
        super().__init__(name)
        self.logger: logging.Logger = create_logger(self)
        self.secret_key = secret_key
        self.driver: drivers.IDriver = driver


def get_drivers() -> List[str]:
    # import drivers modules
    drivers.import_modules()

    # return all imported modules
    return drivers.REGISTERED_DRIVERS.keys()


def get_driver_class(name):
    return drivers.REGISTERED_DRIVERS[name]


app = IndexerFlaskApp(__name__, str(uuid.uuid4()))


def allowed_file(filename: str) -> bool:
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_arch():
    arch = request.args.get('arch', app.config['default_arch'])
    if arch not in common.ARCHITECURES:
        return None, make_response('Invalid architecture! Options: %s. Default: %s'
            % (common.ARCHITECURES, app.config['default_arch']), 400)
    return arch, None  


@app.route('/upload', methods=['POST'])
def _upload():
    arch, err = get_arch()
    if err:
        return err
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file: FileStorage = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        app.driver.add_package(filename, file, arch)
        return make_response('OK', 200)


@app.route('/bulk_upload', methods=['POST'])
def bulk_upload():
    arch, err = get_arch()
    if err:
        return err
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    files: List[FileStorage] = request.files.getlist('file')
    packages = {secure_filename(file.filename): file for file in files}
    app.driver.add_packages(packages, arch)
    return make_response('OK', 200)


@app.route('/rebuild', methods=['POST'])
def _rebuild_index():
    app.driver.rebuild_index()
    return make_response('OK', 200)


def parse_driver_options(driver_option: str) -> Tuple[str, str]:
    assignment_index = driver_option.index('=')
    return \
        driver_option[:assignment_index].strip(), \
        driver_option[assignment_index+1:].strip()


def configure_arguments_parser():
    args_parser = argparse.ArgumentParser(__package__)

    args_parser.add_argument('driver', default='local', choices=get_drivers())
    args_parser.add_argument('--driver-opt', action='append')

    args_parser.add_argument('--default-arch', help='repository architecture', choices=common.ARCHITECURES, default='x86_64')

    args_parser.add_argument('--clean', help='clean repository on startup', action='store_true', default=False)

    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)

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

    driver_cls = get_driver_class(args.driver)
    driver_options = {t[0]: t[1] for t in
                      [parse_driver_options(option) for option in args.driver_opt]}
    driver: drivers.IDriver = driver_cls(**driver_options)

    if isinstance(driver, common.ILoggerSettable):
        driver.set_logger(app.logger)

    if args.clean:
        driver.clean_repository()

    app.driver = driver

    # copy arguments from args to app.config
    for arg_key in dir(args):
        if not arg_key.startswith('_') and not arg_key.endswith('_'):
            app.config[arg_key] = getattr(args, arg_key)

    app.run(host='0.0.0.0', port=args.p)


if __name__ == '__main__':
    main()
