#!/usr/bin/env python3

import os.path
import json
import logging
import flask
import magic
import sys
from dataclasses import is_dataclass
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

@app.route("/data/<path:path>", methods=['GET'])
def get_entities(path):
    """ For low-level tables, allow all of them to be obtained in one go. """
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            records = session.query(table).all()
            data = json.dumps([r.asdict() for r in records])
            result = flask.make_response(data, 200)
            result.headers['Content-Type'] = 'application/json'
            return result
    return flask.make_response('Not allowed', 400)



@app.route("/data/<path:path>/<int:index>", methods=['GET'])
def get_entity_data(path, index):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = session.query(table).filter(table.Id==index).first()
            if not record:
                return flask.make_response('Not found', 404)
            data = json.dumps(record.asdict())
            result = flask.make_response(data, 200)
            result.headers['Content-Type'] = 'application/json'
            return result
    elif is_dataclass(table):
        try:
            record = table.retrieve(index)
        except (dm.WrongType, dm.NotFound):
            return flask.make_response('Not found', 404)
        result = flask.make_response(record.asjson(), 200)
        result.headers['Content-Type'] = 'application/json'
        return result
    return flask.make_response('Not found', 404)

@app.route("/data/<path:path>/<int:index>", methods=['POST', 'PUT'])
def update_entity_data(path, index):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    data = get_request_data()
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = session.query(table).filter(table.Id==index).all()
            if not record:
                return flask.make_response('Not found', 404)
            record = record[0]
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.post_init()
            session.commit()
            data = json.dumps(record.asdict())
            result = flask.make_response(data, 202)
            result.headers['Content-Type'] = 'application/json'
            return result
    elif is_dataclass(table):
        record = table.retrieve(index)
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.update()
        result = record.asjson()
        return flask.make_response(result, 202)

@app.route("/data/<path:path>", methods=['POST', 'PUT'])
def add_entity_data(path):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    data = get_request_data()
    data = {k:v for k, v in data.items() if k not in ['children', '__classname__']}
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = table(**data)
            record.post_init()
            session.add(record)
            session.commit()
            return flask.make_response(json.dumps(record.asdict()), 201)
    else:
        record = table(**data)
        record.store()
        result = record.asjson()
        return flask.make_response(result, 201)

@app.route("/data/<path:path>/<int:index>", methods=['DELETE'])
def delete_entity_data(path, index):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = session.query(table).filter(table.Id==index).all()
            if record:
                session.delete(record[0])
                return flask.make_response('Deleted', 204)
            else:
                return flask.make_response('Not found', 404)
    else:
        record = table.retrieve(index)
        if type(record) != table:
            return flask.make_response('Not found', 404)
        record.delete()
        return flask.make_response('Deleted', 204)



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

@app.route('/data/diagram_contents/<int:index>', methods=['GET'])
def diagram_contents(index):
    with dm.session_context() as session:
        # Get the representations shown in the diagram.
        block_reps = session.query(dm._BlockRepresentation, dm._Entity).filter(dm._BlockRepresentation.diagram==index).join(dm._Entity, onclause=dm._BlockRepresentation.block==dm._Entity.Id).all()
        relat_reps = session.query(dm._RelationshipRepresentation, dm._Relationship).filter(dm._RelationshipRepresentation.diagram==index).join(dm._Relationship).all()
        data = [(r[0].asdict(), r[1].asdict()) for r in block_reps+relat_reps]

    # Decode the details in each Entity
    for r in data:
        details = json.loads(r[1]['details'])
        r[0]['_entity'] = details

    data = [r[0] for r in data]

    response = flask.make_response(
        json.dumps(data, cls=dm.ExtendibleJsonEncoder).encode('utf8'),
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


def run(port):
    if not os.path.exists('data'):
        os.mkdir('data')
    dm.init_db()
    app.run(threaded=True, host='0.0.0.0', port=int(port))


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else '5100')