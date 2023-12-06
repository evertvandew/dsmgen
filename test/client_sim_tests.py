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
from unittest.mock import Mock, MagicMock
import diagrams
import explorer
from rest_api import ExtendibleJsonEncoder
import generate_project     # Ensures the client is built up to date


@prepare
def simulated_client_tests():

    import public.sysml_client as client

    # Set the context for the diagram editor. Normally this is in the HTML file.
    from browser import document as d
    from browser import html
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
        diagram, rest = new_diagram(1, MagicMock())
        diagram.diagram_id = 5
        instance = client.Block(name='One', parent=3, Id=123)
        restif = Mock()
        restif.get_hierarchy = Mock(side_effect=lambda cb: cb([instance]))
        explorer.make_explorer(d['explorer'], restif)
        ev = events.DragStart()
        d['explorer'].select(f'.{explorer.name_cls}')[0].dispatchEvent(ev)
        assert ev.dataTransfer.data
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

    @test
    def load_diagram():
        from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses
        from data_store import DataConfiguration, DataStore, Collection
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

        ds = DataStore(config)

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
                  {"Id": 5, "diagram": 3, "port": 10, "block": 2, "__classname__": "_PortRepresentation",
                   "port_cls": "FlowPortRepresentation",
                   "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}}
                  ]))
        diagram, rest = new_diagram(3, ds)
        assert len(expected_responses) == 0
        assert not unexpected_requests

if __name__ == '__main__':
    run_tests("simulated_client_tests.load_diagram")