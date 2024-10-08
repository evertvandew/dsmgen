
import subprocess
import os, os.path
import json
import requests
import time
from dataclasses import is_dataclass
import threading
import sys

import data_store
from test_frame import prepare, test, run_tests, cleanup
import generate_project     # Ensures the client is built up to date

from build.sysml_data import GEN_VERSION
START_SERVER = True
START_THREADED_SERVER = False

def run_server():
    """ Start the server in a separate process. Return the URL to access it.
        The framework will automatically stop the server when the test is finished.
    """
    port = '5200'
    local_url = f'http://localhost:{port}'
    if START_SERVER:
        server = subprocess.Popen(['/usr/local/bin/python3.12', 'sysml_run.py', port], cwd=os.getcwd()+'/build')
        @cleanup
        def stop_server():
            server.terminate()
            server.wait()
    elif START_THREADED_SERVER:
        sys.path.append(os.getcwd()+'/build')
        from build import sysml_run
        sysml_run.dm.changeDbase("sqlite:///build/data/diagrams.sqlite3")

        def run_threaded():
            sysml_run.run(port, 'client_src')
        th = threading.Thread(target = run_threaded)
        th.setDaemon(True)
        th.start()

    # Wait until the server is up
    while True:
        try:
            r = requests.get(local_url + '/current_database')
            if r.status_code == 200:
                break
        except:
            time.sleep(0.1)
    return local_url


