
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
        r = requests.get(f'{base_url}/data/Version')
        assert r.status_code == 200
        records = json.loads(r.content)
        assert len(records) == 2
        assert records[0]['versionnr'] == '0.1'
        assert records[0]['category'] == 'generator'
        assert records[1]['versionnr'] == '0.1'
        assert records[1]['category'] == 'model'


if __name__ == '__main__':
    run_tests()
