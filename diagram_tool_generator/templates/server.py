#!/usr/bin/env python3
<%
"""
Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
%>


import os.path
import json
import logging
import flask
import magic
import sys
import sqlite3
from typing import Any, Dict
from dataclasses import is_dataclass
from sqlalchemy.orm import aliased
from sqlalchemy.sql import text
import ${generator.module_name}_data as dm



app = flask.Flask(__name__)

# Instance representations are treated (slightly) different than other representations,
# so we need to know which they are
<%
    from dataclasses import Field
    import model_definition as mdef
    from model_definition import fields, is_dataclass, parameter_spec

    ir = ", ".join([f'"{e.__name__}"' for e in generator.md.instance_of])

    parameter_specifications = {
        e.__name__: [f.name for f in fields(e) if parameter_spec in generator.get_inner_types(e, f.type)]
        for e in generator.ordered_items
        if any(parameter_spec in generator.get_inner_types(e, f.type) for f in fields(e))
    }
%>
INSTANCE_ENTITIES = [${ir}]

PARAMETER_SPECIFICATIONS = ${repr(parameter_specifications)}


def get_request_data() -> Dict[str, Any]:
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


def get_parameters_defaults(spec: dm.parameter_spec):
    """ Parse a parameter specification string into default parameters values string. """
    parameter_defaults = {
        'int': 0,
        'float': 0.0,
        'str': '',
        ${",\n        ".join([f"'{k}': {c.server.default}" for k, c in generator.md.type_conversions.items() if not (isinstance(c.server.default, str) and c.server.default.startswith('field('))])}
    }
    print("Determining the defaults for parameters:", repr(spec))
    if not spec:
        return {}
    if isinstance(spec, str):
        try:
            print(f'Reading parameters default from {spec}')
            spec = json.loads(spec)
        except json.JSONDecodeError:
            spec = {k.strip():v.strip() for k,v in [part.split(':') for part in spec.split(',')]}
    return {k: parameter_defaults[v] for k, v in spec.items()}
    #return {k.strip():parameter_defaults[v.strip()] for k,v in [part.split(':') for part in spec.split(',')]}


def create_port_representations(definition_id, representation_id, diagram, session, dm):
    # Find all direct children of this block
    children = session.query(dm._Entity).filter(dm._Entity.parent==definition_id).all()
    # Select only the ports
    port_entities = [dm.AWrapper.load_from_db(p) for p in children if p.type == dm.EntityType.Port]
    port_reprs = [dm._BlockRepresentation(
            diagram=diagram,
            block=ch.Id,
            parent=representation_id,
            x=0,
            y=0,
            z=0,
            width=0,
            height=0,
            styling='',
            category=dm.ReprCategory.port,
        ) for ch in port_entities]
    for p in port_reprs:
        session.add(p)
    return port_entities, port_reprs

def create_block_representation(index, table, data, session, dm):
    """ Create a new representation of a model entity.
        If necessary, this also creates representations of ports and other additional information
        useful for rendering the new element in a diagram.
    """
    if issubclass(table, dm.AInstance):
        # ensure the index actually exists, for safety
        definition_records = session.query(dm._Entity).filter(dm._Entity.Id == index).all()
        if len(definition_records) != 1:
            return flask.make_response(f'Not found', 404)
        definition_record = definition_records[0]
        definition = dm.AWrapper.load_from_db(definition_record)
        # Prepare the set of data to be stored in the Instance model object
        details = dict(parent=data['diagram'], definition=index)
        # Find the 'parameter_spec' fields and add them to the instance
        # This must be done runtime as the list of parameters is specified in the record being instantiated.
        # It is not set statically in the model specification.
        params = PARAMETER_SPECIFICATIONS.get(definition.__class__.__name__, [])
        all_params = {p: get_parameters_defaults(getattr(definition, p)) for p in params}
        details['parameters'] = all_params

        entity = table(**details)
        entity.store(session=session)
    else:
        entity = table.retrieve(index, session=session)

    record = dm._BlockRepresentation(
        diagram=data['diagram'],
        block=entity.Id,
        parent=None,
        x=data['x'],
        y=data['y'],
        z=data.get('z', 0),
        width=data['width'],
        height=data['height'],
        styling='',
        category = data.get('category', dm.ReprCategory.block)
    )
    record.post_init()
    session.add(record)
    session.commit()

    if issubclass(table, dm.AInstance):
        # For an instance, represent the ports belonging to the original entity, not the instance we created just now.
        port_entities, port_reprs = create_port_representations(index, record.Id, data['diagram'], session, dm)
    else:
        # Represent the ports belonging to the block being represented.
        port_entities, port_reprs = create_port_representations(entity.Id, record.Id, data['diagram'], session, dm)
    session.commit()
    record_dict = record.asdict()
    record_dict['_entity'] = entity.asdict()
    if issubclass(table, dm.AInstance):
        record_dict['_definition'] = definition.asdict()
    record_dict['children'] = [p.asdict() for p in port_reprs]
    for e, p in zip(port_entities, record_dict['children']):
        p['_entity'] = e.asdict()
    return flask.make_response(json.dumps(record_dict, cls=dm.ExtendibleJsonEncoder), 201)

def create_relation_representation(index: int, table: type, data: Dict[str, Any], session, dm: type):
    entity = table.retrieve(index, session=session)
    # We need the waypoints supplied by the client.
    record = dm._RelationshipRepresentation(
        diagram=data['diagram'],
        relationship=index,
        source_repr_id=data['source'],
        target_repr_id=data['target'],
        routing=data['routing'],
        z=data['z'],
        styling='',
        rel_cls=table.__name__ + 'Representation',
        category=data.get('category', dm.ReprCategory.relationship)
    )
    record.post_init()
    session.add(record)
    session.commit()
    result_dict = record.asdict()
    result_dict['_entity'] = entity.asdict()
    return flask.make_response(json.dumps(record), 201)


###############################################################################
## Functions for selecting the database to use.
@app.route('/current_database', methods=['GET'])
def get_current_database():
    return flask.jsonify(dm.get_database_name()), 200


@app.route('/databases', methods=['GET'])
def get_databases():
    """Retrieve a list of available databases."""
    databases = dm.list_available_databases()
    return flask.jsonify(databases), 200


@app.route('/databases', methods=['POST'])
def create_db():
    """Create a new database."""
    data = flask.request.get_json()
    db_name = data.get('name')
    if not db_name.endswith('.sqlite3'):
        db_name = db_name + '.sqlite3'
    db_path = os.path.join(dm.data_dir, db_name)

    if os.path.exists(db_path):
        return flask.jsonify({"error": "Database already exists."}), 400

    # Create the database
    engine = dm.create_engine('sqlite:///${config.server_dir}/data/' + db_name)
    dm.init_db(engine)

    return flask.jsonify({"message": f"Database '{db_name}' created."}), 201


@app.route('/databases/<string:db_name>/activate', methods=['PUT'])
def activate_db(db_name):
    """Activate the specified database."""
    try:
        message = dm.switch_database(db_name)
        return flask.jsonify({"message": message}), 200
    except ValueError as e:
        return flask.jsonify({"error": str(e)}), 400


@app.route('/databases/<string:db_name>', methods=['DELETE'])
def delete_db(db_name):
    """Delete the specified database."""
    db_path = os.path.join(dm.data_dir, db_name)

    if not os.path.exists(db_path):
        return flask.jsonify({"error": "Database does not exist."}), 404

    os.remove(db_path)
    return flask.jsonify({"message": f"Database '{db_name}' deleted."}), 200


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
        with dm.session_context() as session:
            record = table.retrieve(index, session)
            for key, value in data.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.update(session)
            result = record.asjson()
            return flask.make_response(result, 202)

@app.route("/data/<path:path>", methods=['POST', 'PUT'])
def add_entity_data(path):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    data = get_request_data()
    data_id = data.get('Id', 0)
    data = {k:v for k, v in data.items() if k not in ['children', '__classname__', 'Id']}
    accept_id = flask.request.args.get('redo', 'false').lower() in ['true', 'y', '1']
    if accept_id:
        data['Id'] = data_id
    elif data_id:
        print("An ID was already set")
        return flask.make_response('Illegal request', 400)
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = table(**data)
            record.post_init()
            session.add(record)
            session.commit()
            return flask.make_response(json.dumps(record.asdict()), 201)
    else:
        record = table(**data)
        record.store(accept_id=accept_id)
        result = record.asjson()
        return flask.make_response(result, 201)

@app.route("/data/<path:path>/<int:index>/create_representation", methods=['POST'])
def create_representation(path, index):
    """ Create a representation of an existing entity.
        Also creates representations of children, if applicable (ports).
    """
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)

    with dm.session_context() as session:
        # Only the "entities" in the data model can have representations.
        # Port representations are not created independently.
        if not issubclass(table, dm.AWrapper) or issubclass(table, dm.APort):
            return flask.make_response("Can not create a representation", 405)

        data = get_request_data()

        # Check we are creating something for an existing diagram
        diagrams = session.query(dm._Entity).filter(dm._Entity.Id == int(data['diagram'])).all()
        if len(diagrams) != 1:
            return flask.make_response('Not found', 404)
        diagram = diagrams[0]
        diagram_cls = dm.__dict__.get(diagram.subtype, '')
        if not issubclass(diagram_cls, dm.ADiagram):
            return flask.make_response("Can not create a representation", 405)

        # Create the Representation for representations
        if issubclass(table, dm.ARelationship):
            return create_relation_representation(index, table, data, session, dm)

        # Create the Representation for other entities
        return create_block_representation(index, table, data, session, dm)

@app.route("/data/<path:path>/<int:index>", methods=['DELETE'])
def delete_entity_data(path, index):
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found', 404)
    if issubclass(table, dm.Base):
        with dm.session_context() as session:
            record = session.query(table).filter(table.Id==index).all()
            if record:
                record = record[0]
                session.delete(record)

                # If the last representation of a connection or instance is deleted, delete it from the model.
                if table is dm._RelationshipRepresentation:
                    count = session.query(table).filter(table.relationship==record.relationship).count()
                    if count == 0:
                        # Delete the relationship from the model.
                        session.query(dm._Relationship).filter(dm._Relationship.Id==record.relationship).delete()
                elif table is dm._BlockRepresentation:
                    # Find the model entity and optional definition
                    entity = session.query(dm._Entity).filter(dm._Entity.Id == record.block).first()
                    if entity.definition:
                        # Check if there are any more representation of this instance
                        count = session.query(table).filter(table.block == entity.Id).count()
                        if count == 0:
                            # Delete the underlying Instance from the model.
                            session.query(dm._Entity).filter(dm._Entity.Id == record.block).delete()

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
        # Using a pure SQL query is easier to get the blocks than tickeling SQLAlchemy and massaging what its returns.
        result = session.execute(text('''
            SELECT _blockrepresentation.*, _entity.details as _entity, definition.details as _definition
            FROM _blockrepresentation 
            LEFT JOIN _entity ON _blockrepresentation.block = _entity.Id 
            LEFT JOIN _entity as definition ON _entity.definition = definition.Id
            WHERE _blockrepresentation.diagram = :index;
        '''), {'index': index})

        data = [{k:v for k, v in zip(r._fields, r._data)} for r in result]
        for d in data:
            d['__classname__'] = '_BlockRepresentation'

        for r in data:
            details = json.loads(r['_entity'])
            r['_entity'] = details
            if details['__classname__'] in INSTANCE_ENTITIES:
                definition = json.loads(r['_definition'])
                r['_definition'] = definition
            else:
                del r['_definition']

        # Relationships are more straight-forward.
        for relat_rep in session.query(dm._RelationshipRepresentation, dm._Relationship).filter(dm._RelationshipRepresentation.diagram==index).join(dm._Relationship).all():
            r = relat_rep[0].asdict()
            r['_entity'] = json.loads(relat_rep[1].details)
            data.append(r)

        # Same for the messages
        for message_rep in session.query(dm._MessageRepresentation, dm._Entity).filter(dm._MessageRepresentation.diagram==index).\
                join(dm._Entity, dm._MessageRepresentation.message == dm._Entity.Id).all():
            m = message_rep[0].asdict()
            m['_entity'] = json.loads(message_rep[1].details)
            data.append(m)

    response = flask.make_response(
        json.dumps(data, cls=dm.ExtendibleJsonEncoder).encode('utf8'),
        200
    )
    response.headers['Content-Type'] = 'application/json'
    return response

    if False:
        entity = aliased(dm._Entity)
        definition = aliased(dm._Entity)
        query = session.query(dm._BlockRepresentation, dm._Entity).\
            filter(dm._BlockRepresentation.diagram==index).\
            join(entity, onclause=dm._BlockRepresentation.block==entity.Id).\
            join(definition, onclause=entity.definition==definition.Id)
        block_reps = query.all()
        relat_reps = session.query(dm._RelationshipRepresentation, dm._Relationship).filter(dm._RelationshipRepresentation.diagram==index).join(dm._Relationship).all()
        data = [(r[0].asdict(), r[1].asdict()) for r in block_reps+relat_reps]

        instance_indices = [i for i, r in enumerate(block_reps) if r[0].block_cls in INSTANCE_REPRESENTATIONS]
        instance_details = [json.loads(data[i][1]['details']) for i in instance_indices]
        definition_ids = [details['definition'] for details in instance_details]
        definitions = {r.Id: r.asdict() for r in
                       session.query(dm._Entity).filter(dm._Entity.Id.in_(definition_ids)).all()}

    # Decode the details in each Entity
    for r in data:
        details = json.loads(r[1]['details'])
        r[0]['_entity'] = details

    for i, def_id in zip(instance_indices, definition_ids):
        d = definitions[def_id]
        details = json.loads(d['details'])
        data[i][0]['_definition'] = details

    data = [r[0] for r in data]

    response = flask.make_response(
        json.dumps(data, cls=dm.ExtendibleJsonEncoder).encode('utf8'),
        200
    )
    response.headers['Content-Type'] = 'application/json'
    return response

# #############################################################################
# # Serve the static data (HTML, JS and other resources)
assets_dir = "${config.pub_dir}"

@app.route('/stylesheet.css')
def send_css():
    return flask.send_from_directory(assets_dir, 'stylesheet.css', mimetype='text/css')

@app.route('/src/<path:path>')
def external_src(path):
    fname = f'{assets_dir}/src/{path}'
    mime_type = my_get_mime(fname)
    return flask.send_from_directory(f'{assets_dir}/src', path, mimetype=mime_type)

@app.route('/assets/<path:path>')
def external_assets(path):
    fname = f'{assets_dir}/assets/{path}'
    mime_type = my_get_mime(fname)
    return flask.send_from_directory(f'{assets_dir}/assets', path, mimetype=mime_type)

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
    if path.endswith('.py'):
        mime_type = my_get_mime(path)
        return flask.send_from_directory(app.config['client_src'], path, mimetype=mime_type)
    return "NOT FOUND", 404

@app.route('/')
def send_index():
    return flask.redirect("${generator.module_name}_client.html", 302)
    #return flask.send_from_directory("${config.client_dir}", 'index.html', mimetype='text/html')


def run(port, client_src):
    if not os.path.exists('data'):
        os.mkdir('data')
    app.config['client_dir'] = 'public'
    app.config['client_src'] = '../'+client_src
    dm.init_db()
    app.run(threaded=True, host='0.0.0.0', port=int(port))


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else '5100', 'client_src')
