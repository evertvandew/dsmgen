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

    def empty_diagram():
        container = d['canvas']
        container.html = ''
        svg = html.SVG()
        svg.classList.add('diagram')
        container <= svg
        diagram_api = MagicMock()
        diagram = diagrams.load_diagram(
            1,
            client.diagram_definitions['BlockDefinitionDiagram'],
            diagram_api,
            svg,
            client.representation_lookup,
            client.connections_from
        )
        return diagram, diagram_api

    @test
    def create_and_move_block():
        diagram, rest = empty_diagram()
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
        diagram, rest = empty_diagram()
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

run_tests()