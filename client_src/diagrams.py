from browser import document, svg, console, window, bind, html
from browser.widgets.dialog import Dialog, InfoDialog


from typing import Any, Self, List, Dict, Type
from dataclasses import dataclass, field, asdict, is_dataclass, fields
from weakref import ref
import enum
from math import inf
import json
from point import Point
from shapes import (Shape, CP, Relationship, getMousePos, Orientations, BlockOrientations, OwnerInterface)
from data_store import DataStore, ExtendibleJsonEncoder
import shapes
import svg_shapes



resize_role = 'resize_decorator'


to_update = {
    Orientations.TL: [Orientations.TR, Orientations.BL, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
    Orientations.TOP: [Orientations.TL, Orientations.TR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP],
    Orientations.TR: [Orientations.TL, Orientations.BR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
    Orientations.RIGHT: [Orientations.TR, Orientations.BR, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
    Orientations.BR: [Orientations.BL, Orientations.TR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
    Orientations.BOTTOM: [Orientations.BL, Orientations.BR, Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM],
    Orientations.BL: [Orientations.BR, Orientations.TL, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
    Orientations.LEFT: [Orientations.TL, Orientations.BL, Orientations.LEFT, Orientations.TOP, Orientations.BOTTOM],
}
locations = {
    Orientations.TL: lambda x, y, w, h: (x, y + h),
    Orientations.TOP: lambda x, y, w, h: (x + w // 2, y + h),
    Orientations.TR: lambda x, y, w, h: (x + w, y + h),
    Orientations.RIGHT: lambda x, y, w, h: (x + w, y + h // 2),
    Orientations.BR: lambda x, y, w, h: (x + w, y),
    Orientations.BOTTOM: lambda x, y, w, h: (x + w // 2, y),
    Orientations.BL: lambda x, y, w, h: (x, y),
    Orientations.LEFT: lambda x, y, w, h: (x, y + h // 2),
}
orientation_details = {
                Orientations.TL: (1, 0, -1, 1, 1, 1),
                Orientations.TOP: (0, 0, 0, 1, 0, 1),
                Orientations.TR: (0, 0, 1, 1, 1, 1),
                Orientations.RIGHT: (0, 0, 1, 0, 1, 0),
                Orientations.BR: (0, 1, 1, -1, 1, 1),
                Orientations.BOTTOM: (0, 1, 0, -1, 0, 1),
                Orientations.BL: (1, 1, -1, -1, 1, 1),
                Orientations.LEFT: (1, 0, -1, 0, 1, 0)
            }

def moveSingleHandle(decorators, widget, orientation):
    d = decorators[orientation]
    x, y, width, height = [getattr(widget, k) for k in ['x', 'y', 'width', 'height']]
    d['cx'], d['cy'] = [int(i) for i in locations[orientation](x, y, width, height)]

def moveHandles(decorators, widget, orientation):
    # Determine which markers to move
    for o in to_update[orientation]:
        moveSingleHandle(decorators, widget, o)

def moveAll(widget, decorators):
    for o in Orientations:
        moveSingleHandle(decorators, widget, o)


class FSMEnvironment:
    """ The FSM needs to talk back to its "environment", the Diagram object. """
    def updateElement(self, element):
        """ Called whenever an element has been updated without informing the Environment
            in another way.
        """
        pass

class BehaviourFSM:
    # FIXME: Remove the diagrams from all these functions.
    def mouseDownShape(self, diagram, widget, ev):
        pass
    def mouseDownConnection(self, diagram, widget, ev):
        pass
    def mouseDownPort(self, diagram, widget, ev):
        pass
    def mouseDownBackground(self, diagram, ev):
        pass
    def onMouseUp(self, diagram, ev):
        pass
    def onMouseMove(self, diagram, ev):
        pass
    def onKeyDown(self, diagram, ev):
        pass
    def delete(self, diagram):
        """ Called when the FSM is about to be deleted"""
        pass


class ResizeStates(enum.IntEnum):
    NONE = enum.auto()
    DECORATED = enum.auto()
    MOVING = enum.auto()
    RESIZING = enum.auto()

class ResizeFSM(BehaviourFSM):
    def __init__(self, diagram):
        super().__init__()
        self.state: ResizeStates = ResizeStates.NONE
        self.diagram = diagram
        self.widget: Shape | List[Shape] = None
        self.decorators = {}

    def mouseDownShape(self, diagram, widget, ev):
        if self.state != ResizeStates.NONE and self.widget != widget:
            self.unselect()
        if self.state == ResizeStates.NONE:
            self.select(widget)
        self.state = ResizeStates.MOVING
        self.dragstart = getMousePos(ev)
        self.initial_pos = widget.getPos()
        ev.stopPropagation()
        ev.preventDefault()

    def mouseDownConnection(self, diagram, widget, ev):
        # We need to change the state machine
        if self.state != ResizeStates.NONE:
            self.unselect()
        fsm = RerouteStates(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownConnection(diagram, widget, ev)

    def mouseDownBackground(self, diagram, ev):
        if self.widget and ev.target == self.widget.shape:
            self.state = ResizeStates.MOVING
            return
        if ev.target == diagram.canvas:
            if self.state == ResizeStates.DECORATED:
                self.unselect()
        self.state = ResizeStates.NONE
        return
        # FIXME: check if this code needs to be removed.
        self.dragstart = getMousePos(ev)
        if self.widget:
            self.initial_pos = diagram.selection.getPos()
            self.initial_size = diagram.selection.getSize()


    def onMouseUp(self, diagram, ev):
        # If an object was being moved, evaluate if it changed owner
        if self.state == ResizeStates.MOVING:
            pos = getMousePos(ev)
            diagram.evaluateOwnership(self.widget, pos, self.widget.owner)
        if self.state in [ResizeStates.MOVING, ResizeStates.RESIZING]:
            self.diagram.updateElement(self.widget)
            self.state = ResizeStates.DECORATED

    def onMouseMove(self, diagram, ev):
        if self.state in [ResizeStates.NONE, ResizeStates.DECORATED]:
            return
        delta = getMousePos(ev) - self.dragstart
        if self.state == ResizeStates.RESIZING:
            self.onDrag(self.initial_pos, self.initial_size, delta)
        if self.state == ResizeStates.MOVING:
            self.widget.setPos(self.initial_pos + delta)
            diagram.rerouteConnections(self.widget)

    def delete(self, diagram):
        """ Called when the FSM is about to be deleted"""
        if self.state != ResizeStates.NONE:
            self.unselect()

    def startResize(self, widget, orientation, ev):
        self.dragstart = getMousePos(ev)
        self.state = ResizeStates.RESIZING
        self.initial_pos = widget.getPos()
        self.initial_size = widget.getSize()

    def unselect(self):
        for dec in self.decorators.values():
            dec.remove()
        self.decorators = {}
        if self.widget:
            self.widget.unsubscribe(resize_role)
        self.widget = None
        self.state = ResizeStates.NONE

    def select(self, widget):
        self.widget = widget

        self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2") for k in Orientations}
        x, y, width, height = [getattr(widget, k) for k in ['x', 'y', 'width', 'height']]

        for k, d in self.decorators.items():
            d['cx'], d['cy'] = [int(i) for i in locations[k](x, y, width, height)]

        def bind_decorator(d, orientation):
            def dragStart(ev):
                self.dragged_handle = orientation
                self.startResize(widget, orientation, ev)
                ev.stopPropagation()

            d.bind('mousedown', dragStart)

        for orientation, d in self.decorators.items():
            self.diagram.canvas <= d
            bind_decorator(d, orientation)

        widget.subscribe(resize_role, lambda w: moveAll(w, self.decorators))

    def onDrag(self, origin, original_size, delta):
        dx, dy, sx, sy, mx, my = orientation_details[self.dragged_handle]
        d = self.decorators[self.dragged_handle]
        shape = self.widget
        movement = Point(x=delta.x * dx, y=delta.y * dy)
        # alert(f"{delta}, {dx}, {dy}, {sx}, {sy}")
        shape.setPos(origin + movement)
        resizement = Point(x=original_size.x + sx * delta.x, y=original_size.y + sy * delta.y)
        shape.setSize(resizement)

        moveHandles(self.decorators, shape, self.dragged_handle)
        self.diagram.rerouteConnections(shape)

    def onKeyDown(self, diagram, ev):
        if ev.key == 'Delete':
            if self.state != ResizeStates.NONE:
                widget = self.widget
                d = Dialog(f'Delete {type(widget).__name__}', ok_cancel=True)
                d.panel <= f'Delete {type(widget).__name__}'
                if hasattr(widget, 'name'):
                    d.panel <= f' "{widget.name}"'

                @bind(d.ok_button, "click")
                def ok(ev):
                    d.close()
                    self.unselect()
                    diagram.deleteBlock(widget)


class RerouteStates(BehaviourFSM):
    States = enum.IntEnum('States', 'NONE DECORATED HANDLE_SELECTED POTENTIAL_DRAG DRAGGING')
    def __init__(self, diagram):
        super().__init__()
        self.state = self.States.NONE
        self.diagram = diagram
        self.decorators = []
        self.dragged_index = None

    def mouseDownShape(self, diagram, widget, ev):
        # We need to change the state machine
        if self.state != self.States.NONE:
            self.clear_decorations()
        fsm = ResizeFSM(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownShape(diagram, widget, ev)


    def mouseDownConnection(self, diagram, widget, ev):
        self.widget = widget
        if not self.decorators:
            self.decorate()
        self.state = self.States.POTENTIAL_DRAG
        self.dragstart = getMousePos(ev)
        self.dragged_index = None
        ev.stopPropagation()
        ev.preventDefault()

    def mouseDownBackground(self, diagram, ev):
        if diagram.selection and ev.target == diagram.selection.shape:
            self.state = self.States.MOVING
            return
        if ev.target == diagram.canvas:
            if self.state == self.States.DECORATED:
                self.clear_decorations()
        self.state = self.States.NONE
        return
        self.dragstart = getMousePos(ev)
        if diagram.selection:
            self.initial_pos = diagram.selection.getPos()
            self.initial_size = diagram.selection.getSize()

    def handleDragStart(self, index, ev):
        self.state = self.States.DRAGGING
        ev.stopPropagation()
        ev.preventDefault()

    def dragHandle(self, ev):
        delta = getMousePos(ev) - self.drag_start
        new_pos = self.initial_pos + delta
        handle = self.decorators[self.dragged_index]
        if self.handle_orientation[self.dragged_index] == 'X':
            handle['x1'] = handle['x2'] = new_pos.x
            self.widget.waypoints[self.dragged_index] = Point(x=new_pos.x, y=inf)
        else:
            handle['y1'] = handle['y2'] = new_pos.y
            self.widget.waypoints[self.dragged_index] = Point(x=inf, y=new_pos.y)

    def onMouseUp(self, diagram, ev):
        if self.state in [self.States.POTENTIAL_DRAG, self.States.DRAGGING]:
            self.widget.router.dragEnd(self.diagram.canvas)
            if self.state == self.States.DRAGGING:
                self.state = self.States.HANDLE_SELECTED
            else:
                self.state = self.States.DECORATED
            diagram.updateElement(self.widget)

    def onMouseMove(self, diagram, ev):
        if self.state in [self.States.NONE, self.States.DECORATED, self.States.HANDLE_SELECTED]:
            return
        pos = getMousePos(ev)
        if self.state == self.States.POTENTIAL_DRAG:
            delta = pos - self.dragstart
            if len(delta) > 10:
                self.widget.router.createWaypointByDrag(pos, self.widget, self.diagram.canvas)
                self.state = self.States.DRAGGING
        if self.state == self.States.DRAGGING:
            self.widget.router.dragHandle(pos)
            diagram.rerouteConnections(self.widget)

    def onKeyDown(self, diagram, ev):
        if ev.key == 'Delete':
            if self.state == self.States.DECORATED:
                # Delete the connection
                self.clear_decorations()
                self.state = self.States.NONE
                diagram.deleteConnection(self.widget)
            elif self.state != self.States.NONE:
                self.widget.router.deleteWaypoint()
                diagram.rerouteConnections(self.widget)

    def delete(self, diagram):
        if self.state != self.States.NONE:
            self.clear_decorations()

    def decorate(self):
        self.widget.router.decorate(self.widget, self.diagram.canvas)

    def clear_decorations(self):
        self.widget.router.clear_decorations()


class ConnectionEditor(BehaviourFSM):
    States = enum.IntEnum('States', 'NONE A_SELECTED RECONNECTING')
    ConnectionRoles = enum.IntEnum('ConnectionRoles', 'START FINISH')
    def __init__(self):
        self.state = self.States.NONE
        self.a_party = None
        self.connection = None
        self.b_connection_role = None
        self.path = None
    def mouseDownShape(self, diagram, widget, ev):
        party = widget.getConnectionTarget(ev)
        if self.state in [self.States.A_SELECTED, self.States.RECONNECTING]:
            if diagram.allowsConnection(self.a_party, party):
                if self.state == self.States.A_SELECTED:
                    diagram.connect(self.a_party, party)
                elif self.state == self.States.RECONNECTING:
                    match self.b_connection_role:
                        case self.ConnectionRoles.START:
                            self.connection.start = party
                        case self.ConnectionRoles.FINISH:
                            self.connection.start = party
                    diagram.reroute(self.connection)

                self.path.remove()
                self.state = self.States.NONE
        elif self.state == self.States.NONE:
            self.state = self.States.A_SELECTED
            self.a_party = party
            # Create a temporary path to follow the mouse
            x, y = [int(i) for i in (self.a_party.getPos() + self.a_party.getSize()/2).astuple()]
            self.path = svg.line(x1=x, y1=y, x2=x, y2=y, stroke_width=2, stroke="gray")
            diagram.canvas <= self.path
    def onMouseMove(self, diagram, ev):
        if self.state == self.States.NONE:
            return
        pos = getMousePos(ev)
        # Let the temporary line follow the mouse.
        # But ensure it doesn't hide the B-shape
        v = pos - self.a_party.getPos()
        delta = (v/len(v)) * 2
        self.path['x2'], self.path['y2'] = [int(i) for i in (pos - delta).astuple()]
    def delete(self, diagram):
        if self.state != self.States.NONE:
            self.path.remove()
    def onKeyDown(self, diagram, ev):
        if ev.key == 'Escape':
            if self.state == self.States.A_SELECTED:
                # Delete the connection
                self.path.remove()
                self.state = self.States.NONE


@dataclass
class DiagramConfiguration:
    connections_from: Dict[type, Dict[type, List[type]]]

    def get_allowed_connections(self, blocka_cls, blockb_cls) -> List[type]:
        console.log(f"getting connections for {blocka_cls} -> {blockb_cls}")
        return self.connections_from.get(blocka_cls, {}).get(blockb_cls, [])


class Diagram(OwnerInterface):
    ModifiedEvent = 'modified'
    ConnectionModeEvent = 'ConnectionMode'
    NormalModeEvent = 'NormalMode'

    def __init__(self, config: DiagramConfiguration, widgets):
        self.selection = None
        self.mouse_events_fsm = None
        self.children = []
        self.connections = []
        self.widgets = widgets
        self.config = config

    def close(self):
        # Release the resources of this diagram and delete references to it.
        self.children = []
        self.connections = []
        if self in diagrams:
            diagrams.remove(self)

    def getCanvas(self):
        return self.canvas

    def onChange(self):
        self.canvas.dispatchEvent(window.CustomEvent.new("modified", {
            "bubbles": True
        }))

    def get_allowed_blocks(cls, block_cls_name: str, for_drop=False) -> Dict[str, Type[Shape]]:
        raise NotImplementedError()

    def addBlock(self, block):
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)

        block.create(self)
        self.children.append(block)

    def addConnection(self, connection):
        """ Handle a completed connection and add it to the diagram. """
        self.connections.append(connection)
        connection.route(self, self.children)

    def deleteConnection(self, connection):
        if connection in self.connections:
            connection.delete()
            self.connections.remove(connection)

    def deleteBlock(self, block):
        block.delete()
        if owner := block.owner():
            owner.children.remove(block)

        # Also delete all connections with this block or its ports
        to_remove = []
        ports = getattr(block, 'ports', [])
        for c in self.connections:
            if c.start == block or c.start in ports or c.finish == block or c.finish in ports:
                to_remove.append(c)
        for c in to_remove:
            self.deleteConnection(c)

    def allowsConnection(self, a, b):
        return True

    def connect_specific(self, a, b, cls):
        # Find the associated representation
        repr_cls = self.config.get_repr_for_connection(cls)
        connection = repr_cls(start=a, finish=b, waypoints=[], diagram=self.diagram_id)
        self.addConnection(connection)
        return connection

    def connect(self, a, b):
        ta, tb = a.getEntityForConnection(), b.getEntityForConnection()
        clss = self.config.get_allowed_connections(ta, tb) + self.config.get_allowed_connections(ta, Any)
        if not clss:
            d = InfoDialog('Can not connect', f"A {type(a).__name__} can not be connected to a {type(b).__name__}")
            return
        if len(clss) > 1:
            # Let the user select Connection type
            self.selectConnectionClass(clss, lambda cls: self.connect_specific(a, b, cls))
        else:
            self.connect_specific(a, b, clss[0])

    def changeFSM(self, fsm):
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)
        self.mouse_events_fsm = fsm

    def getConnectionsToShape(self, widget):
        result = [c for c in self.connections if widget.isConnected(c.start) or widget.isConnected(c.finish)]
        return result

    def rerouteConnections(self, widget):
        if isinstance(widget, Relationship):
            widget.reroute(self.children)
        else:
            for c in self.getConnectionsToShape(widget):
                c.reroute(self.children)

    def bind(self, canvas):
        self.canvas = canvas
        canvas.bind('click', self.onClick)
        canvas.bind('mouseup', self.onMouseUp)
        canvas.bind('mousemove', self.onMouseMove)
        canvas.bind('mousedown', self.onMouseDown)
        canvas.bind('handle_drag_start', self.handleDragStart)
        canvas.bind('drop', self.onDrop)
        canvas.serialize = self.serialize

        @bind(canvas, 'dragover')
        def ondragover(ev):
            ev.dataTransfer.dropEffect = 'move'
            ev.preventDefault()


        document.bind('keydown', self.onKeyDown)
        for widget in self.widgets:
            widget(self)

    def clickChild(self, widget, ev):
        # Check if the ownership of the block has changed
        pos = getMousePos(ev)
        self.takeOwnership(widget, pos, self)


    def mouseDownChild(self, widget, ev, update_func=None):
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = ResizeFSM(self)
        self.mouse_events_fsm.mouseDownShape(self, widget, ev)

        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            old_values = asdict(widget)
            widget.update(new_data)

        if update_func is None:
            update_func = uf


        # Also notify any listeners that an object was selected
        details = json.dumps(widget, cls=ExtendibleJsonEncoder)
        event_detail = {
            "values": details,
            "update": update_func,
            "object": widget
        }
        self.trigger_event(widget, 'shape_selected', event_detail)

    def trigger_event(self, widget, event_name, event_detail):
        self.canvas.dispatchEvent(window.CustomEvent.new(event_name, {
            "bubbles":True,
            "detail": event_detail
        }))


    def mouseDownConnection(self, connection, ev, update_function=None):
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = RerouteStates(self)
        self.mouse_events_fsm.mouseDownConnection(self, connection, ev)

        # Also notify any listeners that an object was selected
        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            connection.update(new_data)

        update_function = update_function or uf
        details = json.dumps(connection, cls=ExtendibleJsonEncoder)
        event_detail = {
            "values": details,
            "update": update_function,
            "object": connection
        }
        self.trigger_event(connection, 'shape_selected', event_detail)

    def takeOwnership(self, widget, pos, ex_owner):
        pass

    def onClick(self, ev):
        pass

    def onMouseDown(self, ev):
        self.mouse_events_fsm and self.mouse_events_fsm.mouseDownBackground(self, ev)

    def onMouseUp(self, ev):
        self.mouse_events_fsm and self.mouse_events_fsm.onMouseUp(self, ev)

    def onMouseMove(self, ev):
        self.mouse_events_fsm and self.mouse_events_fsm.onMouseMove(self, ev)

    def onKeyDown(self, ev):
        self.mouse_events_fsm and self.mouse_events_fsm.onKeyDown(self, ev)

    def handleDragStart(self, ev):
        self.mouse_events_fsm and self.mouse_events_fsm.handleDragStart(self, ev)

    def onHover(self):
        pass

    def getMenu(self):
        pass

    def onDrop(self, ev):
        """ Handler for the 'drop' event.
            Without having a modelling context, a "drop" is meaningless.
            Child classes can implement this function.
        """
        pass


    def serialize(self):
        # Output the model in JSON format
        details = {'blocks': self.children,
                   'connections': self.connections}
        return json.dumps(details, cls=ExtendibleJsonEncoder)

    def updateElement(self, element):
        if is_dataclass(element):
            self.datastore and self.datastore.update(element)

    def selectConnectionClass(self, clss, cb):
        """ Function that builds a dialog for selecting a specific connection type.
            When a selection is made, a callback is called with the selected class.
        """
        d = Dialog()
        d.panel <= html.DIV("Please select the type of connection")
        l = html.UL()
        selection = None
        def add_option(cls):
            o = html.LI(cls.__name__)
            @bind(o, 'click')
            def select(ev):
                cb(cls)
                d.close()
            return o
        for cls in clss:
            l <= add_option(cls)
        d.panel <= l

diagrams = []


def nop(ev):
    return

def createSvgButtonBar(canvas, icons, callbacks, hover_texts=None, x=0, y=0):
    # Count the buttons
    width = 40
    margin = 2
    nr_buttons = len(icons)
    # Draw the border of the box
    # Create the buttons
    for i, (icon, cb) in enumerate(zip(icons, callbacks)):
        xi = x+i*(margin+width)
        r = svg.rect(x=xi, y=y, width=width, height=width, fill='#EFF0F1', stroke='#000000',
                           stroke_width='1', ry='2')
        g = icon(xi+2*margin, y+2*margin, width-4*margin)
        canvas <= r
        canvas <= g
        r.bind('click', cb)
        g.bind('click', cb)


class EditingModeWidget:
    btn_size = 20

    def __init__(self, diagram):
        self.diagram = ref(diagram)
        createSvgButtonBar(diagram.canvas, [svg_shapes.pointer_icon, svg_shapes.chain_icon],
                           [self.onBlockMode, self.onConnectMode], x=100, y=5)

    def onBlockMode(self, ev):
        self.diagram().changeFSM(None)
    def onConnectMode(self, ev):
        self.diagram().changeFSM(ConnectionEditor())


class BlockCreateWidget:
    height = 40
    margin = 10
    def __init__(self, diagram):
        def bindFunc(index, representation):
            """ Create a lambda function for creating a specific block type """
            return lambda ev: self.onMouseDown(ev, index, representation)

        self.diagram = ref(diagram)
        self.diagram_id = diagram.diagram_id
        blocks = {k: b for k, b in diagram.get_allowed_blocks().items() if not b.is_instance_of()}

        g = svg.g()
        # Draw the border of the widget
        _ = g <= svg.rect(x=0, width=2*self.margin+1.6*self.height, y=0, height=len(blocks)*(self.height+self.margin)+self.margin,
                      fill='white', stroke='black', stroke_width="2")
        for i, (name, block_cls) in enumerate(blocks.items()):
            repr_cls = block_cls.representation_cls()
            console.log(f"Creating element of type {repr_cls.__name__} -- shape: {repr_cls.getShapeDescriptor()}")
            representation = repr_cls(x=self.margin, y=i*(self.height+self.margin)+self.margin,
                         height=self.height, width=1.6*self.height)
            representation.logical_class = block_cls
            shape = representation.getShape()
            _ = g <= shape
            _ = g <= svg.text(name, x=self.margin+5, y=i*(self.height+self.margin)+self.margin + self.height/1.5,
                font_size=12, font_family='arial')

            shape.bind('mousedown', bindFunc(i, representation))
        _ = diagram.canvas <= g

    def onMouseDown(self, ev, index, representation):
        diagram = self.diagram()
        if diagram is None:
            return
        # Simply create a new block at the default position.
        cls = type(representation)
        instance = cls(x=300, y=300, height=self.height, width=int(1.6*self.height), diagram=self.diagram_id)
        instance.logical_class = representation.logical_class
        diagram.datastore.add(instance)
        diagram.addBlock(instance)


def load_diagram(diagram_id, diagram_cls, config: DiagramConfiguration, datastore, canvas):
    diagram = diagram_cls(config, [BlockCreateWidget, EditingModeWidget], datastore, diagram_id)
    diagrams.append(diagram)
    diagram.bind(canvas)
    diagram.load_diagram()

    canvas.bind(Diagram.ConnectionModeEvent, lambda ev: diagram.changeFSM(ConnectionEditor()))
    canvas.bind(Diagram.NormalModeEvent, lambda ev: diagram.changeFSM(None))
    return diagram

