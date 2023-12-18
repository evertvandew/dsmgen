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
from browser import events, document
from unittest.mock import Mock, MagicMock
import diagrams
import explorer
from rest_api import ExtendibleJsonEncoder
import generate_project     # Ensures the client is built up to date



@prepare
def test_port_editor():
    from property_editor import createPortEditor
    import public.sysml_client as client
    ds = Mock()
    @test
    def create():
        block_repr = client.BlockRepresentation(
            x=100, y=100, width=64, height=40,
            ports=[client.FlowPortRepresentation()]
        )
        f = [f for f in fields(block_repr) if f.name=='ports'][0]

        # Create the port editor
        element = createPortEditor(block_repr, f, block_repr.get_allowed_ports(), ds)

        # Edit the values of the existing port
        line = element.select(".porttable tr")[0]
        line.dispatchEvent(events.Click())
        side_selector = document.select_one('#edit_orientation')
        side_selector.value = 2
        dialog = document.select_one('.brython-dialog-main')
        dialog.ok_button.dispatchEvent(events.Click())

        # Add a new port
        btn = element.children[-1]
        btn.dispatchEvent(events.Click())
        dialog = document.select('.brython-dialog-main')[0]
        port_selector = document.select('SELECT')[0]
        port_selector.value = 1
        dialog.ok_button.dispatchEvent(events.Click())
        assert len(block_repr.ports) == 2
        pass


if __name__ == '__main__':
    run_tests()