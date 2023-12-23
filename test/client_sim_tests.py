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
from browser.ajax import add_expected_response, unexpected_requests, Response
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
        diagram = diagrams.load_diagram(
            diagram_id,
            client.diagram_definitions['BlockDefinitionDiagram'],
            diagram_api,
            svg,
            client.representation_lookup,
            client.connections_from
        )
        return diagram, diagram_api

    @test
    def create_and_move_block():
        diagram, rest = new_diagram(1, MagicMock())
        instance = client.BlockRepresentation(name='', x=300, y=300, height=64, width=100, block=1, Id=1)
        diagram.addBlock(instance)
        assert len(diagram.children) == 1

        # Simulate dragging the block
        block = diagram.children[0]
        block.shape.dispatchEvent(events.MouseDown())
        block.shape.dispatchEvent(events.MouseMove(offsetX=200, offsetY=100))
        block.shape.dispatchEvent(events.MouseUp(offsetX=200, offsetY=100))
        assert block.x == 500
        assert block.y == 400

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
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123},
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
        ds.cache[Collection.block][123] = deepcopy(instance)
        ds.cache[Collection.block][124] = deepcopy(instance.children[0])
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
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123},
            'children': [
                {
                    'Id': 401,
                    'block': 124,
                    'parent': 400,
                    'diagram': 5,
                    '__classname__': '_BlockRepresentation',
                    'block_cls': 'FlowPortRepresentation',
                    '_entity': {'name': 'Output', 'parent': 123, 'Id': 124}
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
        from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses
        from data_store import DataConfiguration, DataStore, Collection
        import public.sysml_client as client

        ds = mk_ds()

        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=[{"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
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
                   "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}}
                  ]))
        diagram, rest = new_diagram(3, ds)
        assert len(expected_responses) == 0
        assert not unexpected_requests

        # Check the various elemenets were rendered to the DOM
        nonlocal d
        assert len(d['canvas'].select('[data-class="NoteRepresentation"]')) == 1
        assert len(d['canvas'].select('[data-class="BlockRepresentation"]')) == 2
        assert len(d['canvas'].select('[data-class="FlowPortRepresentation"]')) == 1

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
    d.clear()
    d <= html.DIV(id='explorer')
    d <= html.DIV(id='canvas')
    d <= html.DIV(id='details')

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
                {"order": 0, "Id": 3, "entities": [], "parent": 2, "name": "test",
                                                    "__classname__": "BlockDefinitionDiagram"},

            ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        # Get the second line in the explorer and right-click it.
        lines = d.get(selector='.eline [draggable="true"]')
        assert len(lines) == 3
        l = lines[1]
        l.dispatchEvent(events.ContextMenu())
        options = d.select('UL [text="Create"] LI')
        # TODO: This test is not complete.


if __name__ == '__main__':
    run_tests()