
import subprocess
import os, os.path
import json
import requests
import time
from dataclasses import is_dataclass
from test_frame import prepare, test, run_tests, cleanup
import generate_project     # Ensures the client is built up to date


def run_server():
    """ Start the server in a seperate process. Return the URL to access it.
        The framework will automatically stop the server when the test is finished.
    """
    server = subprocess.Popen(['/usr/local/bin/python3.11', 'sysml_run.py', '5200'], cwd=os.getcwd()+'/build')
    time.sleep(1)         # Allow the server to start up
    @cleanup
    def stop_server():
        server.terminate()
        server.wait()
    return  'http://localhost:5200'


@prepare
def test_server():
    base_url = run_server()

    from build import sysml_model_data as sm

    def clear_db():
        with sm.session_context() as session:
            session.query(sm._Entity).delete()
            session.query(sm._Relationship).delete()
            session.query(sm._BlockRepresentation).delete()
            session.query(sm._RelationshipRepresentation).delete()

    def load_db(records):
        with sm.session_context() as session:
            for r in records:
                if is_dataclass(r):
                    r.store(session)
                else:
                    session.add(r)

    @test
    def test_version():
        """ This is a built-in element of the database, that uses a different mechanism
            then the entities that are actually part of the model. So it is tested seperately.
        """
        # Check there are two pre-created versions
        vurl = f'{base_url}/data/Version'
        r = requests.get(vurl)
        assert r.status_code == 200
        records = json.loads(r.content)
        assert len(records) == 2
        assert records[0]['versionnr'] == '0.1'
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
        sm.changeDbase("sqlite:///build/data/diagrams.sqlite3")
        clear_db()
        load_db([
            sm.Note(),
            sm.BlockDefinitionDiagram()
        ])
        load_db([
            sm._BlockRepresentation(block=1, diagram=2),
            sm._BlockRepresentation(block=1, diagram=2)
        ])

        r = requests.get(base_url+'/data/diagram_contents/2')
        assert r.status_code == 200
        results = json.loads(r.content)
        assert results[0]['diagram'] == 2
        assert results[1]['diagram'] == 2

if __name__ == '__main__':
    run_tests()
