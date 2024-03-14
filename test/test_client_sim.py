"""
Tests where the Brython client is run against a simulated Brython - browser.
"""

import json

import data_store
import modeled_shape
from test_frame import prepare, test, run_tests
from dataclasses import fields
from property_editor import longstr
from inspect import signature
from typing import List, Dict, Any, Type, Tuple, Optional
from shapes import Shape, Relationship, Point, HIDDEN
from unittest.mock import Mock, MagicMock
import diagrams
import explorer
from data_store import ExtendibleJsonEncoder, DataStore, DataConfiguration, Collection, StorableElement
from browser.ajax import add_expected_response, unexpected_requests, Response, expected_responses, \
    clear_expected_response
from browser import events, html, document as d
import public.sysml_client as client
from explorer import make_explorer
import tab_view as tv

import generate_project     # Ensures the client is built up to date

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
        base_url='/data'
    )

    ds = DataStore(config)
    return ds


example_diagram = [
    {"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {"color": "yellow"}, "block_cls": "BlockRepresentation", "category": int(data_store.ReprCategory.block),
     "__classname__": "_BlockRepresentation",
     "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1",
                 "description": "This is a test block",
                 "__classname__": "Block"}},
    {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 345.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {}, "block_cls": "BlockRepresentation", "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                 "__classname__": "Block"}},
    {"Id": 3, "diagram": 3, "block": 7, "x": 101.0, "y": 360.0, "z": 0.0, "width": 110.0, "height": 65.0,
     "styling": {"bordercolor": "#000000", "bordersize": "2", "blockcolor": "#fffbd6", "fold_size": "10",
                 "font": "Arial", "fontsize": "16", "textcolor": "#000000", "xmargin": 2, "ymargin": 2,
                 "halign": 11, "valign": 2}, "block_cls": "NoteRepresentation",
     "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "Id": 7, "description": "Dit is een commentaar", "parent": 3,
                 "__classname__": "Note"}},
    {"Id": 1, "diagram": 3, "relationship": 1, "source_repr_id": 1, "target_repr_id": 2, "routing": "[]",
     "z": 0.0, "styling": {}, "rel_cls": "BlockReferenceRepresentation",
     "__classname__": '_RelationshipRepresentation',
     "_entity": {"Id": 1, "stereotype": 1, "source": 4, "target": 5, "source_multiplicity": 1,
                 "target_multiplicity": 1, "__classname__": "BlockReference"}},
    {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation",
     "block_cls": "FlowPortRepresentation",
     "category": int(data_store.ReprCategory.port),
     "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}
     }
]


port2port = [
    {"Id": 1, "diagram": 3, "block": 4, "x": 401.0, "y": 104.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {"color": "yellow"}, "block_cls": "ModeledShapeAndPorts", "parent": None,
     "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "Id": 4, "parent": None, "name": "Test1",
                 "description": "This is a test block",
                 "__classname__": "Block"}},
    {"Id": 2, "diagram": 3, "block": 5, "x": 369.0, "y": 345.0, "z": 0.0, "width": 64.0, "height": 40.0,
     "styling": {}, "block_cls": "ModeledShapeAndPorts", "__classname__": "_BlockRepresentation", "parent": None,
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "Id": 5, "parent": 2, "name": "Test2", "description": "",
                 "__classname__": "Block"}},
    {"Id": 3, "diagram": 3, "block": 7, "x": 101.0, "y": 360.0, "z": 0.0, "width": 110.0, "height": 65.0,
     "styling": {"bordercolor": "#000000", "bordersize": "2", "blockcolor": "#fffbd6", "fold_size": "10",
                 "font": "Arial", "fontsize": "16", "textcolor": "#000000", "xmargin": 2, "ymargin": 2,
                 "halign": 11, "valign": 2}, "block_cls": "ModeledShapeAndPorts",
     "__classname__": "_BlockRepresentation", "parent": None,
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "Id": 7, "name": "Test 3", "description": "Dit is een commentaar", "parent": 2,
                 "__classname__": "Block"}},
    {"Id": 51, "diagram": 3, "block": 10, "parent": 2, "__classname__": "_BlockRepresentation",
     "block_cls": "Port",
     "category": int(data_store.ReprCategory.port),
     "_entity": {"Id": 10, "parent": 5, "__classname__": "FlowPort"}
     },
    {"Id": 52, "diagram": 3, "block": 11, "parent": 3, "__classname__": "_BlockRepresentation",
     "block_cls": "Port",
     "category": int(data_store.ReprCategory.port),
     "_entity": {"Id": 11, "parent": 7, "__classname__": "FlowPort"}
     },
    {"Id": 1, "diagram": 3, "relationship": 1, "source_repr_id": 51, "target_repr_id": 52, "routing": "[]",
     "z": 0.0, "styling": {}, "rel_cls": "ModeledRelationship",
     '__classname__': '_RelationshipRepresentation',
     "category": int(data_store.ReprCategory.relationship),
     "_entity": {"Id": 1, "stereotype": 1, "source": 10, "target": 11, "source_multiplicity": 1,
                 "target_multiplicity": 1, "__classname__": "FlowPortConnection"}},

]


