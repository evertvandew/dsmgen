"""
Tests where the Brython client is run against a simulated Brython - browser.
"""
import enum
import os
import subprocess
import json
from test_frame import prepare, test, run_tests
from dataclasses import fields
from property_editor import longstr
from inspect import signature
from typing import List, Dict, Any
from shapes import Shape, Relationship, Point, HIDDEN
from browser import events
from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses
from unittest.mock import Mock, MagicMock
import diagrams
import explorer
from data_store import ExtendibleJsonEncoder, DataStore, DataConfiguration, Collection
from copy import deepcopy
import generate_project     # Ensures the client is built up to date
import public.sysml_client as client


def set_entity_ids(ids):
    def cb(entity):
        entity.Id = ids.pop(0)
        return entity
    return cb


def mk_ds():
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

    ds = DataStore(config)
    return ds


example_diagram = [
    {"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {"color": "yellow"}, "block_cls": "BlockRepresentation",
     "__classname__": "_BlockRepresentation",
     "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1",
                 "description": "This is a test block",
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
    {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation",
     "block_cls": "FlowPortRepresentation",
     "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}
     }
]


port2port = [
    {"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {"color": "yellow"}, "block_cls": "BlockRepresentation", "parent": None,
     "__classname__": "_BlockRepresentation",
     "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1",
                 "description": "This is a test block",
                 "__classname__": "Block"}},
    {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 345.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {}, "block_cls": "BlockRepresentation", "__classname__": "_BlockRepresentation", "parent": None,
     "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                 "__classname__": "Block"}},
    {"Id": 3, "diagram": 3, "block": 7, "x": 101.0, "y": 360.0, "z": 0.0, "width": 110.0, "height": 65.0,
     "styling": {"bordercolor": "#000000", "bordersize": "2", "blockcolor": "#fffbd6", "fold_size": "10",
                 "font": "Arial", "fontsize": "16", "textcolor": "#000000", "xmargin": 2, "ymargin": 2,
                 "halign": 11, "valign": 2}, "block_cls": "BlockRepresentation",
     "__classname__": "_BlockRepresentation", "parent": None,
     "_entity": {"order": 0, "Id": 7, "name": "Test 3", "description": "Dit is een commentaar", "parent": 2,
                 "__classname__": "Block"}},
    {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation",
     "block_cls": "FlowPortRepresentation",
     "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}
     },
    {"Id": 52, "diagram": 3, "block": 11, "parent": 3, "__classname__": "_BlockRepresentation",
     "block_cls": "FlowPortRepresentation",
     "_entity": {"Id": 10, "parent": 7, "__classname__": "FlowPort"}
     },
    {"Id": 1, "diagram": 3, "relationship": 1, "source_repr_id": 51, "target_repr_id": 52, "routing": "[]",
     "z": 0.0, "styling": {}, "rel_cls": "FlowPortConnectionRepresentation",
     "_entity": {"Id": 1, "stereotype": 1, "source": 10, "target": 11, "source_multiplicity": 1,
                 "target_multiplicity": 1, "__classname__": "FlowPortConnection"}},

]

@prepare
def simulated_diagram_tests():
    # Set the context for the diagram editor. Normally this is in the HTML file.
    from browser import document as d
    from browser import html
    d.clear()
    d <= html.DIV(id='explorer')
    d <= html.DIV(id='canvas')
    d <= html.DIV(id='details')

    def new_diagram(diagram_id, diagram_api):
        container = d['canvas']
        container.html = ''
        svg = html.SVG()
        svg.classList.add('diagram')
        container <= svg
        config = diagrams.DiagramConfiguration(
            client.representation_lookup,
            client.connections_from
        )
        diagram = diagrams.load_diagram(
            diagram_id,
            client.diagram_definitions['BlockDefinitionDiagram'],
            config,
            diagram_api,
            svg
        )
        return diagram, diagram_api

    @test
    def create_and_move_block():
        def create_and_move(instance):
            old_nr_children = len(diagram.children)
            diagram.addBlock(instance)
            assert len(diagram.children) == old_nr_children + 1

            # Simulate dragging the block
            block = diagram.children[old_nr_children]
            block.shape.dispatchEvent(events.MouseDown())
            block.shape.dispatchEvent(events.MouseMove(offsetX=200, offsetY=100))
            block.shape.dispatchEvent(events.MouseUp(offsetX=200, offsetY=100))
            assert block.x == 500
            assert block.y == 400

        # Do a normal block
        diagram, rest = new_diagram(1, MagicMock())
        create_and_move(client.BlockRepresentation(name='', x=300, y=300, height=64, width=100, block=1, Id=1))

        # Add a port label representation
        create_and_move(client.PortLabel(name='', x=300, y=300, height=64, width=100, block=1, Id=1))

        # Add a SubprogramDefinition
        create_and_move(client.SubProgramDefinitionRepresentation(name='', x=300, y=300, height=64, width=100, block=1, Id=1))

    @test
    def create_connect_blocks():
        # Connect two PortLabels: an input and an output.
        diagram, rest = new_diagram(1, MagicMock())
        input = client.PortLabel(name='Input', x=100, y=300, height=64, width=100, block=1, Id=1)
        output = client.PortLabel(name='Output', x=400, y=300, height=64, width=100, block=1, Id=1)
        input.logical_class = client.FlowPort
        output.logical_class = client.FlowPort
        diagram.addBlock(input)
        diagram.addBlock(output)
        diagram.changeFSM(diagrams.ConnectionEditor())
        input.shape.dispatchEvent(events.MouseDown())
        input.shape.dispatchEvent(events.MouseUp())
        output.shape.dispatchEvent(events.MouseDown())
        output.shape.dispatchEvent(events.MouseUp())
        assert len(diagram.connections) == 1
        conn = diagram.connections[0]
        assert type(conn).__name__ == 'FlowPortConnectionRepresentation'
        assert conn.start.id == 10
        assert conn.finish.id == 11


    @test
    def drag_and_drop():
        ds = mk_ds()
        add_expected_response('/data/diagram_contents/5', 'get', Response(201, json=[]))
        diagram, rest = new_diagram(5, ds)
        rest.add = set_entity_ids([400])
        instance = client.Block(name='One', parent=3, Id=123)
        restif = Mock()
        restif.get_hierarchy = Mock(side_effect=lambda cb: cb([instance]))
        explorer.make_explorer(d['explorer'], restif, client.allowed_children)
        ev = events.DragStart()
        d['explorer'].select(f'.{explorer.name_cls}')[0].dispatchEvent(ev)
        assert ev.dataTransfer.data
        add_expected_response('/data/Block/123/create_representation', 'post', Response(201, json={
            'Id': 400,
            '__classname__': '_BlockRepresentation',
            'block': 123,
            'parent': None,
            'diagram': 5,
            'x': 400,
            'y': 500,
            'width': 64,
            'height': 40,
            'children': [],
            'block_cls': 'BlockRepresentation',
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123, '__classname__': 'Block'},
        }))
        diagram.canvas.dispatchEvent(events.DragEnter(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.Drop(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragEnd(dataTransfer=ev.dataTransfer))
        assert diagram.children
        repr = diagram.children[0]
        assert repr.name == 'One'
        assert repr.diagram == 5
        assert repr.block == 123
        assert repr.Id == 400
        assert not unexpected_requests

    @test
    def drag_and_drop_with_ports():
        ds = mk_ds()
        add_expected_response('/data/diagram_contents/5', 'get', Response(201, json=[]))
        diagram, rest = new_diagram(5, ds)
        instance = client.Block(name='One', parent=3, Id=123)
        instance.children.append(client.FlowPort(name='output', parent=123, Id=124))
        ds.update_cache(instance)
        ds.update_cache(instance.children[0])
        restif = Mock()
        restif.get_hierarchy = Mock(side_effect=lambda cb: cb([instance]))
        explorer.make_explorer(d['explorer'], restif, client.allowed_children)
        ev = events.DragStart()
        ev.dataTransfer.data = {'entity': json.dumps(instance, cls=ExtendibleJsonEncoder)}
        add_expected_response('/data/Block/123/create_representation', 'post', Response(201, json={
            'Id': 400,
            '__classname__': '_BlockRepresentation',
            'block': 123,
            'parent': None,
            'diagram': 5,
            'x': 400,
            'y': 500,
            'width': 64,
            'height': 40,
            'block_cls': 'BlockRepresentation',
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123, '__classname__': 'Block'},
            'children': [
                {
                    'Id': 401,
                    'block': 124,
                    'parent': 400,
                    'diagram': 5,
                    '__classname__': '_BlockRepresentation',
                    'block_cls': 'FlowPortRepresentation',
                    '_entity': {'name': 'Output', 'parent': 123, 'Id': 124, '__classname__': 'FlowPort'}
                }
            ]
        }))
        diagram.canvas.dispatchEvent(events.DragEnter(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.Drop(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragEnd(dataTransfer=ev.dataTransfer))
        assert diagram.children
        repr = diagram.children[0]
        assert len(repr.ports) == 1
        port = repr.ports[0]
        assert port.Id == 401
        assert port.parent == 400
        assert port.block == 124
        assert port.diagram == 5

    @test
    def load_diagram():
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=example_diagram))
        diagram, rest = new_diagram(3, ds)
        assert len(expected_responses) == 0
        assert not unexpected_requests

        # Check the various elements were rendered to the DOM
        nonlocal d
        assert len(d['canvas'].select('[data-class="NoteRepresentation"]')) == 1
        assert len(d['canvas'].select('[data-class="BlockRepresentation"]')) == 2
        assert len(d['canvas'].select('[data-class="FlowPortRepresentation"]')) == 1

    @test
    def connection_property_editor():
        import public.sysml_client as client
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=port2port))
        diagram, rest = new_diagram(3, ds)
        ds.subscribe('shape_selected', diagram.canvas, client.on_diagram_selection)
        connection = diagram.connections[0]
        connection.path.dispatchEvent(events.MouseDown())
        connection.path.dispatchEvent(events.MouseUp())
        assert not unexpected_requests
        nonlocal d
        form = d.select('form')
        assert len(form) == 1
        html_form = str(form)
        assert 'name' in html_form
        assert 'linecolor' in html_form
        edit = d.select_one('form #edit_name')
        edit.value = 'Connection'
        btn = d.select_one('#details .btn-primary')

        add_expected_response('/data/FlowPortConnection/1', 'post', Response(200, json={}))
        add_expected_response('/data/_RelationshipRepresentation/1', 'post', Response(200, json={}))
        btn.dispatchEvent(events.Click())

        live_instance = ds.get(Collection.relation, 1)
        assert live_instance.name == 'Connection'

        assert not unexpected_requests
        assert len(expected_responses) == 0

    @test
    def block_property_editor():
        import public.sysml_client as client
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=port2port))
        diagram, rest = new_diagram(3, ds)
        ds.subscribe('shape_selected', diagram, client.on_diagram_selection)
        block = [c for c in diagram.children if c.ports][0]
        block.shape.dispatchEvent(events.MouseDown())
        block.shape.dispatchEvent(events.MouseUp())
        assert not unexpected_requests
        nonlocal d
        form = d.select('form')
        assert len(form) == 1
        html_form = str(form)
        assert 'name' in html_form
        assert 'description' in html_form
        assert 'TR' in html_form            # the editor for the port
        assert 'blockcolor' in html_form

        assert not unexpected_requests
        assert len(expected_responses) == 0


