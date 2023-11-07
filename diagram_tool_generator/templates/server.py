#!/usr/bin/env python3

import os.path
import json
import logging
import flask
import magic
import ${generator.module_name}_data as dm



app = flask.Flask(__name__)

def get_request_data():
    if flask.request.data:
        encoding = flask.request.args.get('encoding')
        if encoding == 'base64':
            new_data = flask.request.data.decode('base64')
        else:
            new_data = flask.request.data

        if isinstance(new_data, bytes) and flask.request.is_json:
            new_data = json.loads(new_data.decode('utf8'))
    else:
        # The data is encoded as form data. Just save them as JSON
        new_data = flask.request.values.to_dict()
    return new_data


def my_get_mime(path):
    """ Get the mime type of a file. """
    mime = None
    if path.endswith('.css'):
        return 'text/css'
    if path.endswith('.html'):
        return 'text/html'
    if os.path.exists(path):
        mime = magic.from_file(path, mime=True)
    else:
        logging.error(f"Trying to look up mime for file {path} failed: NOT FOUND")

    if mime is None:
        mime = 'application/octet-stream'
    else:
        mime = mime.replace(' [ [', '')
    return mime


# #############################################################################
# # Serve the dynamic data: the contents of the model as created and edited by the user.
% for entity in generator.ordered_items:
@app.route("/data/${entity.__name__}/<int:index>", methods=['GET'])
def get_${entity.__name__}_data(index):
    try:
        record = dm.${entity.__name__}.retrieve(index)
    except dm.WrongType:
        return flask.make_response('Not found', 404)
    result = flask.make_response(record.asjson(), 200)
    result.headers['Content-Type'] = 'application/json'
    return result

@app.route("/data/${entity.__name__}/<int:index>", methods=['POST', 'PUT'])
def update_${entity.__name__}_data(index):
    data = get_request_data()
    record = dm.${entity.__name__}.retrieve(index)
    for key, value in data:
        setattr(record, key, value)
    record.update()
    result = record.asjson()
    return flask.make_response(result, 202)

@app.route("/data/${entity.__name__}", methods=['POST', 'PUT'])
def add_${entity.__name__}_data():
    data = get_request_data()
    data = {k:v for k, v in data.items() if k not in ['children', '__classname__']}


    record = dm.${entity.__name__}(**data)
    record.store()
    result = record.asjson()
    return flask.make_response(result, 201)

% endfor



# #############################################################################
# # Some specialized queries

@app.route("/data/hierarchy", methods=['GET'])
def get_hierarchy():
    # Just load all elements in the hierarchy.
    # The actual hierarchy is not formed here but in the client,
    # because it is bothersome to deserialize from JSON.
    with dm.session_context() as session:
        entities = session.query(dm._Entity).all()
        blocks = [dm.AWrapper.load_from_db(r) for r in entities]

    response = flask.make_response(
        json.dumps(blocks, cls=dm.ExtendibleJsonEncoder).encode('utf8'),
        200
    )
    response.headers['Content-Type'] = 'application/json'
    return response

# #############################################################################
# # Serve the static data (HTML, JS and other resources)
@app.route('/<path:chapter>/<path:path>')
def send_static_2(chapter, path):
    fname = f'${config.client_dir}/{chapter}/{path}'
    mime_type = my_get_mime(fname)
    return flask.send_from_directory(f'${config.client_dir}/{chapter}', path, mimetype=mime_type)

@app.route('/<path:path>')
def send_static(path):
    i = f'${config.client_dir}/{path}/index.html'
    if os.path.exists(i):
        return flask.send_from_directory(f'${config.client_dir}/{path}', 'index.html')
    fname = f'${config.client_dir}/{path}'
    if os.path.exists(fname):
        mime_type = my_get_mime(fname)
        return flask.send_from_directory('${config.client_dir}', path, mimetype=mime_type)
    return "NOT FOUND", 404

@app.route('/')
def send_index():
    return flask.send_from_directory("${config.client_dir}", 'index.html', mimetype='text/html')


if __name__ == '__main__':
    if not os.path.exists('data'):
        os.mkdir('data')
    dm.init_db()
    app.run(threaded=True, host='0.0.0.0', port=5100)
