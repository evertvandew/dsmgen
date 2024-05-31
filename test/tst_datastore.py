
import json
from test_frame import prepare, test, run_tests
from data_store import DataConfiguration, DataStore, Collection, ExtendibleJsonEncoder, ReprCategory, UndoableDataStore, \
    CompoundAction
import generate_project     # Ensures the client is built up to date
from unittest.mock import Mock
from build import sysml_data as sm
from modeled_shape import ModeledShapeAndPorts, ModeledRelationship, Port

@prepare
def data_store_tests():
    from browser.ajax import (add_expected_response, Response,
                              clear_expected_response, check_expected_response)
    import public.sysml_client as client

    config = DataConfiguration(
        hierarchy_elements=client.explorer_classes,
        block_entities=client.block_entities,
        relation_entities=client.relation_classes,
        port_entities=client.port_classes,
        base_url='/data'
    )


    def check_request_data(url, method, kwargs):
        if method.lower() not in ['post', 'put']:
            # Don't know how to check 'get' or 'delete'.
            return
        # Check the request data can be parsed into the right class
        entity_name = url.split('/')[2]
        # This is a dataclass
        cls = sm.__dict__[entity_name]
        jdata = json.loads(kwargs['data'])
        jdata = {k: v for k, v in jdata.items() if k not in ['children', '__classname__']}
        _instance = cls(**jdata)
        # If the thing can be instantiated, all is well.

    @test
    def test_get_hierarchy():
        clear_expected_response()
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
             {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": None,
              "__classname__": "StructuralModel"}, {"order": 0, "Id": 3, "parent": 2, "name": "test",
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
        clear_expected_response()
        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=[{"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {"color": "yellow"}, "category": ReprCategory.block,
                   "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1", "description": "This is a test block",
                               "__classname__": "Block"}},
                  {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 345.0, "z": 0.0, "width": 64.0, "height": 40.0,
                   "styling": {}, "category": ReprCategory.block, "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                               "__classname__": "Block"}},
                  {"Id": 3, "diagram": 3, "block": 7, "x": 101.0, "y": 360.0, "z": 0.0, "width": 110.0, "height": 65.0,
                   "styling": {"bordercolor": "#000000", "bordersize": "2", "blockcolor": "#fffbd6", "fold_size": "10",
                               "font": "Arial", "fontsize": "16", "textcolor": "#000000", "xmargin": 2, "ymargin": 2,
                               "halign": 11, "valign": 2}, "category": ReprCategory.block,
                   "__classname__": "_BlockRepresentation",
                   "_entity": {"order": 0, "Id": 7, "description": "Dit is een commentaar", "parent": 3,
                               "__classname__": "Note"}},
                  {"Id": 1, "diagram": 3, "relationship": 1, "source_repr_id": 1, "target_repr_id": 2, "routing": "[]",
                   "z": 0.0, "styling": {}, "__classname__": "_RelationshipRepresentation", "rel_cls": "BlockReferenceRepresentation",
                   "_entity": {"Id": 1, "stereotype": 1, "source": 4, "target": 5, "source_multiplicity": 1,
                               "target_multiplicity": 1, "__classname__": "BlockReference"}},
                  {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation", "category": ReprCategory.port,
                   "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}}
                  ]))

        ds = DataStore(config)
        ok = False
        def ondata(result):
            nonlocal ok
            # Check the overall structure, and some elements
            assert len(result) == 4
            for i, name in enumerate(['Test1', 'Test2']):
                assert result[i].model_entity.name == name
            for i, cls in enumerate([client.Block, client.Block, client.Note,
                                     client.BlockReference]):
                assert isinstance(result[i].model_entity, cls), f"i={i}, expected={cls.__name__} -- actual={result[i]}"
            b1 = result[0]
            assert b1.model_entity.name == 'Test1'
            assert b1.model_entity.description == 'This is a test block'
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
        clear_expected_response()
        ds = DataStore(config)
        item = client.Block(name='Test1', description='This is a test block')
        ok = False
        def check_request(url, method, kwargs):
            nonlocal ok
            assert json.loads(kwargs['data']) == {"Id": 0, "order": 0, "parent": None, "name": "Test1", "description": "This is a test block", "__classname__": "Block"}
            ok = True
            return Response(201, json={'Id': 123})

        add_expected_response('/data/Block', 'post', get_response=check_request)
        ds.add_complex(item)
        assert item.Id == 123
        assert ok
        assert ds.shadow_copy[Collection.block][123] == item

    @test
    def add_repr_new_model():
        clear_expected_response()
        ds = DataStore(config)
        model = client.Block(name="Test1", description="This is a test block")
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={}, diagram=456)
        def check_request_model(url, method, kwargs):
            assert json.loads(kwargs['data']) == {"Id": 0, "parent": 456, "name": "Test1", "description": "This is a test block", "order": 0, "__classname__": "Block"}
            return Response(201, json={'Id': 123})

        def check_request_repr(url, method, kwargs):
            assert json.loads(kwargs['data']) == {"Id": 0, "order": 0, "category": 2, "diagram": 456, "block": 123, "parent": None, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "__classname__": "ModeledShapeAndPorts"}
            return Response(201, json={'Id': 121})

        add_expected_response('/data/Block', 'post', get_response=check_request_model)
        add_expected_response('/data/_BlockRepresentation', 'post', get_response=check_request_repr)
        ds.add_complex(item)
        assert item.block == 123
        assert item.Id == 121
        assert 123 in ds.shadow_copy[Collection.block]
        assert 121 in ds.shadow_copy[Collection.block_repr]
        assert ds.shadow_copy[Collection.block_repr][121] == item
        assert ds.shadow_copy[Collection.block][123].parent == 456
        check_expected_response()

    @test
    def add_repr_new_repr():
        clear_expected_response()
        ds = DataStore(config)
        a = client.Block(Id=101)
        b = client.Block(Id=102)
        item = ModeledRelationship(
            model_entity=client.BlockReference(
                stereotype=2,
                source=a,
                target=b
            ),
            diagram=456,
            start=ModeledShapeAndPorts(Id=1, model_entity=a),
            finish=ModeledShapeAndPorts(Id=2, model_entity=b),
            waypoints=[]
        )

        def check_request_model(url, method, kwargs):
            data = json.loads(kwargs['data'])
            assert data["stereotype"] == 2
            assert data["source"] == 101
            assert data["target"] == 102
            assert data["__classname__"] == "BlockReference"
            return Response(201, json={'Id': 123})

        def check_request_repr(url, method, kwargs):
            assert json.loads(kwargs['data']) == {'Id': 0, "diagram": 456, "relationship": 123, "source_repr_id": 1, "target_repr_id": 2, "routing": "[]", "z": 0.0, "styling": {}, '__classname__': 'ModeledRelationship'}
            return Response(201, json={'Id': 121})

        add_expected_response('/data/BlockReference', 'post', get_response=check_request_model)
        add_expected_response('/data/_RelationshipRepresentation', 'post', get_response=check_request_repr)
        ds.add_complex(item)
        assert item.relationship == 123
        assert item.Id == 121
        assert 123 in ds.shadow_copy[Collection.relation]
        assert 121 in ds.shadow_copy[Collection.relation_repr]
        check_expected_response()

    @test
    def add_repr_existing_model():
        clear_expected_response()
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        ds.update_cache(model)
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={}, diagram=456)
        def check_request_repr(url, method, kwargs):
            details = json.loads(kwargs['data'])
            expected = dict(Id=0, diagram=456, block=123, parent=None, x=100, y=150, z=0.0, width=64, height=40,
                            styling={}, __classname__='ModeledShapeAndPorts')
            for k in expected.keys():
                assert details[k] == expected[k], f"Values not equal for key {k}: {details[k]} != {expected[k]}"
            #assert kwargs['data'] == '''{"diagram": 456, "block": 123, "parent": null, "x": 100, "y": 150, "z": 0.0, "width": 64, "height": 40, "styling": {}, "block_cls": "BlockRepresentation"}'''
            return Response(201, json={'Id': 121})

        add_expected_response('/data/_BlockRepresentation', 'post', get_response=check_request_repr)
        ds.add_complex(item)
        assert item.Id == 121
        assert 123 in ds.shadow_copy[Collection.block]
        assert 121 in ds.shadow_copy[Collection.block_repr]
        assert ds.shadow_copy[Collection.block_repr][121] == item
        check_expected_response()

    @test
    def delete_block():
        clear_expected_response()
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block')
        ds.update_cache(model)
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={}, diagram=456,
                                    Id=121)
        ds.update_cache(item)
        add_expected_response('/data/_BlockRepresentation/121', 'delete', Response(204))
        ds.delete(item)
        assert not ds.shadow_copy[Collection.block_repr]
        add_expected_response('/data/Block/123', 'delete', Response(204))
        ds.delete(model)
        assert not ds.shadow_copy[Collection.block]
        check_expected_response()

    @test
    def delete_relationship():
        clear_expected_response()
        ds = DataStore(config)
        model = client.BlockReference(Id=123)
        ds.update_cache(model)
        item = ModeledRelationship(model_entity=model, Id=121, start=1, finish=2, waypoints=[])
        ds.update_cache(item)
        add_expected_response('/data/_RelationshipRepresentation/121', 'delete', Response(204))
        ds.delete(item)
        assert not ds.shadow_copy[Collection.relation_repr]
        add_expected_response('/data/BlockReference/123', 'delete', Response(204))
        ds.delete(model)
        assert not ds.shadow_copy[Collection.relation]
        check_expected_response()

    @test
    def update_repr():
        clear_expected_response()
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block', parent=456)
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={},
                                    diagram=456, Id=121)
        ds.update_cache(model)
        ds.update_cache(item)

        # Check the update is filtered out
        ds.update(item)
        check_expected_response()

        # Update the representation and check there is one and only one msg sent
        item.x = 250
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        check_expected_response()
        # Check the cache is also updated.
        assert ds.shadow_copy[Collection.block_repr][121] == item
        assert id(ds.shadow_copy[Collection.block_repr][121]) != id(item), "The shadow_copy must store a copy of the submitted object"

        # Update the model
        item.model_entity.name = 'Test123'
        add_expected_response('/data/Block/123', 'post', Response(201))
        ds.update(item)
        ds.update(item)
        check_expected_response()
        # Check the shadow_copy is also updated.
        assert ds.shadow_copy[Collection.block][123].name == item.model_entity.name
        assert isinstance(ds.shadow_copy[Collection.block][123], client.Block)

        # Update both representation and model
        item.model_entity.name = 'More Testing'
        item.y = 399
        add_expected_response('/data/Block/123', 'post', Response(201))
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)
        check_expected_response()

    @test
    def test_ports():
        clear_expected_response()
        # Test adding, updating, loading and deleting ports.
        # First create the block and model they belong to.
        # Ports are never created without a pre-existing block.
        ds = DataStore(config)
        model = client.Block(Id=123, name='Test1', description='This is a test block', parent=456)
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={}, diagram=456,
                                    Id=121)
        ds.update_cache(model)
        ds.update_cache(item)

        # Now add a port and try to save it.
        p1 = Port(model_entity=client.FlowPort(parent=model.Id), diagram=item.diagram, parent=item.Id)
        add_expected_response('/data/FlowPort', 'post', Response(201, json={'Id': 155}),
                              check_request=check_request_data)
        add_expected_response('/data/_BlockRepresentation', 'post', Response(201, json={'Id': 65}),
                              check_request=check_request_data)
        ds.add_complex(p1)
        # Expect the most important fields to be set by the datastore
        assert p1.block == 155
        assert p1.parent == 121
        assert p1.diagram == 456
        # Expect a new Port to be created as well as its representation.
        assert 155 in ds.shadow_copy[Collection.block]
        assert 65 in ds.shadow_copy[Collection.block_repr]
        assert item.ports == [p1]
        assert model.ports == [p1.model_entity]
        check_expected_response()

        # Check the object is stable
        ds.update(item)
        check_expected_response()

        # Update the representation of the port
        p1.styling = {'color': 'yellow'}
        add_expected_response('/data/_BlockRepresentation/65', 'post', Response(201))
        ds.update(p1)
        check_expected_response()
        assert ds.shadow_copy[Collection.block_repr][65].styling == {'color': 'yellow'}

        # Update the model part of the port
        p1.model_entity.name = 'Output'
        add_expected_response('/data/FlowPort/155', 'post', Response(201))
        ds.update(p1)
        check_expected_response()
        assert ds.shadow_copy[Collection.block][155].name == 'Output'

        # Now delete the port
        add_expected_response('/data/FlowPort/155', 'delete', Response(204))
        add_expected_response('/data/_BlockRepresentation/65', 'delete', Response(204))
        ds.delete(p1.model_entity)
        assert 65 not in ds.shadow_copy[Collection.block_repr]
        assert 155 not in ds.shadow_copy[Collection.block]
        check_expected_response()

    @test
    def test_undo_redo():
        clear_expected_response()
        # Test adding, updating, loading and deleting ports.
        # First create the block and model they belong to.
        # Ports are never created without a pre-existing block.
        ds = UndoableDataStore(config)

        # Add a new representation + model
        model = client.Block(name='Test1', description='This is a test block', parent=456)
        item = ModeledShapeAndPorts(model_entity=model, x=100, y=150, width=64, height=40, styling={}, diagram=456)
        add_expected_response('/data/Block', 'post', Response(201, json={'Id': 123}))
        add_expected_response('/data/_BlockRepresentation', 'post', Response(201, json={'Id': 121}))
        ds.add_complex(item)

        # Update the representation and model
        item.x = 200
        item.model_entity.name = 'This is not a test'
        add_expected_response('/data/Block/123', 'post', Response(201))
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.update(item)

        # Delete the representation
        add_expected_response('/data/_BlockRepresentation/121', 'delete', Response(204))
        ds.delete(item)
        # Check the item is truly deleted, but not the model item
        assert ds.get_live_instance(item) is None
        assert ds.get_shadow_copy(item) is None
        assert ds.get_live_instance(item.model_entity) is not None
        assert ds.get_shadow_copy(item.model_entity) is not None


        # The undo stack should have three elements, two of which are compounded actions.
        assert len(ds.undo_queue) == 3
        assert len([a for a in ds.undo_queue if isinstance(a, CompoundAction)]) == 2

        # Undo the delete
        add_expected_response('/data/_BlockRepresentation', 'post', Response(201, json={'Id': 121}))
        ds.undo_one_action()
        assert len(ds.undo_queue) == 2
        assert ds.get_live_instance(item) is item
        assert ds.get_shadow_copy(item) is not None

        # Undo the update
        add_expected_response('/data/Block/123', 'post', Response(201))
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.undo_one_action()
        assert item.x == 100 and item.model_entity.name=="Test1"
        assert len(ds.undo_queue) == 1

        # Undo the add
        add_expected_response('/data/Block/123', 'delete', Response(204))
        add_expected_response('/data/_BlockRepresentation/121', 'delete', Response(204))
        ds.undo_one_action()
        assert ds.get_live_instance(item) is None
        assert ds.get_shadow_copy(item) is None
        assert ds.get_live_instance(item.model_entity) is None
        assert ds.get_shadow_copy(item.model_entity) is None


        # The undo stack should be empty, but he redo stack should have three actions.
        assert len(ds.undo_queue) == 0
        assert len(ds.redo_queue) == 3

        # Redo the add
        add_expected_response('/data/Block', 'post', Response(201, json={'Id': 123}))
        add_expected_response('/data/_BlockRepresentation', 'post', Response(201, json={'Id': 121}))
        ds.redo_one_action()
        assert ds.get_live_instance(item) is item
        assert ds.get_shadow_copy(item) is not None
        assert ds.get_live_instance(item.model_entity) is item.model_entity
        assert ds.get_shadow_copy(item.model_entity) is not None

        # Redo the update
        add_expected_response('/data/Block/123', 'post', Response(201))
        add_expected_response('/data/_BlockRepresentation/121', 'post', Response(201))
        ds.redo_one_action()
        assert item.x == 200 and item.model_entity.name=="This is not a test"

        # Redo the delete
        add_expected_response('/data/_BlockRepresentation/121', 'delete', Response(204))
        ds.redo_one_action()
        assert ds.get_live_instance(item) is None
        assert ds.get_shadow_copy(item) is None
        assert ds.get_live_instance(item.model_entity) is item.model_entity
        assert ds.get_shadow_copy(item.model_entity) is not None


if __name__ == '__main__':
    run_tests('*.test_ports')
    run_tests()
