#!/usr/bin/env python3

import os.path
import json
import logging
import flask
import magic
import sys
from typing import Any, Dict
from dataclasses import is_dataclass
import ${generator.module_name}data as dm



app = flask.Flask(__name__)

# Instance representations are treated (slightly) different than other representations,
# so we need to know which they are
<%
    ir = ", ".join([f'"{e.__name__}Representation"' for e in generator.md.instance_of])
%>
INSTANCE_REPRESENTATIONS = [${ir}]

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



def create_port_representations(definition_id, representation_id, diagram, session, dm):
    # Find all direct children of this block
    children = session.query(dm._Entity).filter(dm._Entity.parent==definition_id).all()
    # Select only the ports
    port_entities = [p for p in children if p.type == dm.EntityType.Port]
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
            block_cls=ch.subtype + 'Representation',
        ) for ch in port_entities]
    for p in port_reprs:
        session.add(p)
    return port_entities, port_reprs

def create_block_representation(index, table, data, session, dm):
    if issubclass(table, dm.AInstance):
        # ensure the index actually exists, for safety
        if session.query(dm._Entity).filter(dm._Entity.Id == index).count() != 1:
            return flask.make_response(f'Not found', 404)
        # We are creating a new instance, it also needs adding in the
        entity = table(parent=data['diagram'], definition=index)
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
        block_cls=type(entity).__name__ + 'Representation'
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
        rel_cls=table.__name__ + 'Representation'
    )
    record.post_init()
    session.add(record)
    session.commit()
    result_dict = record.asdict()
    result_dict['_entity'] = entity.asdict()
    return flask.make_response(json.dumps(record), 201)


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

@app.route("/data/<path:path>/<int:index>/create_instance", methods=['POST'])
def create_instance(path, index):
    """ Create an instance of a pre-defined class / block / etc.
        The following steps are taken:
        1. The Instance object is created in the hierarchical model for storing parameters.
        2. The representation is created for the diagram.
        3. The representations for the ports associated with the pre-defined block are created
        Arguments:
            path -- the name of the Instance class to be created.
            index -- the index of the definition record.
    """
    if not (table := dm.__dict__.get(path, '')):
        return flask.make_response('Not found 1', 404)
    data = get_request_data()

    with dm.session_context() as session:
        # Check the definition object actually exists
        nr_definitions = session.query(dm._Entity).filter(dm._Entity.Id == index).count()
        print("Found records:", nr_definitions)
        nr_definitions = len(nr_definitions)
        if nr_definitions != 1:
            return flask.make_response(f'Not found 2 - {nr_definitions}', 404)

        # Create the structural element for this entity and persist it.
        # The instance is created under the diagram in the hierarchical model.
        model_record = table(parent=data['diagram'], definition=index)
        model_record.store()

        # Create the representation of the Instance
        record = dm._BlockRepresentation(
            diagram=data['diagram'],
            block=model_record.Id,
            parent=None,
            x=data['x'],
            y=data['y'],
            z=data.get('z', 0),
            width=data['width'],
            height=data['height'],
            styling='',
            block_cls=f'{path}Representation'
        )
        record.post_init()
        session.add(record)
        session.commit()

        # Create any ports associated with this object
        port_entities, port_reprs = create_port_representations(index, record.Id, data['diagram'], session, dm)
        record_dict = record.asdict()
        record_dict['_entity'] = model_record.asdict()
        record_dict['children'] = [p.asdict() for p in port_reprs]
        for e, p in zip(port_entities, record_dict['children']):
            p['_entity'] = e.asdict()
        return flask.make_response(json.dumps(record_dict, cls=dm.ExtendibleJsonEncoder), 201)

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
                    if record.block_cls in INSTANCE_REPRESENTATIONS:
                        # Check if there are any more representation of this block
                        count = session.query(table).filter(table.block == record.block).count()
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