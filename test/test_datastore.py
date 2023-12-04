
import os, subprocess
from copy import copy
from test_frame import prepare, test, run_tests
from data_store import DataConfiguration, DataStore, Collection

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
def data_store_tests():
    from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses
    import public.sysml_client as client

    config = DataConfiguration(
        hierarchy_elements=client.explorer_classes,
        block_entities=client.block_entities,
        relation_entities=client.relation_classes,
        block_representations=client.block_representations,
        relation_representations=client.relation_representations,
        base_url='/data'
    )

    @test
    def test_get_hierarchy():
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
             {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": None,
              "__classname__": "StructuralModel"}, {"order": 0, "Id": 3, "entities": [], "parent": 2, "name": "test",
                                                    "__classname__": "BlockDefinitionDiagram"},
             {"order": 0, "Id": 4, "parent": None, "name": "Test1", "description": "", "__classname__": "Block"},
             {"order": 0, "Id": 5, "parent": 2, "name": "Test Block", "description": "", "__classname__": "Block"},
             {"order": 0, "Id": 6, "parent": 2, "name": "Another Testblock", "description": "", "__classname__": "Block"}]
        ))

        ds = DataStore(config)

        def ondata(result):
            # Check the overall structure, and some elements
            assert len(result) == 3
            for i, name in enumerate(['Functional Model', 'Structural Model', 'Test1']):
                assert result[i].name == name
            for i, cls in enumerate([client.FunctionalModel, client.StructuralModel, client.Block]):
                assert isinstance(result[i], cls)
            assert len(result[1].children) == 3
            for i, name in enumerate(['test', 'Test Block', 'Another Testblock']):
                assert result[1].children[i].name == name
            for i, cls in enumerate([client.BlockDefinitionDiagram, client.Block, client.Block]):
                assert isinstance(result[1].children[i], cls)

        ds.get_hierarchy(ondata)

    @test
    def test_get_diagram():
        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=[{"Id": 1, "diagram": 3, "block": 4, "x": 167.0, "y": 140.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {"color": "yellow"}, "block_cls": "BlockRepresentation",
                   "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1", "description": "This is a test block",
                               "__classname__": "Block"}},
                  {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 382.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {}, "block_cls": "BlockRepresentation", "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                               "__classname__": "Block"}}]
        ))

        ds = DataStore(config)
        ok = False
        def ondata(result):
            nonlocal ok
            # Check the overall structure, and some elements
            assert len(result) == 2
            for i, name in enumerate(['Test1', 'Test2']):
                assert result[i].name == name
            for i, cls in enumerate([client.BlockRepresentation, client.BlockRepresentation]):
                assert isinstance(result[i], cls)
            b1 = result[0]
            assert b1.name == 'Test1'
            assert b1.description == 'This is a test block'
            assert b1.x == 167.0
            assert b1.y == 140.0
            assert b1.width == 64.0
            assert b1.height == 40.0
            assert b1.styling == {"color": "yellow"}
            ok=True

        ds.get_diagram_data(3, ondata)
        assert ok

    @test
    def add_modelitem():
        ds = DataStore(config)
        item = client.Block(name='Test1', description='This is a test block')
        ok = False
        def check_request(url, method, kwargs):
            nonlocal ok
            assert kwargs['data'] == '''{"Id": 0, "parent": null, "name": "Test1", "description": "This is a test block", "order": 0, "children": [], "__classname__": "Block"}'''
            ok = True
            return Response(201, json={'Id': 123})

        add_expected_response('/data/Block', 'post', get_response=check_request)
        ds.add(item)
        assert item.Id == 123
        assert ok
        assert ds.cache[Collection.block][123] == item

    @test
    def add_repr_new_model():
        ds = DataStore(config)
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456,
              name='Test1', description='This is a test block')
        def check_request_model(url, method, kwargs):
            assert kwargs['data'] == '''{"Id": 0, "parent": 456, "name": "Test1", "description": "This is a test block", "order": 0, "children": [], "__classname__": "Block"}'''
            return Response(201, json={'Id': 123})

        def check_request_repr(url, method, kwargs):
            assert kwargs['data'] == '''{"diagram": 456, "block": 0, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "block_cls": "BlockRepresentation"}'''
            return Response(201, json={'Id': 121})

        add_expected_response('/data/Block', 'post', get_response=check_request_model)
        add_expected_response('/data/_BlockRepresentation', 'post', get_response=check_request_repr)
        ds.add(item)
        assert item.block == 123
        assert item.Id == 121
        assert 123 in ds.cache[Collection.block]
        assert 121 in ds.cache[Collection.block_repr]
        assert ds.cache[Collection.block_repr][121] == item
        assert ds.cache[Collection.block][123].parent == 456
        assert len(expected_responses) == 0
        assert unexpected_requests == 0

    @test
    def add_repr_existing_model():
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        ds.cache[Collection.block][123] = model
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block')
        def check_request_repr(url, method, kwargs):
            assert kwargs['data'] == '''{"diagram": 456, "block": 123, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "block_cls": "BlockRepresentation"}'''
            return Response(201, json={'Id': 121})

        add_expected_response('/data/_BlockRepresentation', 'post', get_response=check_request_repr)
        ds.add(item)
        assert item.Id == 121
        assert 123 in ds.cache[Collection.block]
        assert 121 in ds.cache[Collection.block_repr]
        assert ds.cache[Collection.block_repr][121] == item
        assert len(expected_responses) == 0
        assert unexpected_requests == 0

    @test
    def delete_block():
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        ds.cache[Collection.block][123] = model
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block', Id=121)
        ds.cache[Collection.block_repr][121] = item
        add_expected_response('/data/_BlockRepresentation/121', 'delete', Response(204))
        ds.delete(item)
        assert not ds.cache[Collection.block_repr]
        add_expected_response('/data/Block/123', 'delete', Response(204))
        ds.delete(model)
        assert not ds.cache[Collection.block]

    @test
    def delete_relationship():
        ds = DataStore(config)
        model = client.BlockReference(Id=123)
        ds.cache[Collection.relation][123] = model
        item = client.BlockReferenceRepresentation(Id=121, start=1, finish=2, waypoints=[])
        ds.cache[Collection.relation_repr][121] = item
        add_expected_response('/data/_RelationshipRepresentation/121', 'delete', Response(204))
        ds.delete(item)
        assert not ds.cache[Collection.relation_repr]
        add_expected_response('/data/BlockReference/123', 'delete', Response(204))
        ds.delete(model)
        assert not ds.cache[Collection.relation]

    @test
    def update_repr():
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block', Id=121)
        ds.cache[Collection.block][123] = copy(model)
        ds.cache[Collection.block_repr][121] = copy(item)

        # Check the update is filtered out
        ds.update(item)
        assert len(expected_responses) == 0
        assert unexpected_requests == 0

        # Update the representation and check there is one and only one msg sent
        item.x = 250
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        assert len(expected_responses) == 0
        assert unexpected_requests == 0
        # Check the cache is also updated.
        assert ds.cache[Collection.block_repr][121] == item
        assert id(ds.cache[Collection.block_repr][121]) != id(item), "The cache must store a copy of the submitted object"

        # Update the model
        item.name = 'Test123'
        add_expected_response('/data/Block/123', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        assert len(expected_responses) == 0
        assert unexpected_requests == 0
        # Check the cache is also updated.
        assert ds.cache[Collection.block][123].name == item.name
        assert isinstance(ds.cache[Collection.block][123], client.Block)

        # Update both representation and model
        item.name = 'More Testing'
        item.y = 399
        add_expected_response('/data/Block/123', 'post', Response(201))
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)
        assert len(expected_responses) == 0
        ds.update(item)
        assert len(expected_responses) == 0
        assert unexpected_requests == 0



if __name__ == '__main__':
    run_tests()
