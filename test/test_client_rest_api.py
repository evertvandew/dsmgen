import enum
import os
import subprocess
import json
from test_frame import prepare, test, run_tests
from dataclasses import fields
from property_editor import longstr
from inspect import signature
from typing import List
from shapes import Shape, Relationship, Point, HIDDEN
import generate_project     # Ensures the client is built up to date

@prepare
def test_diagram_api():
    from rest_api import DiagramApi, ExplorerApi
    import public.sysml_client as client
    from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses

    expo_api = ExplorerApi(client.allowed_children, client.explorer_classes)
    api = DiagramApi(1, client.explorer_classes, client.representation_classes, expo_api)

    def representation_factor(cls, repr_id=None, model_id=None):
        model_cls = cls.logical_class
        custom_fields = [f for f in fields(model_cls) if f.name not in ['Id', 'parent', 'order', 'children']]
        d = {}
        for i, f in enumerate(custom_fields):
            if f.type in [str, longstr]:
                d[f.name] = f.name
            elif f.type in [int, float]:
                d[f.name] = i
            else:
                pass
        if cls.repr_category() == 'block':
            d.update(x=100, y=100, width=120, height=64)
            if model_id:
                d['block'] = model_id
        elif cls.repr_category() == 'relationship':
            d.update(start=client.Block(Id=1), finish=client.Block(Id=2), waypoints=[])
            if model_id:
                d['relationship'] = model_id
        if repr_id:
            d['Id'] = repr_id
        new_item = cls(**d)
        return new_item

    def get_base_url(item):
        return {
            'block': '/data/_BlockRepresentation',
            'relationship': '/data/_RelationshipRepresentation'
        }[item.repr_category()]

    def get_specific_url(item):
        return f'{get_base_url(item)}/{item.Id}'


    @test
    def test_dirty():
        # Create a Representation object and check the dirty checking is initiated
        item = client.BlockRepresentation(x=100, y=100, width=120, height=64)
        assert hasattr(item, '_dirty')
        assert not item._dirty
        assert not item.is_dirty()
        item.name = 'Test'
        assert item.is_dirty()
        assert 'name' in item._dirty
        item.set_clean()
        assert not item.is_dirty()

    @test
    def create_totally_new():
        for element_nr, (name, cls) in enumerate(client.explorer_classes.items()):
            if not (repr_cls := client.representation_lookup.get(name, None)):
                continue
            print(f"Testing class {element_nr}: {name}")
            sig = signature(create_new_representation)
            new_item = representation_factor(repr_cls)
            # Expect two REST calls: one for the model item, one for the representation.
            add_expected_response(f'/data/{name}', 'post', Response(201, json={'Id': element_nr}))
            add_expected_response(get_base_url(new_item), 'post', Response(201, json={'Id': 1}))

            # Create the new object and offer it to the API
            api.add_element(new_item)
            if repr_cls.repr_category() == 'block':
                assert new_item.Id == 1 and new_item.block == element_nr
            elif repr_cls.repr_category() == 'relationship':
                assert new_item.Id == 1 and new_item.relationship == element_nr

            # Check the two REST calls were made
            assert len(expected_responses) == 0

    @test
    def create_new_representation():
        # Create new representations referring to existing blocks and relationships.
        # They won't actually exist, just that their reference is valid.
        for element_nr, repr_cls in enumerate(client.RelationshipReprSerializer.__subclasses__() +
                                              client.EntityReprSerializer.__subclasses__()):
            name = repr_cls.__name__
            print(f"Testing class {element_nr}: {name}")
            new_item = representation_factor(repr_cls, model_id=123+element_nr)
            # Expect one REST calls: one for the model item, one for the representation.
            add_expected_response(get_base_url(new_item), 'post', Response(201, json={'Id': 1}))

            # Create the new object and offer it to the API
            api.add_element(new_item)
            if repr_cls.repr_category() == 'block':
                assert new_item.Id == 1 and new_item.block == 123+element_nr
            elif repr_cls.repr_category() == 'relationship':
                assert new_item.Id == 1 and new_item.relationship == 123+element_nr

            # Check the expected REST calls were made
            assert len(expected_responses) == 0
            assert unexpected_requests == 0

    @test
    def update_representation():
        for element_nr, repr_cls in enumerate(client.RelationshipReprSerializer.__subclasses__() +
                                              client.EntityReprSerializer.__subclasses__()):
            new_item = representation_factor(repr_cls, model_id=123+element_nr, repr_id=5)
            # Insert a dummy model element in the explorer rest buffer
            if repr_cls.repr_category == 'block':
                api.blocks[123+element_nr] = repr_cls.logical_class()
                keys = Shape.__annotations__
            else:
                api.relations[123+element_nr] = repr_cls.logical_class()
                keys = Relationship.__annotations__

            # We check if an update to each attribute leads to an update to the REST interface
            for key, update_type in keys.items():
                if key in ['id', 'shape_type', 'start', 'finish']:
                    continue
                assert not new_item.is_dirty()
                if update_type == float:
                    setattr(new_item, key, getattr(new_item, key) + 1.0)
                elif update_type == Shape:
                    continue
                elif key == 'styling':
                    style = list(new_item.getDefaultStyle().keys())[0]
                    new_item.styling = {style: '12342'}
                elif update_type == List[Point]:
                    setattr(new_item, key, [Point(100, 100)])
                else:
                    raise RuntimeError(f"Forgot to add support for element {key}: {update_type}")


                add_expected_response(get_specific_url(new_item), 'post', Response(202))
                api.update_element(new_item)
                assert len(expected_responses) == 0
                assert unexpected_requests == 0

    @test
    def update_model():
        for element_nr, repr_cls in enumerate(client.RelationshipReprSerializer.__subclasses__() +
                                              client.EntityReprSerializer.__subclasses__()):
            name = repr_cls.__name__
            new_item = representation_factor(repr_cls, model_id=123+element_nr, repr_id=5)
            # Insert a dummy model element in the explorer rest buffer
            expo_api.records[123+element_nr] = repr_cls.logical_class(Id=123+element_nr)
            # Check that changes in the representation bit produce a single REST call
            keys = repr_cls.__annotations__   # Does not include the inherited fields.

            # We check if an update to each attribute leads to an update to the REST interface
            for key, update_type in keys.items():
                if key in ['Id', 'diagram', 'relationship', 'block', 'source', 'target']:
                    continue
                print('Updating', key)
                assert not new_item.is_dirty()
                if update_type == float:
                    setattr(new_item, key, getattr(new_item, key) + 1.0)
                if update_type == int:
                    setattr(new_item, key, getattr(new_item, key) + 1)
                elif update_type == Shape:
                    continue
                elif key == 'styling':
                    style = list(new_item.getDefaultStyle().keys())[0]
                    new_item.styling = {style: '12342'}
                elif update_type == List[Point]:
                    setattr(new_item, key, [Point(100, 100)])
                elif update_type == HIDDEN:
                    setattr(new_item, key, getattr(new_item, key) + 10)
                elif update_type == str or update_type == client.longstr:
                    setattr(new_item, key, getattr(new_item, key) + 'ha')
                elif isinstance(update_type, enum.EnumType):
                    options = list(update_type)
                    setattr(new_item, key, options[getattr(new_item, key) + 1])
                elif isinstance(update_type, list):
                    if all(issubclass(c, client.CleanMonitor) for c in update_type):
                        # This is to hold a reference to another object.
                        setattr(new_item, key, 111)
                else:
                    raise RuntimeError(f"Forgot to add support for element {key}: {update_type}")

                if issubclass(repr_cls, client.RelationshipReprSerializer):
                    url = f'/data/{repr_cls.logical_class.__name__}/{new_item.relationship}'
                else:
                    url = f'/data/{repr_cls.logical_class.__name__}/{new_item.block}'

                add_expected_response(url, 'post', Response(202))
                api.update_element(new_item)
                assert len(expected_responses) == 0
                assert unexpected_requests == 0

    @test
    def extract_model_entity():
        # Check that when a model item is extracted from a representation, it doesn't overwrite
        # details that are not stored in the representation.
        repr = client.BlockRepresentation(
            x=100, y=100, width=64, height=40,
            diagram=9, block=5, Id=3, styling={},
            name="Legolas", description="Elf that shoots well"
        )
        model_details = dict(
            Id=5, name="Legolas", description="Elf that shoots well", parent=1
        )
        model = client.Block(**model_details)
        updated = repr.extract_model(model)
        assert not updated.is_dirty()
        for k, v in model_details.items():
            assert getattr(updated, k) == v, f"A value was wrongly updated: {k}"

        # Now update a single element: the name
        repr.name = "Duilin"
        model_details['name'] = "Duilin"
        updated = repr.extract_model(model)
        assert updated.is_dirty()
        assert updated._dirty == {'name'}
        for k, v in model_details.items():
            assert getattr(updated, k) == v, f"A value was wrongly updated: {k}"

    @test
    def extract_model_relationship():
        # Check that when a model item is extracted from a representation, it doesn't overwrite
        # details that are not stored in the representation.
        model_details = dict(
            Id=5, stereotype=3, source=222, target=333, source_multiplicity=2, target_multiplicity=3
        )
        repr_details = dict(
            Id=6, id=923, z=0.0, styling={'color': 'yellow'}, waypoints=[(100,100), (200,100)], start=444, finish=555
        )
        ddict = model_details.copy()
        ddict.update(repr_details)
        repr = client.BlockReferenceRepresentation(**ddict)
        model = client.BlockReference(**model_details)
        updated = repr.extract_model(model)
        assert not updated.is_dirty()
        for k, v in model_details.items():
            assert getattr(updated, k) == v, f"A value was wrongly updated: {k}"

        # Now update a single model element: the stereotype
        repr.stereotype = 2
        model_details['stereotype'] = 2
        updated = repr.extract_model(model)
        assert updated.is_dirty()
        assert updated._dirty == set(['stereotype'])
        for k, v in model_details.items():
            assert getattr(updated, k) == v, f"A value was wrongly updated: {k}"

    @test
    def update_both_model_and_representation():
        # Run the test with a Block Representation
        repr = client.BlockRepresentation(x=100, y=100, width=120, height=64, name='Aristotle', block=123, Id=5)
        expo_api.records[123] = client.Block(Id=123, name='Aristotle')
        assert not repr.is_dirty()
        # Make two changes, one to the representation, one to the model itself.
        repr.x = 200
        repr.name = 'Archimedes'
        assert 'name' in repr.get_dirty() and 'x' in repr.get_dirty()
        # Test whether both items are updated
        add_expected_response('/data/Block/123', 'post', Response(202))
        add_expected_response('/data/_BlockRepresentation/5', 'post', Response(202))
        api.update_element(repr)
        assert len(expected_responses) == 0
        assert unexpected_requests == 0

    @test
    def delete_representation():
        # Delete is much less complex than adding or updating the data.
        example = client.BlockRepresentation(Id=1234, x=100, y=100, width=120, height=64)
        add_expected_response('/data/_BlockRepresentation/1234', 'delete', Response(204))
        api.delete_element(example)
        assert len(expected_responses) == 0

    @test
    def load_data():
        js = [{"Id": 1, "diagram": 3, "block": 4, "x": 300.0, "y": 300.0, "z": 0.0, "width": 64.0, "height": 40.0, "styling": {}, "block_cls": "BlockRepresentation", "__classname__": "_BlockRepresentation", "_entity": {"order": 0, "Id": 4, "parent": 3, "name": "Test1", "description": "A test object", "__classname__": "Block"}}
             ]
        api = DiagramApi(3, client.explorer_classes, client.representation_classes)
        response = None
        def callback(data):
            nonlocal response
            response = data

        add_expected_response('/data/diagram_contents/3', 'get', Response(200, json=js))

        api.get_elements_async(callback)
        assert response
        for k, v in dict(
            Id=1,
            diagram=3,
            block=4,
            x=300.0,
            y=300.0,
            z=0.0,
            width=64.0,
            height=40.0,
            styling= {},
            name="Test1",
            description="A test object"
        ).items():
            assert getattr(response[0], k) == v

run_tests()