diagram_w_instance = [
    {"Id": 1, "diagram": 3, "block": 7, "parent": None, "x": 358.0, "y": 235.0, "z": 0.0, "width": 64.0, "height": 40.0, "styling": {}, "block_cls": "BlockInstanceRepresentation", "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "parameters": {"parameters": {"factor": 41, "gain": 3.1415}}, "Id": 7, "parent": 3, "definition": 4, "__classname__": "BlockInstance"},
     "_definition": {"order": 0, "Id": 4, "parent": 1, "name": "test block", "implementation": "", "parameters": {"factor": "int", "gain": "float"}, "__classname__": "SubProgramDefinition"}},
    {"Id": 2, "diagram": 3, "block": 5, "parent": 1, "x": 0.0, "y": 0.0, "z": 0.0, "width": 0.0, "height": 0.0, "styling": {}, "block_cls": "FlowPortRepresentation", "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.block),
     "_entity": {"order": 0, "orientation": 8, "Id": 5, "name": "in", "parent": 4, "__classname__": "FlowPort"}},
    {"Id": 3, "diagram": 3, "block": 6, "parent": 1, "x": 0.0, "y": 0.0, "z": 0.0, "width": 0.0, "height": 0.0, "styling": {}, "block_cls": "FlowPortRepresentation", "__classname__": "_BlockRepresentation",
     "category": int(data_store.ReprCategory.port),
     "_entity": {"order": 0, "orientation": 4, "Id": 6, "name": "out", "parent": 4, "__classname__": "FlowPort"}}
]


