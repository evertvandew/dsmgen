


import json

import data_store
import modeled_shape
from shapes import Point, handle_class
import diagrams
from modeled_diagram import ModeledDiagram
import explorer
from data_store import ReprCategory
from browser.ajax import add_expected_response, Response, check_expected_response
from browser import events, html, document as d
import tab_view as tv
from typing import List, Dict, Any, Type, Tuple, Optional, Generator

from storable_element import StorableElement, Collection
from modeled_shape import ModelRepresentation, Port


class HtmlApi:
    parent = d

    def click(self, source):
        """ Click on a specific items in the explorer."""
        source.dispatchEvent(events.Click())

    def dblclick(self, source):
        """ Click on a specific items in the explorer."""
        source.dispatchEvent(events.DblClick())

    def rightclick(self, source):
        """ Click on a specific items in the explorer."""
        source.dispatchEvent(events.ContextMenu())

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

    def press_ok(self):
        btn = [b for b in d.select('.brython-dialog-button') if b.text.lower() == 'ok'][0]
        btn.dispatchEvent(events.Click())


class ExplorerApi(HtmlApi):
    def __init__(self, context):
        self.context = context
        self.parent = d['explorer']

    def expect_request(self, *args, **kwargs):
        self.context.expect_request(*args, **kwargs)

    def count(self):
        """ Return the number of elements in the explorer, over all levels. """
        elements = self.find_elements(f'.{explorer.name_cls}')
        return len(elements)

    def dblclick_element(self, mid: int):
        self.dblclick(self.find_element(f'[data-modelid="{mid}"]'))

    def click_element(self, mid: int):
        self.click(self.find_element(f'[data-modelid="{mid}"]'))

    def rightclick_element(self, mid: int):
        self.rightclick(self.find_element(f'[data-modelid="{mid}"]'))

    def name(self, mid: int):
        """ Return the name of the element `mid` as shown in the explorer. """
        el = self.find_element(f'[data-modelid="{mid}"] .ename')
        return el.text[3:]

    def create_block(self, parent_mid, cls, **details):
        """ Create a block as child of block <parent_mid>, of type cls, with attributes set to details. """
        self.rightclick_element(parent_mid)
        # Click the action to create the right class block.
        btn = [b for b in d.select(f'DIALOG .contextmenu li') if b.text == cls.__name__][0]
        btn.dispatchEvent(events.Click())
        # Set the details
        for k, v in details.items():
            d.select_one(f'.brython-dialog-panel #edit_{k}').value = str(v)
        # Click the OK button to create the block.
        btn = [b for b in d.select('.brython-dialog-button') if b.text == 'OK'][0]
        btn.dispatchEvent(events.Click())

    def delete_block(self, mid: int):
        assert self.context.no_dialogs()
        self.rightclick_element(mid)
        model_item = self.context.data_store.get(Collection.block, mid)
        self.context.expect_request(f'/data/{type(model_item).__name__}/{mid}', 'delete', 204)
        # Navigate the right-click menu
        btn = [b for b in d.select(f'DIALOG .contextmenu li') if b.text.lower() == 'remove'][0]
        btn.dispatchEvent(events.Click())
        self.press_ok()
        self.context.check_expected_response()
        assert self.context.no_dialogs()

    def drag_to_diagram(self, mid: int, drop_cls) -> int:
        """ Drag the block identified by model Id mid to the current diagram.
            :param drop_cls: the expected class for which a representation is requested.
        """
        # Prepare for the expected Server API calls
        diagram = self.context.diagrams.current_diagram()
        assert diagram, "Please open a diagram first"
        rid = None

        def determine_response(url, method, kwargs):
            """ Simulate the behaviour of the server handling the create_representation function. """
            nonlocal rid
            request_cls: Type[StorableElement] = self.context.data_store.all_classes[url.split('/')[2]]
            rid = self.context.get_new_id(
                request_cls.get_representation_cls(modeled_shape.ReprCategory.block))
            # Find any possible children (ports)
            ports = [p for p in self.context.data_store.live_instances[Collection.block].values()
                     if p.parent == mid and p.get_representation_cls(modeled_shape.ReprCategory.port)]
            children = [dict(
                Id=rid + 1 + i,
                parent=rid,
                _entity=p.asdict(),
                category=ReprCategory.port,
                __classname__='_BlockRepresentation'
            ) for i, p in enumerate(ports)]

            entity: StorableElement = self.context.data_store.get(Collection.block, mid)

            #data = json.loads(kwargs['data'])
            data = kwargs
            category = data.get('category', None) or ReprCategory.block
            content = {
                'Id': rid,
                '_entity': entity.asdict(),
                'children': children,
                'category': category,
                '__classname__': request_cls.get_representation_cls(category).__name__
            }

            return Response(201, json=content)

        # We need to know what
        self.context.expect_request(f'/data/{drop_cls.__name__}/{mid}/create_representation',
                              'post', get_response=determine_response)
        el = self.find_element(f'[data-modelid="{mid}"]')
        # Perform a drag-and-drop sequence.
        ev = events.DragStart()
        el.dispatchEvent(ev)
        diagram = self.context.diagrams.current_diagram()
        target = diagram.canvas
        target.dispatchEvent(events.DragEnter(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragOver(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.Drop(dataTransfer=ev.dataTransfer))
        target.dispatchEvent(events.DragEnd(dataTransfer=ev.dataTransfer))
        # Check the AJAX requests were consumed.
        self.context.check_expected_response()
        return rid

class DiagramsApi(HtmlApi):
    def __init__(self, context):
        self.parent: html.DOMNode = d['canvas']
        self.context = context

    def expect_request(self, *args, **kwargs):
        self.context.expect_request(*args, **kwargs)

    def current_diagram(self) -> ModeledDiagram:
        return self.context.diagram_tabview.current_diagram

    def count(self):
        """ Count how many diagrams are in the editor. """
        return len(d['canvas'].select(f'.{tv.body_cls}'))

    def blocks(self) -> List:
        return self.current_diagram().children

    def connections(self) -> List:
        return self.current_diagram().connections

    def prepare_contents(self, contents: Dict[int, Any]):
        """ Prepare the Ajax communications mockup to yield the contents for specific diagrams. """
        for key, content in contents.items():
            self.context.expect_request(f'/data/diagram_contents/{key}', 'get', 201, response_json=content)

    def create_block(self, block_cls: modeled_shape.ModelEntity) -> Tuple[int, int]:
        """ Create a block inside the current diagram by clicking on the CreateWidget. """
        # Prepare the AJAX mock to return two ID's: one for the model entity, one for the representation.
        self.context.check_expected_response()
        mid = self.context.get_new_id(block_cls)
        repr_cls = block_cls.get_representation_cls(modeled_shape.ReprCategory.block)
        rid = self.context.get_new_id(repr_cls)
        self.expect_request(f'/data/{block_cls.__name__}', 'post', response_code=201, response_json={'Id': mid})
        # self.context.expect_request(
        #    f'/data/{block_cls.__name__}', 'post',
        #    Response(201, json={'Id': mid})
        # )
        self.expect_request(f'/data/_BlockRepresentation', 'post', response_code=201,
                            response_json={'Id': rid}, expect_values={'category': 2})
        # self.context.expect_request(
        #    f'/data/_BlockRepresentation', 'post',
        #    Response(201, json={'Id': rid}),
        #    expect_values={'category': 2}
        # )

        # Find the create widget
        btn = self.find_element(f'#create_{block_cls.__name__}_btn')
        # Press it.
        btn.dispatchEvent(events.MouseDown())
        btn.dispatchEvent(events.MouseUp())
        # Check the AJAX requests were consumed.
        self.context.check_expected_response()
        return mid, rid

    def create_message(self, rid: int, cls: Type) -> Tuple[int, int]:
        """ Create a new message linked to a relationship: rid """
        # Get hold of the path to click it and get the context menu.
        paths = self.parent.select(f'path[data-category="4"][data-rid="{rid}"]')
        assert paths
        path = paths[0]
        path.dispatchEvent(events.ContextMenu())
        # Find the item to click to create the right message class.
        items = d.select(f'dialog li[data-text="{cls.__name__}"]')
        assert items
        items[0].dispatchEvent(events.Click())
        # Prepare for the correct requests
        mid = self.context.get_new_id(cls)
        repr_cls = cls.get_representation_cls(modeled_shape.ReprCategory.message)
        msg_rid = self.context.get_new_id(repr_cls)
        self.expect_request(f'/data/ClassMessage', 'post', response_code=201, response_json={'Id': mid})
        self.expect_request(f'/data/_MessageRepresentation', 'post', response_code=201,
                            response_json={'Id': msg_rid})
        # Click OK on the details pop-up
        btn = [b for b in d.select('.brython-dialog-button') if b.text == 'OK'][0]
        btn.dispatchEvent(events.Click())
        self.context.check_expected_response()
        return mid, msg_rid

    def move_message(self, rid: int, delta: Tuple[float, float] | Point):
        if isinstance(delta, Point):
            delta = delta.astuple()
        msg_repr = self.parent.select_one(f'g[data-category="5"][data-rid="{rid}"]')
        self.context.expect_request(f'/data/_MessageRepresentation/{rid}', 'post', 200)
        msg_repr.dispatchEvent(events.MouseDown(offsetX=0, offsetY=0))
        msg_repr.dispatchEvent(events.MouseMove(offsetX=delta[0], offsetY=delta[1]))
        msg_repr.dispatchEvent(events.MouseUp(offsetX=delta[0], offsetY=delta[1]))
        self.context.check_expected_response()

    def delete_message(self, rid: int):
        msg_repr = self.parent.select_one(f'g[data-category="5"][data-rid="{rid}"]')
        msg_repr.dispatchEvent(events.Click())
        self.context.expect_request(f'/data/_MessageRepresentation/{rid}', 'delete', 204)
        ev = events.KeyDown(key='Delete')
        self.parent.parent.dispatchEvent(ev)
        self.press_ok()
        self.context.check_expected_response()

    def click_block(self, rid: int, altKey=False, shiftKey=False, ctrlKey=False):
        shape = self.resolve(rid).shape
        shape.dispatchEvent(events.MouseDown(altKey=altKey, shiftKey=shiftKey, ctrlKey=ctrlKey))
        shape.dispatchEvent(events.MouseUp(altKey=altKey, shiftKey=shiftKey, ctrlKey=ctrlKey))
        shape.dispatchEvent(events.Click(altKey=altKey, shiftKey=shiftKey, ctrlKey=ctrlKey))

    def click_relation(self, rid: int):
        shape = self.parent.select(f'[data-category="{ReprCategory.relationship}"][data-rid="{rid}"]')[0]
        shape.dispatchEvent(events.MouseDown())
        shape.dispatchEvent(events.MouseUp())
        shape.dispatchEvent(events.Click())

    def move_block(self, rid: int, cood: Tuple[float, float] | Point, expect_no_change=False):
        """ Move the block by manipulating it through mouse events
        """
        # Expect an update of the representation to be sent to the server.
        if not expect_no_change:
            self.context.expect_request(f'/data/_BlockRepresentation/{rid}', 'post', 200)
        # Find the shape involved.
        shape = self.resolve(rid).shape
        # Move it.
        self.move_shape(shape, cood)
        self.context.check_expected_response()

    def move_shape(self, shape, cood: Tuple[float, float] | Point):
        if isinstance(cood, Point):
            cood = cood.astuple()
        shape.dispatchEvent(events.MouseDown(offsetX=0, offsetY=0))
        shape.dispatchEvent(events.MouseMove(offsetX=cood[0], offsetY=cood[1]))
        shape.dispatchEvent(events.MouseUp(offsetX=cood[0], offsetY=cood[1]))

    def drag_relation_handle(self, index: int, delta: Tuple[float, float] | Point):
        diagram = self.current_diagram()
        handle = diagram.canvas.select_one(f'.{handle_class}[data-index="{index}"]')
        self.move_shape(handle, delta)

    def delete_block(self, rid: int):
        """ Delete a block """
        # The block must first be selected, then the delete key pressed.
        self.click_block(rid)
        assert self.current_diagram().mouse_events_fsm.state == diagrams.ResizeStates.DECORATED
        self.parent.parent.dispatchEvent(events.KeyDown(key='Delete'))
        # The user is presented with an acknowledgement diagram
        self.context.expect_request('/data/_BlockRepresentation/4', 'delete', 204)
        self.press_ok()
        self.context.check_expected_response()

    def add_port(self, rid, port_cls, **kwargs) -> Tuple[int, int]:
        """ Add a port to a block. This is simply done by manipulating the data structure,
            as this is what happens in real life (by the properties editor).
        """
        # Expect an update of the representation to be sent to the server.
        pid = self.context.get_new_id(port_cls)
        prid = self.context.get_new_id(port_cls.get_representation_cls(modeled_shape.ReprCategory.port))
        self.context.expect_request(f'/data/{port_cls.__name__}', 'post', 201, response_json={'Id': pid})
        self.context.expect_request(f'/data/_BlockRepresentation', 'post', 201, response_json={'Id': prid})
        # Find the shape data structure
        shape = self.context.data_store.get(Collection.block_repr, rid)
        me = shape.model_entity
        # Add the port to the underlying model
        port = port_cls(parent=me.Id, **kwargs)
        self.context.data_store.add_complex(port)
        # Cause the port to be drawn
        shape.updateShape(shape.shape)
        # Check the AJAX requests were consumed.
        self.context.check_expected_response()
        return [pid, prid]

    def ports(self, rid: int) -> List[Port]:
        block = self.resolve(rid)
        assert hasattr(block, 'ports')
        return block.ports

    def resolve(self, block_port: int | Tuple[int, int]) -> ModelRepresentation:
        """ Resolve a connection point.
            :param block_port: either an integer containing the repr.Id of the block in the diagram's children
                list, or a tuple containing the block repr.Id and the index of the port in the block's ports list.
        """
        if isinstance(block_port, tuple):
            return self.ports(block_port[0])[block_port[1]]
        else:
            diagram = self.current_diagram()
            reprs = [s for s in diagram.children if s.Id == block_port]
            assert reprs
            return reprs[0]

    def enter_connection_mode(self):
        diagram = self.current_diagram()
        diagram.canvas.select_one('#onConnectMode').dispatchEvent(events.Click())
        assert isinstance(diagram.mouse_events_fsm, diagrams.ConnectionEditor)

    def enter_block_mode(self):
        diagram = self.current_diagram()
        diagram.canvas.select_one('#onBlockMode').dispatchEvent(events.Click())

    def connect(self, a: int | Tuple[int, int], b: int | Tuple[int, int], relation_cls, expect_popup=False) -> \
    Tuple[int, int]:
        """ Connect two entities in the current diagram.
            The connection is made between a (source) and b (target). Both can be given as a simple
            integer (meaning a simple block) or a (block, port) tuple.

            This function can not handle the selection dialog if multiple connections are possible!
        """
        # Expect new records to be created in the database, and determine IDs for the new records
        rid = self.context.get_new_id(relation_cls)
        rrid = self.context.get_new_id(
            relation_cls.get_representation_cls(modeled_shape.ReprCategory.relationship))

        self.expect_request(f'/data/{relation_cls.__name__}', 'post', response_code=201,
                            response_json={'Id': rid})
        self.expect_request(f'/data/_RelationshipRepresentation', 'post', response_code=201,
                            response_json={'Id': rrid})
        # self.context.expect_request(f'/data/_RelationshipRepresentation', 'post', Response(201, json={'Id': rrid}))

        source = self.resolve(a)
        target = self.resolve(b)
        self.enter_connection_mode()
        source.shape.dispatchEvent(events.MouseDown())
        source.shape.dispatchEvent(events.MouseUp())
        # Move the mouse over the canvas
        delta = (target.getPos() - source.getPos()).astuple()
        self.parent.dispatchEvent(events.MouseMove(offsetX=delta[0] / 2, offsetY=delta[1] / 2))
        target.shape.dispatchEvent(events.MouseDown())
        target.shape.dispatchEvent(events.MouseUp())

        if expect_popup:
            btn = [b for b in d.select('.brython-dialog-panel li') if b.text == relation_cls.__name__][0]
            btn.dispatchEvent(events.Click())
        # Check the AJAX requests were consumed.
        self.context.check_expected_response()
        return rid, rrid

    def block_text(self, rid: int) -> str:
        """ Returns the text currently being displayed in a block.
            If there are multiple text blocks associated with the block, return the first.
        """
        repr = self.context.data_store.live_instances[Collection.block_repr][rid]
        txt = repr.shape.select('text')
        if txt:
            return ' '.join(t.text for t in txt)
        return ''

    def nr_block_decorated(self) -> bool:
        handles = self.parent.select(f'.{handle_class}')
        return len(handles)

    def undo(self):
        self.parent.parent.dispatchEvent(events.KeyDown(key='z', ctrlKey=True, shiftKey=False))

    def redo(self):
        self.parent.parent.dispatchEvent(events.KeyDown(key='z', ctrlKey=True, shiftKey=True))

class PropertyEditorApi(HtmlApi):
    def __init__(self, context):
        self.parent: html.DOMNode = d['details']
        self.context = context

    def expect_request(self, *args, **kwargs):
        self.context.expect_request(*args, **kwargs)

    def save(self):
        """ Save the current values in the port editor to the model.. """
        self.parent.select_one(f'#save_properties').dispatchEvent(events.Click())

    def add_port(self, port_cls: Type, nr_reprs: int = 0):
        """ Add a new port of class `port_cls` using the property editor.
            Expect nr_reprs to be made in various diagrams.
        """
        # Expect new records to be created in the database, and determine IDs for the new records
        pid = self.context.get_new_id(port_cls)
        self.context.expect_request(f'/data/{port_cls.__name__}', 'post', 201, response_json={'Id': pid})
        # Expect a number of representations to be made.
        for _ in range(nr_reprs):
            rid = self.context.get_new_id(
                port_cls.get_representation_cls(modeled_shape.ReprCategory.port))
            self.context.expect_request(f'/data/_BlockRepresentation', 'post', 201, response_json={'Id': rid})

        self.parent.select_one(f'#add_port').dispatchEvent(events.Click())
        # Check if the selection dialog popped up
        port_options = d.select('#port_selector option')
        if port_options:
            # Select the right option
            for o in port_options:
                if o.text == port_cls.__name__:
                    d.select_one('#port_selector').value = o.attrs['value']
            # Click the Ok button
            [b for b in d.select('.brython-dialog-button') if b.text.lower() == 'ok'][0].dispatchEvent(
                events.Click())

        # Check the AJAX requests were consumed.
        self.context.check_expected_response()

    def remove_port(self, index: int = 0):
        """ remove a specific port from the list """
        # Determine which database record will be deleted.
        rows = self.find_elements('tr.port_row')
        row_ids = [int(r.attrs['data-mid']) for r in rows]
        mid = row_ids[index]
        record = self.context.data_store.live_instances[Collection.block][mid]
        self.context.expect_request(f'/data/{type(record).__name__}/{record.Id}', 'delete', 204)
        # Also expect representations of this record to be deleted.
        repr_ids = [r.Id for r in self.context.data_store.live_instances[Collection.block_repr].values()
                    if r.block == mid]
        for rid in repr_ids:
            self.context.expect_request(f'/data/_BlockRepresentation/{rid}', 'delete', 204)
        # Click on the button deleting the port.
        rows[index].select_one('button').dispatchEvent(events.Click())
        # Now click on the "Yes" button.
        [b for b in d.select('.brython-dialog-button') if b.text.lower() == 'yes'][0].dispatchEvent(
            events.Click())
        # Check the AJAX requests were consumed.
        self.context.check_expected_response()

    def count_ports(self):
        return len(self.parent.select('[id^="delete_port_"]'))

    def set_field(self, **kwargs):
        """ Set the value of one or more fields in the record currently being edited in property editor. """
        for key, value in kwargs.items():
            self.find_element(f'#edit_{key}').value = str(value)

    def set_style(self, **kwargs):
        """ Set the value of one or more style items """
        for key, value in kwargs.items():
            self.find_element(f'#styling_{key}').value = str(value)

class DataStoreApi:
    def __init__(self, context, ds: data_store.UndoableDataStore):
        self.ds = ds
        self.context = context

    def all_elements(self) -> Generator[Tuple[int, StorableElement], None, None]:
        for c in Collection:
            yield from self.ds.live_instances[c].items()

    @property
    def undo_queue(self):
        return self.ds.undo_queue

    @property
    def redo_queue(self):
        return self.ds.redo_queue

    def expect_request(self, *args, **kwargs):
        self.context.expect_request(*args, **kwargs)


class IntegrationContext:

    def get_new_id(self, block_cls: Type[StorableElement] | Collection) -> int:
        if isinstance(block_cls, type) and issubclass(block_cls, StorableElement):
            block_cls = block_cls.get_collection()
        if block_cls in [Collection.block, Collection.hierarchy]:
            return max(list(self.data_store.live_instances[Collection.hierarchy]) +
                       list(self.data_store.live_instances[Collection.block]) +
                       [0]) + 1
        return max(list(self.data_store.live_instances[block_cls]) + [0]) + 1

    def __init__(self, client, server, hierarchy=None):
        d.clear()
        d <= html.DIV(id='explorer')
        d <= html.DIV(id='canvas')
        d <= html.DIV(id='details')
        self.d = d
        self.server = server

        self.explorer = ExplorerApi(self)
        self.diagrams = DiagramsApi(self)
        self.property_editor = PropertyEditorApi(self)

        self.expect_request(f'/current_database', 'get', 201, response_json="test_db")
        if hierarchy:
            self.expect_request(f'/data/hierarchy', 'get', 201, response_json=hierarchy)

        self.data_store, self.diagram_tabview = client.run('explorer', 'canvas', 'details')
        self.ds = DataStoreApi(self, self.data_store)

    def no_dialogs(self) -> bool:
        """ Check there are no dialogs (i.e. all have been closed) """
        return len(d.select('.brython-dialog-main')) == 0

    def expect_request(self, url, method, response_code: int=200, response_json=None, response_obj=None,
                       expect_values: Optional[Dict[str, Any]] = None, get_response=None):
        """ Expect a request over Ajax, and provide a specific response.
            When received, the data of the request is checked by trying to instantiate an object of
            `request_type` from it. If successful, the response is returned. The response can either be
            a preset simple JSON-parseable datastructure, or an object with an `asdict` member function.
            This function is called to determine the response.
        """
        parts = url.split('/')

        if get_response:
            response = None
        else:
            response = Response(response_code, json=response_obj.asdict()) if response_obj else (
                Response(response_code, json=response_json))

        checker = None
        if (len(parts) > 1 and len(parts) < 4 and parts[1] == 'data' and (table := getattr(self.server, parts[2], None))
                and method.lower() in ['post', 'put']):
            def checker(url, method, kwargs):
                #data = json.loads(kwargs['data'])
                data = kwargs
                if expect_values:
                    for k, v in expect_values.items():
                        assert data[k] == v
                if '__classname__' in data:
                    del data['__classname__']
                _request = table(**data)

        add_expected_response(url, method, response, get_response=get_response, check_request=checker,
                              expect_values=expect_values)

    def check_expected_response(self):
        check_expected_response()
