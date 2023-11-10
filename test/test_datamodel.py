
import subprocess
import os
import sys
import logging
from dataclasses import fields

###############################################################################
## Test framework
## Testing in python is so easy, wtf use frameworks?

all_tests = []
preparations = []

def test(func):
    all_tests.append(func)
    return func

def prepare(func):
    preparations.append(func)
    return func

def run_tests():
    for p in preparations:
        p()

    successes = []
    failures = []
    for t in all_tests:
        try:
            t()
            successes.append(t)
        except Exception as e:
            logging.exception(f'Error failed: {str(e)}')
            failures.append(t)

    logging.info(f"Failures: {len(failures)} / {len(all_tests)}")
    if failures:
        sys.exit(1)



###############################################################################
## The actual tests.

@prepare
def init():
    for d in ['public', 'data', 'build']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run("../diagram_tool_generator/generate_tool.py sysml_model.py", shell=True)
    import build.sysml_model_data as dm

    @test
    def create_database():
        dm.init_db()
        assert os.path.exists('data/diagrams.sqlite3')

    @test
    def store_retrieve_update_note():
        note = dm.Note(description="Dit is een opmerking")
        note.store()
        the_id = note.Id     # Actual value depends on database state
        assert the_id >= 1

        # Try to query the database and get the record
        note2 = dm.Note.retrieve(the_id)
        assert note.Id == note2.Id
        assert note.description == note2.description

        # Try to update the record
        note.description = "Creëren van Koeïen"
        note.store()
        note2 = dm.Note.retrieve(note.Id)
        assert note.Id == note2.Id
        assert note.description == note2.description

    @test
    def store_retrieve_update_network():
        blocks = [
            dm.Block(parent=None, name="block1"),
            dm.Block(parent=None, name="block2"),
        ]
        for block in blocks:
            block.store()

        ports = [
            dm.FlowPort(name='output', parent=blocks[0].Id),
            dm.FlowPort(name='input', parent=blocks[1].Id)
        ]
        for port in ports:
            port.store()

        connection = dm.FlowPortConnection(source=ports[0].Id, target=ports[1].Id)
        connection.store()

        for o in blocks + ports + [connection]:
            o2 = type(o).retrieve(o.Id)
            for f in fields(o):
                assert getattr(o, f.name) == getattr(o2, f.name)

if __name__ == '__main__':
    run_tests()