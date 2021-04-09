import os
from flask import Flask, flash, request, redirect, url_for, make_response
from werkzeug.utils import secure_filename
from argparse import ArgumentParser
from uuid import uuid4

ALLOWED_EXTENSIONS = {'apk', 'txt'}

app = Flask(__name__)
app.secret_key = str(uuid4())

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        # TODO: call index
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
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # TODO: call index
    return make_response('OK', 200)


def main(argv=None):
    args_parser = ArgumentParser(__package__)
    args_parser.add_argument('uploaded_folder', help='folder to uploading files')
    args_parser.add_argument('--max-content-length', type=int, help='max content length for uploaded files', default=None)
    
    priv_key_group = args_parser.add_mutually_exclusive_group()
    priv_key_group.add_argument('--priv-key', help='private key (as text)', default=None)
    priv_key_group.add_argument('--priv-key-file', help='file contains the repository private key', default=None)

    args_parser.add_argument('-p', help='listening port', type=int, default=80)
    args_parser.add_argument('--clean', help='clean all files from uploaded_folder before begin listening', action='store_true', default=False)
    args = args_parser.parse_args(argv)

    app.config['UPLOAD_FOLDER'] = args.uploaded_folder
    if args.max_content_length is not None:
        app.config['MAX_CONTENT_LENGTH'] = args.max_content_length
    
    if args.clean:
        for name in os.listdir(args.uploaded_folder):
            file_path = os.path.join(args.uploaded_folder, name)
            if os.path.islink(file_path) or os.path.isfile(file_path):
                os.unlink(file_path)

    app.run(host='0.0.0.0', port=args.p)

if __name__ == '__main__':
    main()