@prepare
def test_server():
    import public.sysml_client as client
    #base_url = 'http://localhost:5200'
    base_url = run_server()

    from build import sysml_data as sm

    def clear_db():
        with sm.session_context() as session:
            session.query(sm._Entity).delete()
            session.query(sm._Representation).delete()

    def load_db(records):
        with sm.session_context() as session:
            for r in records:
                if isinstance(r, sm.SpecialRepresentation):
                    session.add(r.to_db())
                elif is_dataclass(r):
                    r.store(session, accept_id=True)
                else:
                    session.add(r)

    @test
    def test_version():
        """ This is a built-in element of the database, that uses a different mechanism
            then the entities that are actually part of the model. So it is tested separately.
        """
        # Check there are two pre-created versions
        vurl = f'{base_url}/data/Version'
        r = requests.get(vurl)
        assert r.status_code == 200
        records = json.loads(r.content)
        assert len(records) >= 2
        assert records[0]['versionnr'] == GEN_VERSION
        assert records[0]['category'] == 'generator'
        assert records[1]['versionnr'] == '0.1'
        assert records[1]['category'] == 'model'

        # Try to add a third, retrieve it.
        r = requests.post(
            vurl,
            data=json.dumps({'category': 'test', 'versionnr': '123.45.67'}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        r = requests.get(vurl+'/3')
        record = json.loads(r.content)
        assert r.status_code == 200
        assert record['category'] == 'test'
        assert record['versionnr'] == '123.45.67'

        # Update the record
        record['versionnr'] = '1.2'
        r = requests.post(
            vurl+'/3',
            data=json.dumps(record),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 202
        r = requests.get(vurl+'/3')
        record = json.loads(r.content)
        assert record['versionnr'] == '1.2'

        # Try to delete it
        r = requests.delete(vurl+'/3')
        assert r.status_code == 204
        r = requests.get(vurl+'/3')
        assert r.status_code == 404

    @test
    def test_Note():
        """ Test the support of the modelling entities. """
        # Try to add a Note, retrieve it.
        nurl = f'{base_url}/data/Note'
        r = requests.post(
            nurl,
            data=json.dumps(dict(
                __classname__= 'Note',
                description  = 'Dit is een test'
            )),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        nid = json.loads(r.content)['Id']
        r = requests.get(nurl+f'/{nid}')
        record = json.loads(r.content)
        assert r.status_code == 200
        assert record['description'] == 'Dit is een test'

        # Update the record
        record['description'] = 'Dit was een test'
        r = requests.post(
            nurl+f'/{nid}',
            data=json.dumps(record),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 202
        r = requests.get(nurl+f'/{nid}')
        record = json.loads(r.content)
        assert record['description'] == 'Dit was een test'

        # Try to delete it
        r = requests.delete(nurl+f'/{nid}')
        assert r.status_code == 204
        r = requests.get(nurl+f'/{nid}')
        assert r.status_code == 404

    @test
    def test_styling_formatting():
        """ Styling is stored in the database as a string, but outside it as a dict.
            The conversions are done by the server. Test them.
        """
        # We test with a Note, so first create the base Note
        r = requests.post(
            f'{base_url}/data/Note',
            data=json.dumps(dict(
                __classname__= 'Note',
                description  = 'Dit is een test'
            )),
            headers={'Content-Type': 'application/json'}
        )
        nid = json.loads(r.content)['Id']
        r = requests.post(
            f'{base_url}/data/BlockDefinitionDiagram',
            data=json.dumps(dict(
                __classname__= 'BlockDefinitionDiagram',
                name  = 'testdiagram'
            )),
            headers={'Content-Type': 'application/json'}
        )
        did = json.loads(r.content)['Id']

        # Try to create a representation of this Note.
        rurl = f'{base_url}/data/_BlockRepresentation'
        r = requests.post(
            rurl,
            data=json.dumps(dict(
                __classname__= '_BlockRepresentation',
                diagram  = did,
                block = nid,
                styling = {'color':'aabbcc', 'text_offset': 12}
            )),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        rid = json.loads(r.content)['Id']
        r = requests.get(rurl+f'/{rid}')
        assert r.status_code == 200
        record = json.loads(r.content)
        assert record['styling'] == {'color':'aabbcc', 'text_offset': 12}

    @test
    def test_diagram_contents():
        from data_store import DataStore, Collection
        from browser import ajax
        ajax.DO_NOT_SIMULATE = True
        ajax.server_base = base_url

        @cleanup
        def clean_up():
            ajax.DO_NOT_SIMULATE = False

        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            # Create a model, with one recursive block with a port,
            # and three connected blocks inside. Including the instance of another block
            sm.SubProgramDefinition(Id=1, name="Test diagram"),
            sm.FlowPort(Id=2, name='in', parent=2),
            sm.SubProgramDefinition(Id=3),
            sm.FlowPort(Id=4, parent=3),
            sm.BlockInstance(Id=5, definition=3),
            sm.Block(Id=6, name="Block 1", description="Dit is een test"),
            sm.Note(Id=7, description="Don't mind me"),
            sm.FlowPortConnection(Id=8, source=2, target=4),
            sm.Anchor(Id=9, source=7, target=6),

            # Put the representations in diagram #1
            # First the "blocks"
            sm._BlockRepresentation(Id=1, block=2, diagram=2, category=2),  # Port Label!
            sm._BlockRepresentation(Id=2, block=5, diagram=2, category=2),  # BlockInstance
            sm._BlockRepresentation(Id=3, block=6, diagram=2, category=2),  # Block
            sm._BlockRepresentation(Id=4, block=7, diagram=2, category=2),  # Note
            # The ports represented as ports
            sm._BlockRepresentation(Id=5, block=4, diagram=2, parent=2, category=3), # Port linked to block instance
            # Relationships
            sm._RelationshipRepresentation(
                Id=6,
                diagram=2,
                relationship=8,
                source_repr_id=1,
                target_repr_id=5
            ),  # From PortLabel to BlockInstance port
            sm._RelationshipRepresentation(
                Id=7,
                diagram=2,
                relationship=9,
                source_repr_id=4,
                target_repr_id=3
            )  # From Note to Block
        ])

        ds = DataStore(client.data_config)
        def check_data(data):
            assert len(data) == 6
            assert len(data[1].ports) == 1

        ds.get_diagram_data(2, check_data)
        assert len(ds.live_instances[Collection.block_repr]) == 5
        assert len(ds.live_instances[Collection.block]) == 5
        assert len(ds.live_instances[Collection.relation_repr]) == 2
        assert len(ds.live_instances[Collection.relation]) == 2

    @test
    def test_create_block_representation():
        # Load the DB with a block and two ports, then make a representation of it.
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.BlockDefinitionDiagram(Id=1, name="Test diagram"),
            sm.Block(Id=2, name="Block 1", description="Dit is een test", parent=1, order=1),
            sm.FlowPort(Id=3, name='out', orientation=4, parent=2),
            sm.FlowPort(Id=4, name='in', orientation=1, parent=2),
        ])
        r = requests.post(
            base_url+'/data/Block/2/create_representation',
            data=json.dumps({'diagram': 1, 'x': 400, 'y': 500, 'z': 0, 'width': 64, 'height': 40, 'category': 2}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        results = json.loads(r.content)
        for i, p in enumerate(results['children']):
            assert p['category'] == int(data_store.ReprCategory.port)
            assert p['block'] == 3 + i
            assert p['diagram'] == 1
            assert p['parent'] == 1

    @test
    def test_relationship_delete():
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.Note(Id=1, description="Don't mind me"),
            sm.BlockDefinitionDiagram(Id=2, name="Test diagram"),
            sm.Block(Id=3, name="Block 1", description="Dit is een test", parent=2, order=1),
            sm.Anchor(Id=4, source=3, target=1),
            sm._BlockRepresentation(Id=1, block=1, diagram=2),
            sm._BlockRepresentation(Id=2, block=3, diagram=2),
            sm._RelationshipRepresentation(Id=3, diagram=2, relationship=4, source_repr_id=1, target_repr_id=2),
            sm.BlockDefinitionDiagram(Id=5, name="Test diagram"),
            sm._BlockRepresentation(Id=4, block=1, diagram=5),
            sm._BlockRepresentation(Id=5, block=3, diagram=5),
            sm._RelationshipRepresentation(Id=6, diagram=5, relationship=4, source_repr_id=4, target_repr_id=5)
        ])

        # Delete the first representation
        r = requests.delete(base_url+'/data/_RelationshipRepresentation/3')
        assert r.status_code == 204
        # Ensure the relationship still exists
        r = requests.get(base_url+'/data/_Entity/4')
        assert r.status_code == 200
        # Delete the second representation
        r = requests.delete(base_url+'/data/_RelationshipRepresentation/6')
        assert r.status_code == 204
        # Ensure the relationship is still there.
        r = requests.get(base_url+'/data/_Entity/4')
        assert r.status_code == 200

    @test
    def test_create_delete_instance():
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.Note(Id=1, description="Don't mind me"),
            sm.BlockDefinitionDiagram(Id=2, name="Test diagram"),
            sm.SubProgramDefinition(Id=3, name="Block 1", description="Dit is een test", parent=2, order=1,
                                    parameters='{"limit":"int","factor":"float"}'),
            sm.FlowPort(Id=4, name='output', parent=3),
            sm.FlowPort(Id=5, name='input', parent=3)
        ])

        # Create an instance
        r = requests.post(
            base_url+'/data/BlockInstance/3/create_representation',
            data=json.dumps({'diagram': 2, 'x': 400, 'y': 500, 'z': 0, 'width': 64, 'height': 40, 'category': 2}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        results = json.loads(r.content)
        assert results['category'] == int(data_store.ReprCategory.block)
        assert results['Id'] == 1
        assert results['diagram'] == 2
        assert results['parent'] == None
        assert len(results['children']) == 2
        assert results['_entity']['__classname__'] == 'BlockInstance'
        assert results['_entity']['Id'] == 6
        assert results['_entity']['parent'] == 2    # The Instance block is created under the diagram
        assert results['_entity']['definition'] == 3
        assert results['_entity']['parameters'] == {'parameters': {'factor': 0.0, 'limit': 0}}
        assert results['_definition']['__classname__'] == 'SubProgramDefinition'
        assert results['_definition']['Id'] == 3
        assert results['_definition']['name'] == 'Block 1'
        assert results['_definition']['description'] == 'Dit is een test'
        assert results['_definition']['parameters'] == '{"limit":"int","factor":"float"}'

        for i, p in enumerate(results['children']):
            assert p['category'] == int(data_store.ReprCategory.port)
            assert p['block'] == 4 + i
            assert p['diagram'] == 2
            assert p['parent'] == 1
            assert p['_entity']['__classname__'] == 'FlowPort'
        # Check the underlying Instance can be accessed
        r = requests.get(base_url + '/data/BlockInstance/6')
        assert r.status_code == 200

        # Now delete the Instance Representation and check that the underlying Instance is deleted as well
        r = requests.delete(base_url+'/data/_BlockRepresentation/1')
        assert r.status_code == 204
        # Check the port representations are gone
        r = requests.get(base_url+'/data/_BlockRepresentation/2')
        assert r.status_code == 404
        r = requests.get(base_url+'/data/_BlockRepresentation/3')
        assert r.status_code == 404

    @test
    def test_create_instance_no_parameters():
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.Note(Id=1, description="Don't mind me"),
            sm.BlockDefinitionDiagram(Id=2, name="Test diagram"),
            sm.SubProgramDefinition(Id=3, name="Block 1", description="Dit is een test", parent=2, order=1,
                                    parameters=''),
            sm.FlowPort(Id=4, name="Input", parent=3, order=1)
        ])

        # Create an instance
        r = requests.post(
            base_url+'/data/BlockInstance/3/create_representation',
            data=json.dumps({'diagram': 2, 'x': 400, 'y': 500, 'z': 0, 'width': 64, 'height': 40,
                             'category': int(data_store.ReprCategory.block)}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        results = json.loads(r.content)
        assert results['Id'] == 1
        assert results['diagram'] == 2
        assert results['parent'] == None
        assert len(results['children']) == 1
        p = results['children'][0]
        assert p['Id'] == 2
        assert p['__classname__'] == '_BlockRepresentation'
        assert p['_entity']['Id'] == 4
        assert p['_entity']['__classname__'] == 'FlowPort'
        assert results['_entity']['__classname__'] == 'BlockInstance'
        assert results['_entity']['Id'] == 5
        assert results['_entity']['parent'] == 2    # The Instance block is created under the diagram
        assert results['_entity']['definition'] == 3
        assert results['_entity']['parameters'] == {'parameters': {}}
        assert results['_definition']['__classname__'] == 'SubProgramDefinition'
        assert results['_definition']['Id'] == 3
        assert results['_definition']['name'] == 'Block 1'
        assert results['_definition']['description'] == 'Dit is een test'
        assert results['_definition']['parameters'] == ''

    @test
    def redo_add():
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        # True to add an object with a pre-set ID.
        item = sm.Note(Id=123, description="Don't mind me")
        r = requests.post(
            base_url+'/data/Note',
            data=json.dumps(item.asdict()),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code > 399
        # Try again, now with the redo-flag
        r = requests.post(
            base_url+'/data/Note',
            params={'redo': True},
            data=json.dumps({'Id': 123, 'description': "Don't mind me"}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201

    @test
    def store_parameter_specification():
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.Block(Id=1, description="Don't mind me", parameters="type:PinType"),
            sm.BlockDefinitionDiagram(Id=2, name="Test diagram"),
        ])

        # Create an instance
        r = requests.post(
            base_url+'/data/BlockInstance/1/create_representation',
            data=json.dumps({'diagram': 2, 'x': 400, 'y': 500, 'z': 0, 'width': 64, 'height': 40,
                             'category': int(data_store.ReprCategory.block)}),
            headers={'Content-Type': 'application/json'}
        )
        assert r.status_code == 201
        results = json.loads(r.content)
        assert results['diagram'] == 2
        assert results['block'] == 3
        assert results['_entity']['parameters']['parameters']['type'] == 1


if __name__ == '__main__':
    run_tests('*.test_create_delete_instance')
    run_tests()