class IntegrationContext:

    def get_new_id(self, block_cls: Type[StorableElement]) -> int:
        return max(list(self.data_store.live_instances[block_cls.get_collection()]) + [0]) + 1

    def __init__(self, hierarchy=None):
        d.clear()
        d <= html.DIV(id='explorer')
        d <= html.DIV(id='canvas')
        d <= html.DIV(id='details')
        self.d = d

        integration_context = self

        class HtmlApi:
            parent = d
            def click(self, source):
                """ Click on a specific items in the explorer."""
                source.dispatchEvent(events.Click())
            def dblclick(self, source):
                """ Click on a specific items in the explorer."""
                source.dispatchEvent(events.DblClick())
            def find_elements(self, selector='*', text=''):
                """ Find all elements in the explorer fitting a specific selector and/or text."""
                elements = self.parent.select(selector)
                if text:
                    elements = [e for e in elements if text in str(e)]
                return elements

            def find_element(self, selector='*', text=''):
                """ Find a single element in the explorer, fitting a specific selector and/or text. """
                elements = self.find_elements(selector, text)
                assert len(elements) == 1
                return elements[0]

        class ExplorerApi(HtmlApi):
            parent = d['explorer']
            def count(self):
                """ Return the number of elements in the explorer, over all levels. """
                elements = self.find_elements(f'.{explorer.name_cls}')
                return len(elements)
            def dblclick_element(self, mid: int):
                self.dblclick(self.find_element(f'[data-modelid="{mid}"]'))

        class DiagramsApi(HtmlApi):
            parent: html.tag = d['canvas']
            def count(self):
                """ Count how many diagrams are in the editor. """
                return len(d['canvas'].select(f'.{tv.body_cls}'))

            def prepare_contents(self, contents: Dict[int, Any]):
                """ Prepare the Ajax communications mockup to yield the contents for specific diagrams. """
                for key, content in contents.items():
                    add_expected_response(f'/data/diagram_contents/{key}', 'get', Response(201, json=content))

            def create_block(self, block_cls: modeled_shape.ModelEntity):
                """ Create a block inside the current diagram by clicking on the CreateWidget. """
                # Prepare the AJAX mock to return two ID's: one for the model entity, one for the representation.
                assert len(expected_responses) == 0
                mid = integration_context.get_new_id(block_cls)
                repr_cls = block_cls.get_representation_cls(modeled_shape.ReprCategory.block)
                rid = integration_context.get_new_id(repr_cls)
                add_expected_response(f'/data/{block_cls.__name__}', 'post',  Response(201, json={'Id': mid}))
                add_expected_response(f'/data/_BlockRepresentation', 'post', Response(201, json={'Id': rid}))

                # Find the create widget
                btn = self.find_element(f'#create_{block_cls.__name__}_btn')
                # Press it.
                btn.dispatchEvent(events.MouseDown())
                btn.dispatchEvent(events.MouseUp())
                # Check the AJAX requests were consumed.
                assert len(expected_responses) == 0

            def click_block(self, rid: int):
                shape = self.resolve(rid).shape
                shape.dispatchEvent(events.MouseDown())
                shape.dispatchEvent(events.MouseUp())
                shape.dispatchEvent(events.Click())

            def move_block(self, rid: int, cood: Tuple[float,float] | Point):
                """ Move the block by manipulating it through mouse events
                """
                # Expect an update of the representation to be sent to the server.
                add_expected_response(f'/data/_BlockRepresentation/{rid}', 'post', Response(2001, json={'Id': rid}))
                # Find the shape involved.
                shape = self.resolve(rid).shape
                # Move it.
                shape.dispatchEvent(events.MouseDown(offsetX=0, offsetY=0))
                shape.dispatchEvent(events.MouseMove(offsetX=cood[0], offsetY=cood[1]))
                shape.dispatchEvent(events.MouseUp(offsetX=cood[0], offsetY=cood[1]))

            def add_port(self, rid, port_cls, **kwargs):
                """ Add a port to a block. This is simply done by manipulating the data structure,
                    as this is what happens in real life (by the properties editor).
                """
                # Expect an update of the representation to be sent to the server.
                pid = integration_context.get_new_id(port_cls)
                prid = integration_context.get_new_id(port_cls.get_representation_cls(modeled_shape.ReprCategory.port))
                add_expected_response(f'/data/{port_cls.__name__}', 'post', Response(201, json={'Id': pid}))
                add_expected_response(f'/data/_BlockRepresentation', 'post', Response(201, json={'Id': prid}))
                # Find the shape data structure
                shape = integration_context.data_store.get(Collection.block_repr, rid)
                me = shape.model_entity
                # Add the port to the underlying model
                port = port_cls(parent=me.Id, **kwargs)
                integration_context.data_store.add(port)
                # Cause the port to be drawn
                shape.updateShape(shape.shape)
                # Check the AJAX requests were consumed.
                assert len(expected_responses) == 0
                assert not unexpected_requests


            def ports(self, rid: int) -> List[client.ms.Port]:
                block = self.resolve(rid)
                assert hasattr(block, 'ports')
                return block.ports

            def resolve(self, block_port: int | Tuple[int, int]) -> client.ms.ModelRepresentation:
                if isinstance(block_port, tuple):
                    return self.ports(block_port[0])[1]
                else:
                    diagram = integration_context.diagram_tabview.current_diagram
                    reprs = [s for s in diagram.children if s.Id == block_port]
                    assert reprs
                    return reprs[0]

            def enter_connection_mode(self):
                diagram = integration_context.diagram_tabview.current_diagram
                diagram.canvas.select_one('#onConnectMode').dispatchEvent(events.Click())
                assert isinstance(diagram.mouse_events_fsm, diagrams.ConnectionEditor)


            def enter_block_mode(self):
                diagram = integration_context.diagram_tabview.current_diagram
                diagram.canvas.select_one('#onBlockMode').dispatchEvent(events.Click())

            def connect(self, a: int | Tuple[int, int], b: int | Tuple[int, int], relation_cls):
                """ Connect two entities in the current diagram.
                    The connection is made between a (source) and b (target). Both can be given as a simple
                    integer (meaning a simple block) or a (block, port) tuple.

                    This function can not handle the selection dialog if multiple connections are possible!
                """
                # Expect new records to be created in the database, and determine IDs for the new records
                rid = integration_context.get_new_id(relation_cls)
                rrid = integration_context.get_new_id(relation_cls.get_representation_cls(modeled_shape.ReprCategory.relationship))

                add_expected_response(f'/data/{relation_cls.__name__}', 'post', Response(201, json={'Id': rid}))
                add_expected_response(f'/data/_RelationshipRepresentation', 'post', Response(201, json={'Id': rrid}))

                source = self.resolve(a)
                target = self.resolve(b)
                self.enter_connection_mode()
                source.shape.dispatchEvent(events.MouseDown())
                source.shape.dispatchEvent(events.MouseUp())
                target.shape.dispatchEvent(events.MouseDown())
                target.shape.dispatchEvent(events.MouseUp())
                # Check the AJAX requests were consumed.
                assert len(expected_responses) == 0
                assert not unexpected_requests

            def block_text(self, rid: int) -> str:
                """ Returns the text currently being displayed in a block.
                    If there are multiple text blocks associated with the block, return the first.
                """
                repr = integration_context.data_store.live_instances[Collection.block_repr][rid]
                txt = repr.shape.select('text')
                if txt:
                    return ' '.join(t.text for t in txt)
                return ''

        class PropertyEditorApi(HtmlApi):
            parent: html.tag = d['details']

            def save(self):
                """ Save the current values in the port editor to the model.. """
                self.parent.select_one(f'#save_properties').dispatchEvent(events.Click())
            def add_port(self, port_cls: Type, nr_reprs: int=0):
                """ Add a new port of class `port_cls` using the property editor.
                    Expect nr_reprs to be made in various diagrams.
                """
                # Expect new records to be created in the database, and determine IDs for the new records
                pid = integration_context.get_new_id(port_cls)
                add_expected_response(f'/data/{port_cls.__name__}', 'post', Response(201, json={'Id': pid}))
                # Expect a number of representations to be made.
                for _ in range(nr_reprs):
                    rid = integration_context.get_new_id(port_cls.get_representation_cls(modeled_shape.ReprCategory.port))
                    add_expected_response(f'/data/_BlockRepresentation', 'post', Response(201, json={'Id': rid}))

                self.parent.select_one(f'#add_port').dispatchEvent(events.Click())
                # Check if the selection dialog popped up
                port_options = d.select('#port_selector option')
                if port_options:
                    # Select the right option
                    for o in port_options:
                        if o.text == port_cls.__name__:
                            d.select_one('#port_selector').value = o.attrs['value']
                    # Click the Ok button
                    [b for b in d.select('.brython-dialog-button') if b.text.lower() == 'ok'][0].dispatchEvent(events.Click())

                # Check the AJAX requests were consumed.
                assert len(expected_responses) == 0
                assert not unexpected_requests

            def remove_port(self, index: int=0):
                """ remove a specific port from the list """
                # Determine which database record will be deleted.
                rows = self.find_elements('tr.port_row')
                row_ids = [int(r.attrs['data-mid']) for r in rows]
                mid = row_ids[index]
                record = integration_context.data_store.live_instances[Collection.block][mid]
                add_expected_response(f'/data/{type(record).__name__}/{record.Id}', 'delete', Response(204))
                # Also expect representations of this record to be deleted.
                repr_ids = [r.Id for r in integration_context.data_store.live_instances[Collection.block_repr].values() if r.block == mid]
                for rid in repr_ids:
                    add_expected_response(f'/data/_BlockRepresentation/{rid}', 'delete', Response(204))
                # Click on the button deleting the port.
                rows[index].select_one('button').dispatchEvent(events.Click())
                # Now click on the "Yes" button.
                [b for b in d.select('.brython-dialog-button') if b.text.lower() == 'yes'][0].dispatchEvent(
                    events.Click())
                # Check the AJAX requests were consumed.
                assert len(expected_responses) == 0
                assert not unexpected_requests

            def count_ports(self):
                return len(self.parent.select('[id^="delete_port_"]'))

            def set_field(self, **kwargs):
                """ Set the value of one or more fields in the record currently being edited in property editor. """
                for key, value in kwargs.items():
                    self.find_element(f'#edit_{key}').value = str(value)


        self.explorer = ExplorerApi()
        self.diagrams = DiagramsApi()
        self.property_editor = PropertyEditorApi()

        if hierarchy:
            add_expected_response(f'/data/hierarchy', 'get', Response(201, json=hierarchy))

        self.data_store, self.diagram_tabview = client.run('explorer', 'canvas', 'details')



