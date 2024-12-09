from posthog.utils import clean

from test_frame import prepare, test, run_tests, cleanup
import requests
import json
import integration_context as ic
from typing import Dict, Optional, Any

import build.public.block_programming_client as client
import build.block_programming_data as server_data
import sqlite3

from browser import ajax

class IntegrationContext(ic.IntegrationContext):
    def __init__(self, url):
        self.url = url
        ajax.DO_NOT_SIMULATE = True
        ajax.server_base = f'http://{url}'
        self.load_explorer_data()
        super().__init__(client, server_data)

    def load_explorer_data(self):
        data = requests.get(f'http://{self.url}/data/hierarchy')
        assert data.status_code == 200
        self.explorer_data = json.loads(data.text)
        pass

    def id_from_path(self, path) -> Dict:
        parts = path.split('/')
        parent_id = None
        result = None
        for p in parts:
            result = [o for o in self.explorer_data if o.get('name') == p and o['parent'] == parent_id]
            if len(result) == 0:
                raise RuntimeError(f"Could not find name {p} as child of {parent_id}")
            if len(result) > 1:
                raise RuntimeError(f"There are multiple objects called {p} as child of {parent_id}")
            parent_id = result[0]['Id']
        return result[0]['Id']

    def expect_request(self, *args, **kwargs):
        # In this context, we do not check the exact requests that were made.
        pass
    def check_expected_response(self):
        # In this context, we do not check the exact requests that were made.
        pass


test_diagram_name = 'integration_test_program'
def delete_test_diagram():
    dbfile = 'build/data/diagrams.sqlite3'
    db = sqlite3.connect(dbfile)
    cur = db.cursor()
    diagrams = cur.execute(f'SELECT Id FROM _entity WHERE parent == 2 AND json_extract(details, "$.name")="{test_diagram_name}";')
    for data in diagrams:
        cur.execute(f'DELETE FROM _representation WHERE diagram == {data[0]};')
        cur.execute(f'DELETE FROM _entity WHERE Id == {data[0]};')
    db.commit()

@prepare
def prepare_integration_checks():

    context = IntegrationContext('localhost:5101')

    delete_test_diagram()

    @cleanup
    def clean_db():
        delete_test_diagram()


    @test
    def check_MCU_placement():
        # Create a new diagram and open it
        context.explorer.create_block(
            2,
            server_data.ProgramDefinition,
            name=test_diagram_name
        )
        context.load_explorer_data()
        did = context.id_from_path('Programs/integration_test_program')
        print("Created diagram with ID", did)

        # Double-clicking a diagram opens it.
        context.explorer.dblclick_element(did)

        # Drag a F446 block onto a diagram.
        context.explorer.drag_to_diagram(context.id_from_path('Library/stdlib/Micro Controllers/STM32F446R(C-E)Tx/io_pins'),
                                         server_data.BlockDefinition)
        assert len(context.diagrams.blocks()) == 1
        assert len(context.diagrams.blocks()[0].children) == 64

    @test
    def connect_ioconfig_ports():
        """ Test whether io configuration ports can be connected. """


if __name__ == '__main__':
    run_tests()