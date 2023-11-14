
import subprocess
import os, os.path
import json
import requests
import time
from test_frame import prepare, test, run_tests, cleanup


def generate_tool():
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run("../diagram_tool_generator/generate_tool.py sysml_model.py", shell=True)
    if not os.path.exists('public/src'):
        os.symlink(os.path.abspath('../public/src'), 'public/src')
    import build.sysml_model_data as dm
    db = 'build/data/diagrams.sqlite3'
    if os.path.exists(db):
        os.remove(db)

def run_server():
    """ Start the server in a seperate process. Return the URL to access it.
        The framework will automatically stop the server when the test is finished.
    """
    server = subprocess.Popen(['/usr/local/bin/python3.11', 'sysml_model_run.py', '5200'], cwd=os.getcwd()+'/build')
    time.sleep(1)         # Allow the server to start up
    @cleanup
    def stop_server():
        server.terminate()
        server.wait()
    return  'http://localhost:5200'


@prepare
def test_server():
    generate_tool()
    base_url = run_server()

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

if __name__ == '__main__':
    run_tests()
