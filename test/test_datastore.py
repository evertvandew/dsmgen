
import os, subprocess
from copy import deepcopy

import diagrams
from test_frame import prepare, test, run_tests
from data_store import DataConfiguration, DataStore, Collection
import generate_project     # Ensures the client is built up to date
from unittest.mock import Mock


@prepare
def data_store_tests():
    from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses
    import public.sysml_client as client

    config = DataConfiguration(
        hierarchy_elements=client.explorer_classes,
        block_entities=client.block_entities,
        relation_entities=client.relation_classes,
        port_entities=client.port_classes,
        block_representations=client.block_representations,
        relation_representations=client.relation_representations,
        port_representations=client.port_representations,
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
            json=[{"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {"color": "yellow"}, "block_cls": "BlockRepresentation",
                   "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1", "description": "This is a test block",
                               "__classname__": "Block"}},
                  {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 345.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {}, "block_cls": "BlockRepresentation", "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                               "__classname__": "Block"}},
                  {"Id": 3, "diagram": 3, "block": 7, "x": 101.0, "y": 360.0, "z": 0.0, "width": 110.0, "height": 65.0,
                   "styling": {"bordercolor": "#000000", "bordersize": "2", "blockcolor": "#fffbd6", "fold_size": "10",
                               "font": "Arial", "fontsize": "16", "textcolor": "#000000", "xmargin": 2, "ymargin": 2,
                               "halign": 11, "valign": 2}, "block_cls": "NoteRepresentation",
                   "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 7, "description": "Dit is een commentaar", "parent": 3,
                               "__classname__": "Note"}},
                  {"Id": 1, "diagram": 3, "relationship": 1, "source_repr_id": 1, "target_repr_id": 2, "routing": "[]",
                   "z": 0.0, "styling": {}, "rel_cls": "BlockReferenceRepresentation",
                   "_entity": {"Id": 1, "stereotype": 1, "source": 4, "target": 5, "source_multiplicity": 1,
                               "target_multiplicity": 1, "__classname__": "BlockReference"}},
                  {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation", "block_cls": "FlowPortRepresentation",
                   "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}}
                  ]))

        ds = DataStore(config)
        ok = False
        def ondata(result):
            nonlocal ok
            # Check the overall structure, and some elements
            assert len(result) == 4
            for i, name in enumerate(['Test1', 'Test2']):
                assert result[i].name == name
            for i, cls in enumerate([client.BlockRepresentation, client.BlockRepresentation, client.NoteRepresentation,
                                     client.BlockReferenceRepresentation]):
                assert isinstance(result[i], cls), f"i={i}, expected={cls.__name__} -- actual={result[i]}"
            b1 = result[0]
            assert b1.name == 'Test1'
            assert b1.description == 'This is a test block'
            assert b1.x == 401.0
            assert b1.y == 104.0
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
            assert kwargs['data'] == '''{"diagram": 456, "block": 123, "parent": 0, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "block_cls": "BlockRepresentation"}'''
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
        assert not unexpected_requests

    @test
    def add_repr_new_repr():
        ds = DataStore(config)
        item = client.BlockReferenceRepresentation(diagram=456, stereotype=2, start=Mock(Id=1, block=101), finish=Mock(Id=2, block=102), waypoints=[])

        def check_request_model(url, method, kwargs):
            assert kwargs['data'] == '{"Id": 0, "stereotype": 2, "source": 101, "target": 102, "source_multiplicity": 1, "target_multiplicity": 1, "__classname__": "BlockReference"}'
            return Response(201, json={'Id': 123})

        def check_request_repr(url, method, kwargs):
            assert kwargs['data'] == '{"diagram": 456, "relationship": 123, "source_repr_id": 1, "target_repr_id": 2, "routing": "[]", "z": 0.0, "styling": {}, "rel_cls": "BlockReferenceRepresentation"}'
            return Response(201, json={'Id': 121})

        add_expected_response('/data/BlockReference', 'post', get_response=check_request_model)
        add_expected_response('/data/_RelationshipRepresentation', 'post', get_response=check_request_repr)
        ds.add(item)
        assert item.relationship == 123
        assert item.Id == 121
        assert 123 in ds.cache[Collection.relation]
        assert 121 in ds.cache[Collection.relation_repr]
        assert len(expected_responses) == 0
        assert not unexpected_requests

    @test
    def add_repr_existing_model():
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        ds.cache[Collection.block][123] = model
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block')
        def check_request_repr(url, method, kwargs):
            assert kwargs['data'] == '''{"diagram": 456, "block": 123, "parent": 0, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "block_cls": "BlockRepresentation"}'''
            return Response(201, json={'Id': 121})

        add_expected_response('/data/_BlockRepresentation', 'post', get_response=check_request_repr)
        ds.add(item)
        assert item.Id == 121
        assert 123 in ds.cache[Collection.block]
        assert 121 in ds.cache[Collection.block_repr]
        assert ds.cache[Collection.block_repr][121] == item
        assert len(expected_responses) == 0
        assert not unexpected_requests

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
        model = client.Block(Id=123, name='Test1', description='This is a test block', parent=456)
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block', Id=121)
        ds.cache[Collection.block][123] = deepcopy(model)
        ds.cache[Collection.block_repr][121] = deepcopy(item)

        # Check the update is filtered out
        ds.update(item)
        assert len(expected_responses) == 0
        assert not unexpected_requests

        # Update the representation and check there is one and only one msg sent
        item.x = 250
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        assert len(expected_responses) == 0
        assert not unexpected_requests
        # Check the cache is also updated.
        assert ds.cache[Collection.block_repr][121] == item
        assert id(ds.cache[Collection.block_repr][121]) != id(item), "The cache must store a copy of the submitted object"

        # Update the model
        item.name = 'Test123'
        add_expected_response('/data/Block/123', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        assert len(expected_responses) == 0
        assert not unexpected_requests
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
        assert not unexpected_requests

    @test
    def test_ports():
        # Test adding, updating, loading and deleting ports.
        # First create the block and model they belong to.
        # Ports are never created without a pre-existing block.
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block', parent=456)
        item = client.BlockRepresentation(x=100, y=150, width=64, height=40, styling={}, diagram=456, block=123,
              name='Test1', description='This is a test block', Id=121)
        ds.cache[Collection.block][123] = deepcopy(model)
        ds.cache[Collection.block_repr][121] = deepcopy(item)

        # Now add a port and try to save it.
        p1 = client.FlowPortRepresentation()
        item.ports.append(p1)
        add_expected_response('/data/FlowPort', 'post', Response(201, json={'Id': 155}))
        add_expected_response('/data/_BlockRepresentation', 'post', Response(201, json={'Id': 65}))
        ds.update(item)
        # Expect the most important fields to be set by the datastore
        assert p1.block == 155
        assert p1.parent == 121
        assert p1.diagram == 456
        # Expect a new Port to be created as well as its representation.
        assert 155 in ds.cache[Collection.block]
        assert 65 in ds.cache[Collection.block_repr]
        assert p1.block == 155
        assert p1.parent == 121
        assert len(ds.cache[Collection.block_repr][121].ports) == 1
        for k in ['diagram', 'parent', 'block', 'name', 'orientation']:
            assert getattr(ds.cache[Collection.block_repr][121].ports[0], k) == getattr(p1, k)
        assert not unexpected_requests
        assert len(expected_responses) == 0

        # Check the object is stable
        ds.update(item)
        assert not unexpected_requests

        # Update the representation of the port
        p1.orientation = diagrams.BlockOrientations.TOP
        add_expected_response('/data/_BlockRepresentation/65', 'post', Response(201))
        ds.update(item)
        assert not unexpected_requests
        assert len(expected_responses) == 0
        assert ds.cache[Collection.block_repr][65].orientation == diagrams.BlockOrientations.TOP

        # Update the model part of the port
        p1.name = 'Output'
        add_expected_response('/data/FlowPort/155', 'post', Response(201))
        ds.update(item)
        assert not unexpected_requests
        assert len(expected_responses) == 0
        assert ds.cache[Collection.block][155].name == 'Output'

        # Now delete the port
        item.ports = []
        add_expected_response('/data/FlowPort/155', 'delete', Response(204))
        add_expected_response('/data/_BlockRepresentation/65', 'delete', Response(204))
        ds.update(item)
        assert not unexpected_requests
        assert len(expected_responses) == 0
        assert 65 not in ds.cache[Collection.block_repr]
        assert 155 not in ds.cache[Collection.block]

if __name__ == '__main__':
    run_tests()