@prepare
def simulated_diagram_tests():
    """ Test detailed behaviour of the diagram editor. """
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
        def create_and_move(model_entity: client.ms.ModelEntity, **repr_details):
            instance = model_entity.get_representation_cls(modeled_shape.ReprCategory.block)(model_entity=model_entity, **repr_details)
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
        create_and_move(client.Block(name='', Id=1), x=300, y=300, height=64, width=100, Id=1)

        # Add a port label representation
        create_and_move(client.FlowPort(name='', Id=1), x=300, y=300, height=64, width=100, Id=1)

        # Add a SubprogramDefinition
        create_and_move(client.SubProgramDefinition(name='', Id=1), x=300, y=300, height=64, width=100, Id=1)

    @test
    def create_connect_blocks():
        # Connect two PortLabels: an input and an output.
        diagram, rest = new_diagram(1, MagicMock())
        entity = client.Block(Id=1, name='block')
        p1 = client.FlowPort(Id=2, parent=1, name='Input')
        p2 = client.FlowPort(Id=3, parent=1, name='Output')
        input = client.PortLabel(model_entity=p1, x=100, y=300, height=64, width=100, Id=10)
        output =client.PortLabel(model_entity=p2, x=400, y=300, height=64, width=100, Id=11)

        diagram.addBlock(input)
        diagram.addBlock(output)
        diagram.changeFSM(diagrams.ConnectionEditor())
        input.shape.dispatchEvent(events.MouseDown())
        input.shape.dispatchEvent(events.MouseUp())
        output.shape.dispatchEvent(events.MouseDown())
        output.shape.dispatchEvent(events.MouseUp())
        assert len(diagram.connections) == 1
        conn = diagram.connections[0]
        assert type(conn.model_entity).__name__ == 'FlowPortConnection'
        assert conn.start.Id == 10
        assert conn.finish.Id == 11


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
            'category': int(data_store.ReprCategory.block),
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123, '__classname__': 'Block'},
        }))
        diagram.canvas.dispatchEvent(events.DragEnter(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.Drop(dataTransfer=ev.dataTransfer))
        diagram.canvas.dispatchEvent(events.DragEnd(dataTransfer=ev.dataTransfer))
        assert diagram.children
        repr = diagram.children[0]
        assert repr.model_entity.name == 'One'
        assert repr.diagram == 5
        assert repr.model_entity.Id == 123
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
            'category': int(data_store.ReprCategory.block),
            '_entity': {'name': 'One', 'parent': 3, 'Id': 123, '__classname__': 'Block'},
            'children': [
                {
                    'Id': 401,
                    'block': 124,
                    'parent': 400,
                    'diagram': 5,
                    '__classname__': '_BlockRepresentation',
                    'block_cls': 'FlowPortRepresentation',
                    'category': int(data_store.ReprCategory.port),
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
        assert len(d['canvas'].select('[data-class="ModeledShapeAndPorts"]')) == 2
        assert len(d['canvas'].select('[data-class="ModeledShape"]')) == 1
        assert len(d['canvas'].select('[data-class="Port"]')) == 1

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
        assert len(form) == 2
        html_form = str(form)
        assert d.select('#edit_name')
        assert d.select('#styling_linecolor')
        edit = d.select_one('form #edit_name')
        edit.value = 'Connection'
        btn = d.select_one('#details .btn-primary')

        add_expected_response('/data/FlowPortConnection/1', 'post', Response(200, json={}))
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
        assert len(form) == 2
        assert d.select('#edit_name')
        assert d.select('#edit_description')
        assert d.select('.porttable TR')           # the editor for the port
        # There should be a style editor in the second form.
        assert d.select('#styling_blockcolor')

        assert not unexpected_requests
        assert len(expected_responses) == 0

    @test
    def handling_parameter_spec_dropped_block():
        """ Simulate dropping a block so that it is instantiated.
            Then check the proper edit fields are presented and handled.
        """
        nonlocal d
        import public.sysml_client as client
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/5', 'get', Response(201, json=[]))
        diagram, rest = new_diagram(5, ds)
        ds.subscribe('shape_selected', diagram.canvas, client.on_diagram_selection)
        rest.add = set_entity_ids([400])

        definition = client.SubProgramDefinition(Id=123, name='Block 1', parent=1, description='Dit is een test', parameters='limit:int,factor:float')
        ds.update_cache(definition)

        restif = Mock()
        restif.get_hierarchy = Mock(side_effect=lambda cb: cb([definition]))
        explorer.make_explorer(d['explorer'], restif, client.allowed_children)
        ev = events.DragStart()
        ev.dataTransfer.data = {'entity': json.dumps(definition, cls=ExtendibleJsonEncoder)}

        add_expected_response('/data/BlockInstance/123/create_representation', 'post', Response(201, json={
            'Id': 400,
            '__classname__': '_BlockInstanceRepresentation',
            'block': 125,
            'parent': None,
            'diagram': 5,
            'x': 400,
            'y': 500,
            'width': 64,
            'height': 40,
            'children': [
                {
                    'Id': 401,
                    'block': 124,
                    'parent': 400,
                    'diagram': 5,
                    '__classname__': '_BlockRepresentation',
                    'block_cls': 'FlowPortRepresentation',
                    "category": int(data_store.ReprCategory.port),
                    '_entity': {'name': 'Output', 'parent': 123, 'Id': 124, '__classname__': 'FlowPort'}
                }
            ],
            'block_cls': 'BlockInstanceRepresentation',
            '_entity': {'Id': 125, 'definition': 123, 'parameters': '',  'parent': 5, '__classname__': 'BlockInstance'},
            '_definition': definition.asdict()
        }))

        for cls in [events.DragEnter, events.DragOver, events.DragOver, events.Drop, events.DragEnd]:
            diagram.canvas.dispatchEvent(cls(dataTransfer=ev.dataTransfer))

        assert diagram.children
        repr: client.ms.ModeledShapeAndPorts = diagram.children[0]
        assert repr.diagram == 5
        assert repr.model_entity.Id == 125
        assert repr.model_entity.parent == 5
        assert repr.model_entity.definition == definition
        assert repr.Id == 400
        assert not unexpected_requests

        # Trigger the details editor.
        repr.shape.dispatchEvent(events.MouseDown())
        repr.shape.dispatchEvent(events.MouseUp())
        assert not unexpected_requests
        form = d.select('form')
        assert len(form) == 2

        # Assert the correct edits have been created.
        assert d.select('#edit_factor')
        assert d.select('#edit_limit')
        assert not d.select('#edit_parameters')

        # Set the values and check they are stored properly.
        d.select('#edit_factor')[0].value = '123.456'
        d.select('#edit_limit')[0].value = '87654'
        btn = d.select_one('#details .btn-primary')

        add_expected_response('/data/BlockInstance/125', 'post', Response(200, json={}))
        btn.dispatchEvent(events.Click())

        assert repr.model_entity.parameters == {'factor': 123.456, 'limit': 87654}

        assert not unexpected_requests
        assert len(expected_responses) == 0

    @test
    def block_properties_editor_instance():
        """ Load a diagram with a single block: an instance with ports """
        nonlocal d
        import public.sysml_client as client
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/3', 'get', Response(
            200,
            json=diagram_w_instance))
        diagram, rest = new_diagram(3, ds)
        ds.subscribe('shape_selected', diagram, client.on_diagram_selection)

        block = diagram.children[0]
        block.shape.dispatchEvent(events.MouseDown())
        block.shape.dispatchEvent(events.MouseUp())
        assert not unexpected_requests
        form = d.select('form')
        assert len(form) == 2
        html_form = str(form)
        # There should be edit fields for the gain and the factor parameters, as specified in the parameter definitions.
        assert d.select('#edit_gain')
        assert d.select('#edit_factor')
        assert not d.select('form TR')            # There must be no editor for ports.
        # Check there is no editing of the fields in the Definition
        assert len(d.select('#edit_parameters')) == 0
        assert len(d.select('#edit_description')) == 0
        assert len(d.select('#edit_name')) == 0
        # It should be possible to edit the styling of the block.
        assert d.select('#styling_blockcolor')

        assert not unexpected_requests
        assert len(expected_responses) == 0

    @test
    def load_test_diagrams():
        resp = [{"Id": 0, "diagram": 4, "block": 7, "parent": None, "x": 110.0, "y": 393.0, "z": 0.0, "width": 64.0,
          "height": 40.0, "order": 0, "orientation": None, "styling": "", "category": None,
          "_entity": {"order": 0, "Id": 7, "description": "Dit is een test", "parent": 4, "__classname__": "Note"},
          "__classname__": "_BlockRepresentation"},
         {"Id": 1, "diagram": 4, "block": 5, "parent": None, "x": 188.0, "y": 106.0, "z": 0.0, "width": 64.0,
          "height": 40.0, "order": None, "orientation": None, "styling": "", "category": 2,
          "_entity": {"order": 0, "parameters": {"parameters": {}}, "Id": 5, "parent": 4, "definition": 3,
                      "__classname__": "BlockInstance"},
          "_definition": {"order": 0, "Id": 3, "parent": 1, "name": "test_block", "implementation": "",
                          "parameters": "{}", "__classname__": "BlockDefinition"},
          "__classname__": "_BlockRepresentation"},
         {"Id": 2, "diagram": 4, "block": 6, "parent": None, "x": 309.0, "y": 104.0, "z": 0.0, "width": 64.0,
          "height": 40.0, "order": None, "orientation": None, "styling": "", "category": 2,
          "_entity": {"order": 0, "Id": 6, "name": "subprog", "description": "", "parameters": "", "parent": 4,
                      "__classname__": "SubProgram"}, "__classname__": "_BlockRepresentation"}]

        nonlocal d
        import public.sysml_client as client
        ds = mk_ds()

        add_expected_response('/data/diagram_contents/4', 'get', Response(
            200,
            json=diagram_w_instance))
        diagram, rest = new_diagram(4, ds)


@prepare
def simulated_explorer_tests():
    """ Test detailed behaviour of the explorer. """
    def reset_document():
        clear_expected_response()
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
        input = d.select("#edit_name")[0]
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
    def editing_parameter_spec():
        """ Test the editor for a parameter spec. """
        # The SubProgramDefinition has a parameter spec.
        reset_document()
        ds = DataStore(config)

        clear_expected_response()
        add_expected_response('/data/hierarchy', 'get', Response(
            200,
            json=[
                {"order": 0, "Id": 1, "name": "Test block", "description": "", "parent": None,
              "__classname__": "SubProgramDefinition"},
            ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        blank = d['explorer']
        ds.subscribe('click', blank, client.on_explorer_click)

        # Get the first line in the explorer and left-click it.
        lines = d.get(selector='.eline [draggable="true"]')
        assert len(lines) == 1
        # Check the details editor is empty
        assert len(d.select('#details *')) == 0
        l = [l for l in lines if 'Test block' in str(l)][0]
        l.dispatchEvent(events.Click())
        # Check the details editor is not empty
        assert len(d.select('#details *')) > 0
        for expected in ['edit_name', 'edit_description', 'edit_parameters']:
            assert len(d.select(f'#{expected}')) > 0, f"Expected edit {expected} not found"

        # Set the parameters field and submit the changes.
        input = d.select('#edit_parameters')[0]
        input.value = 'gain:float,factor:int'
        add_expected_response('/data/StructuralModel/2', 'post', Response(200))
        btn = d.select_one('#details button')
        btn.dispatchEvent(events.Click())
        assert len(expected_responses) == 0
        assert len(unexpected_requests) == 0


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

    @test
    def existing_instance_property_editer():
        # Create an explorer showing one definition block and one instance.
        ds = mk_ds()
        add_expected_response('/data/hierarchy', 'get', Response(201, json=[
            {'Id': 123, 'name': 'Block 1', 'parent': None, 'description': 'Dit is een test', 'parameters': 'limit:int,factor:float', '__classname__': 'SubProgramDefinition'},
            {'Id': 125, 'definition': 123, 'parameters': '', 'parent': None, '__classname__': 'BlockInstance', 'parameters': {'factor': 123, 'limit': 456}}
        ]))
        make_explorer(d['explorer'], ds, client.allowed_children)
        blank = d['explorer']
        ds.subscribe('click', blank, client.on_explorer_click)

        # Click on the Instance and check that the values in the edit fields are correct.
        source = [i for i in d['explorer'].select('.eline [draggable="true"]') if 'BlockInstance' in str(i)][0]
        source.dispatchEvent(events.Click())
        assert d.select('#edit_factor')[0].value == 123
        assert d.select('#edit_limit')[0].value == 456
        pass

@prepare
def integration_tests():
    """ Test high-level behaviour of the tool. """
    from browser import document as d
    from browser import html

    TheHierarchy = [
        {"order": 0, "Id": 1, "name": "Functional Model", "description": "", "parent": None,
        "__classname__": "FunctionalModel"},
        {"order": 0, "Id": 2, "name": "Structural Model", "description": "", "parent": 1,
        "__classname__": "StructuralModel"},
        {'Id': 3, 'parent': 1, 'name': 'subprogram', '__classname__': "SubProgramDefinition"}
    ]

    @test
    def edit_subdiagram():
        context = IntegrationContext(hierarchy=TheHierarchy)
        assert context.explorer.count() == 3
        context.diagrams.prepare_contents({3: []})
        context.explorer.dblclick_element(mid=3)
        assert context.diagrams.count() == 1

        # Create a basic network.
        # First create the main components.
        context.diagrams.create_block(client.FlowPort)
        context.diagrams.move_block(1, (0, 100))
        context.diagrams.create_block(client.Block)
        context.diagrams.move_block(2, (300, 100))
        context.diagrams.create_block(client.FlowPort)
        context.diagrams.move_block(3, (600, 100))
        # Add two ports to the Block
        context.diagrams.add_port(2, client.FlowPort, name='in')
        context.diagrams.add_port(2, client.FlowPort, name='out')
        assert len(context.diagrams.ports(2)) == 2
        # Connect the three blocks
        context.diagrams.connect(1, (2,1), client.FlowPortConnection)
        context.diagrams.connect((2,2), 3, client.FlowPortConnection)
        # Check the data in the data store
        # The SubProgramDefinition should have two ports
        assert len([p for p in context.data_store.ports if p.parent == 3]) == 2
        # There should be two relationships to the block
        assert len(context.data_store.relationships) == 2

    @test
    def edit_ports():
        """ Create a block, add ports, edit them and delete them.
            Use the property editor, check changes are reflected in the diagram.
        """
        context = IntegrationContext(hierarchy=[
            client.BlockDefinitionDiagram(Id=1, name="diagram").asdict(),
        ])
        # Open the diagram in the display and add a block
        context.explorer.dblclick_element(mid=1)
        context.diagrams.create_block(client.Block)
        # Open the property editor for this block
        context.diagrams.click_block(rid=1)
        # Add a port and check it is represented
        context.property_editor.add_port(client.FlowPort, 1)
        context.property_editor.save()
        assert context.property_editor.count_ports() == 1
        assert len(context.diagrams.ports(rid=1)) == 1
        # Add another port
        context.property_editor.add_port(client.FlowPort, 1)
        context.property_editor.save()
        assert context.property_editor.count_ports() == 2
        assert len(context.diagrams.ports(rid=1)) == 2
        # Check they are in the database
        assert len(context.data_store.live_instances[Collection.block]) == 3
        assert len(context.data_store.live_instances[Collection.block_repr]) == 3
        # Delete the two ports
        add_expected_response(f'/data/FlowPort/3', 'delete', Response(204))
        context.property_editor.remove_port()
        add_expected_response(f'/data/FlowPort/2', 'delete', Response(204))
        context.property_editor.remove_port()
        context.property_editor.save()
        assert context.property_editor.count_ports() == 0
        assert len(context.diagrams.ports(rid=1)) == 0
        # Check they are no more in the database
        assert len(context.data_store.live_instances[Collection.block]) == 1
        assert not context.data_store.live_instances[Collection.block][1].ports
        assert len(context.data_store.live_instances[Collection.block_repr]) == 1
        assert not context.data_store.live_instances[Collection.block_repr][1].ports
        # Check they are in the database
        assert len(context.data_store.live_instances[Collection.block]) == 1
        assert len(context.data_store.live_instances[Collection.block_repr]) == 1

    @test
    def edit_block_name():
        """ Create a block, edit the 'name' field.
            Use the property editor, check changes are reflected in the diagram.
        """
        context = IntegrationContext(hierarchy=[
            client.BlockDefinitionDiagram(Id=1, name="diagram").asdict(),
        ])
        # Open the diagram in the display and add a block
        context.explorer.dblclick_element(mid=1)
        context.diagrams.create_block(client.Block)
        # Open the property editor for this block
        context.diagrams.click_block(rid=1)
        # Change the name and save it.
        name = 'test block'
        context.property_editor.set_field(name=name)
        context.property_editor.save()
        assert context.diagrams.block_text(rid=1) == name

if __name__ == '__main__':
    run_tests('*.edit_block_name')
    run_tests()