@prepare
def simulated_explorer_tests():
    from data_store import DataConfiguration, DataStore, Collection
    from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses, clear_expected_response
    from browser import events
    import public.sysml_client as client
    from explorer import make_explorer

    # Set the context for the diagram editor. Normally this is in the HTML file.
    from browser import document as d
    from browser import html

    def reset_document():
        d.clear()
        d <= html.DIV(id='explorer')
        d <= html.DIV(id='canvas')
        d <= html.DIV(id='details')
    reset_document()

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
    def right_click_menu():
        ds = DataStore(config)

        clear_expected_response()
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
                {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": None,
              "__classname__": "StructuralModel"},

            ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        # Get the second line in the explorer and right-click it.
        lines = d.get(selector='.eline [draggable="true"]')
        assert len(lines) == 2
        l = [l for l in lines if 'Structural' in str(l)][0]
        l.dispatchEvent(events.ContextMenu())
        # Find the option to create a new diagram
        items = list(l.select('*'))
        print(f'Len items: {len(items)} {[i.text for i in items]}')
        option = [item for item in l.select('*') if item.text == 'BlockDefinitionDiagram'][0]
        option.dispatchEvent(events.Click())
        # There should be a form to enter the name for the new diagram.
        # Enter a name and click OK
        input = d.select(".brython-dialog-main input")[0]
        input.value = 'My Diagram'
        button = [b for b in d.select(".brython-dialog-main button") if b.text.lower() == 'ok'][0]
        add_expected_response('/data/BlockDefinitionDiagram', 'post', Response(201, json={'Id': 3}))
        button.dispatchEvent(events.Click())
        lines = d.get(selector='.eline [draggable="true"]')
        assert len(lines) == 3

    @test
    def left_click():
        reset_document()
        ds = DataStore(config)

        clear_expected_response()
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
                {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": None,
              "__classname__": "StructuralModel"},

            ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        blank = d['explorer']
        ds.subscribe('click', blank, client.on_explorer_click)

        # Get the second line in the explorer and left-click it.
        lines = d.get(selector='.eline [draggable="true"]')
        assert len(lines) == 2
        # Check the details editor is empty
        assert len(d.select('#details *')) == 0
        l = [l for l in lines if 'Structural' in str(l)][0]
        l.dispatchEvent(events.Click())
        # Check the details editor is not empty
        assert len(d.select('#details *')) > 0

        # Change the value of the Structural Model,
        btn = d.select_one('#details button')
        edit_fields = [i for i in d.select('#details input') if i.value == 'Structural Model']
        assert len(edit_fields) == 1
        assert edit_fields[0].value == 'Structural Model'
        edit_fields[0].value = 'blablablabla'
        add_expected_response('/data/StructuralModel/2', 'post', Response(200))
        btn.dispatchEvent(events.Click())
        assert len(expected_responses) == 0
        assert len(unexpected_requests) == 0
        assert ds.get(Collection.hierarchy, 2).name == 'blablablabla'

    @test
    def drag_drop():
        reset_document()
        ds = DataStore(config)

        clear_expected_response()
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
                {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": None,
              "__classname__": "StructuralModel"},

            ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        blank = d['explorer']

        source = [i for i in d['explorer'].select(f'.{explorer.name_cls}') if 'Structural' in str(i)][0]
        ev = events.DragStart()
        source.dispatchEvent(ev)
        assert ev.dataTransfer.data
        target = [i for i in d['explorer'].select(f'.{explorer.name_cls}') if 'Functional' in str(i)][0]
        target.dispatchEvent(events.DragEnter(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.Drop(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragEnd(dataTransfer=ev.dataTransfer))

        # Acknowledge that a move is desired
        btns = d.select('.brython-dialog-main button')
        ok_btn = [b for b in btns if b.text.lower() == 'ok'][0]
        def get_response(url, method, kwargs):
            data = json.loads(kwargs['data'])
            assert data['parent'] == 1
            return Response(200, json=data)
        add_expected_response('/data/StructuralModel/2', 'post', get_response=get_response)
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
              "__classname__": "FunctionalModel"},
                {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": 1,
              "__classname__": "StructuralModel"},

            ]))
        ok_btn.dispatchEvent(events.Click())

        assert not unexpected_requests
        assert len(expected_responses) == 0


if __name__ == '__main__':
    run_tests()
