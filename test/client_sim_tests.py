"""
Tests where the Brython client is run against a simulated Brython - browser.
"""


import os
import subprocess
from test_frame import prepare, test, run_tests
from dataclasses import fields, asdict
from property_editor import longstr

def generate_tool():
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run("../diagram_tool_generator/generate_tool.py sysml_spec.py", shell=True)
    if not os.path.exists('public/src'):
        os.symlink(os.path.abspath('../public/src'), 'public/src')


# Generate all the components of the tool.
generate_tool()


@prepare
def test_diagram_api():
    from rest_api import DiagramApi, ExplorerApi
    import public.sysml_client as client
    from browser.ajax import add_expected_response, remove_expected_reponse, Response, expected_responses

    expo_api = ExplorerApi(client.allowed_children, client.explorer_classes)
    api = DiagramApi(1, client.explorer_classes, client.representation_classes, expo_api)

    @test
    def create_totally_new():
        for element_nr, (name, cls) in enumerate(client.explorer_classes.items()):
            if not (repr_cls := client.representation_lookup.get(name, None)):
                continue
            print(f"Testing class {element_nr}: {name}")
            custom_fields = [f for f in fields(cls) if f.name not in ['Id', 'parent', 'order', 'children']]
            d = {}
            for i, f in enumerate(custom_fields):
                if f.type in [str, longstr]:
                    d[f.name] = f.name
                elif f.type in [int, float]:
                    d[f.name] = i
                else:
                    pass
            # Expect two REST calls: one for the model item, one for the representation.
            add_expected_response(f'/data/{name}', 'post', Response(201, json={'Id': element_nr}))
            if repr_cls.repr_category() == 'block':
                url = '/data/_BlockRepresentation'
                d.update(x=100, y=100, width=120, height=64)
            elif repr_cls.repr_category() == 'relationship':
                url = '/data/_RelationshipRepresentation'
                d.update(start=client.Block(Id=1), finish=client.Block(Id=2), waypoints=[])
            add_expected_response(url, 'post', Response(201, json={'Id': 1}))

            # Create the new object and offer it to the API
            new_item = repr_cls(**d)
            api.add_element(new_item)
            if repr_cls.repr_category() == 'block':
                assert new_item.Id == 1 and new_item.block == element_nr
            elif repr_cls.repr_category() == 'relationship':
                assert new_item.Id == 1 and new_item.relationship == element_nr

            # Check the two REST calls were made
            assert len(expected_responses) == 0


@prepare
def simulated_client_tests():

    import public.sysml_client as client

    # Set the context for the diagram editor. Normally this is in the HTML file.
    from browser import document as d
    from browser import html
    d <= html.DIV(id='explorer')
    d <= html.DIV(id='canvas')
    d <= html.DIV(id='details')



run_tests()