"""

Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""


from browser import document, svg, console, window, bind, html, DOMNode
from browser.widgets.dialog import Dialog, InfoDialog


from typing import Any, Self, List, Dict, Type, Optional
from dataclasses import dataclass, field, asdict, is_dataclass, fields
from weakref import ref
import enum
from math import inf
import json
from point import Point
from shapes import (Shape, CP, Relationship, getMousePos, Orientations, OwnerInterface, handle_class)
from data_store import DataStore, ExtendibleJsonEncoder, ReprCategory
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

def moveSingleHandle(decorators, widget, orientation) -> None:
    d = decorators[orientation]
    x, y, width, height = [getattr(widget, k) for k in ['x', 'y', 'width', 'height']]
    d['cx'], d['cy'] = [int(i) for i in locations[orientation](x, y, width, height)]

def moveHandles(decorators, widget, orientation) -> None:
    # Determine which markers to move
    for o in to_update[orientation]:
        moveSingleHandle(decorators, widget, o)

def moveAll(widget, decorators) -> None:
    for o in Orientations:
        moveSingleHandle(decorators, widget, o)

def mk_scrollable(canvas: DOMNode):
    """ Make an SVG widget scrollable. """
    @bind(canvas, 'wheel')
    def scroll_wheel(ev):
        ev.preventDefault()
        viewbox = canvas.attrs.get('viewBox', None)
        if not viewbox:
            viewbox = f'0 0 {canvas.width} {canvas.height}'
        values = [float(v) for v in viewbox.split()]

        if ev.shiftKey:
            factor = values[2] * ev.deltaY / 132 / 20
            values[0] += factor
        elif ev.ctrlKey:
            factor = 1.1 ** (ev.deltaY / 132)
            values[2] *= factor
            values[3] *= factor
        else:
            factor = values[3] * ev.deltaY / 132 / 20
            values[1] += factor
        canvas.attrs['viewBox'] = ' '.join(str(v) for v in values)


class BehaviourFSM:
    # FIXME: Remove the diagrams from all these functions.
    def mouseDownShape(self, diagram, widget, ev) -> None:
        pass
    def mouseDownConnection(self, diagram, widget, ev) -> None:
        pass
    def mouseDownPort(self, diagram, widget, ev) -> None:
        pass
    def mouseDownBackground(self, diagram, ev) -> None:
        pass
    def onMouseUp(self, diagram, ev) -> None:
        pass
    def onMouseMove(self, diagram, ev) -> None:
        pass
    def onKeyDown(self, diagram, ev) -> None:
        pass
    def delete(self, diagram) -> None:
        """ Called when the FSM is about to be deleted"""
        pass
    def is_at_rest(self) -> bool:
        """ Returns True if the state machine is not in the middle of something. """
        raise NotImplementedError()


class ResizeStates(enum.IntEnum):
    NONE = enum.auto()
    DECORATED = enum.auto()
    MOVING = enum.auto()
    RESIZING = enum.auto()
    MULTISELECT = enum.auto()
    AREA_SELECT = enum.auto()

class ResizeFSM(BehaviourFSM):
    def __init__(self, diagram):
        super().__init__()
        self.state: ResizeStates = ResizeStates.NONE
        self.diagram = diagram
        self.selection: List[Shape] = []
        self.initial_pos: List[Point] = []
        self.decorators = {}
        self.outlines = []
        self.selection_area = None

    def is_at_rest(self) -> bool:
        return self.state == ResizeStates.NONE

    def mouseDownShape(self, diagram, widget, ev) -> None:
        if self.state != ResizeStates.NONE and widget not in self.selection:
            if ev.ctrlKey or ev.shiftKey:
                self.select(widget)
            else:
                self.unselect()
        if self.state == ResizeStates.NONE:
            self.select(widget)
        self.state = ResizeStates.MOVING
        self.dragstart = getMousePos(ev)
        self.initial_pos = [w.getPos() for w in self.selection]
        ev.stopPropagation()
        ev.preventDefault()

    def mouseDownConnection(self, diagram, widget, ev) -> None:
        # We need to change the state machine
        if self.state != ResizeStates.NONE:
            self.unselect()
        fsm = RerouteStates(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownConnection(diagram, widget, ev)

    def mouseDownBackground(self, diagram, ev) -> None:
        if self.selection and ev.target in [w.shape for w in self.selection]:
            self.state = ResizeStates.MOVING
            return
        if self.state in [ResizeStates.NONE, ResizeStates.DECORATED, ResizeStates.MULTISELECT]:
            self.state = ResizeStates.AREA_SELECT
            pos = getMousePos(ev)
            self.initial_pos = pos
            self.selection_area = svg.rect(x=pos.x, y=pos.y, width=0, height=0, fill='none', stroke='black')
            _ = self.diagram.canvas <= self.selection_area

    def onMouseUp(self, diagram, ev) -> None:
        if self.state == ResizeStates.AREA_SELECT:
            if not (ev.ctrlKey or ev.shiftKey):
                self.unselect()

            pos = getMousePos(ev)
            xs = [self.initial_pos.x, pos.x]
            ys = [self.initial_pos.y, pos.y]
            minx, maxx = min(xs), max(xs)
            miny, maxy = min(ys), max(ys)

            for w in self.diagram.children:
                if w.x < minx or w.y < miny or w.x+w.width > maxx or w.y+w.height >  maxy:
                    continue
                if w in self.selection:
                    continue
                self.select(w)
            self.selection_area.remove()
            self.selection_area = None
            self.state = {0: ResizeStates.NONE, 1: ResizeStates.DECORATED}.get(len(self.selection), ResizeStates.MULTISELECT)
            return

        # If an object was being moved, evaluate if it changed owner
        if self.state == ResizeStates.MOVING and len(self.selection)==1:
            pos = getMousePos(ev)
            widget = self.selection[0]
            diagram.evaluateOwnership(widget, pos, widget.owner)
        if self.state in [ResizeStates.MOVING, ResizeStates.RESIZING]:
            for widget in self.selection:
                self.diagram.updateElement(widget)
            self.state = ResizeStates.DECORATED if len(self.selection) == 1 else ResizeStates.MULTISELECT

    def onMouseMove(self, diagram, ev) -> None:
        if self.state in [ResizeStates.NONE, ResizeStates.DECORATED, ResizeStates.MULTISELECT]:
            return
        if self.state == ResizeStates.AREA_SELECT:
            pos = getMousePos(ev)
            if pos.x > self.initial_pos.x:
                self.selection_area.attrs['width'] = pos.x - self.initial_pos.x
            else:
                self.selection_area.attrs['width'] = self.initial_pos.x - pos.x
                self.selection_area.attrs['x'] = pos.x
            if pos.y > self.initial_pos.y:
                self.selection_area.attrs['height'] = pos.y - self.initial_pos.y
            else:
                self.selection_area.attrs['height'] = self.initial_pos.y - pos.y
                self.selection_area.attrs['y'] = pos.y
            return
        delta = getMousePos(ev) - self.dragstart
        if self.state == ResizeStates.RESIZING:
            self.onDrag(self.initial_pos[0], self.initial_size, delta)
        if self.state == ResizeStates.MOVING:
            for widget, initial_pos in zip(self.selection, self.initial_pos):
                widget.setPos(initial_pos + delta)
                diagram.rerouteConnections(widget)

    def delete(self, diagram) -> None:
        """ Called when the FSM is about to be deleted"""
        if self.state != ResizeStates.NONE:
            self.unselect()

    def startResize(self, widget, orientation, ev) -> None:
        self.dragstart = getMousePos(ev)
        self.state = ResizeStates.RESIZING
        self.initial_pos = [w.getPos() for w in self.selection]
        self.initial_size = widget.getSize()

    def clear_decorations(self) -> None:
        for dec in self.decorators.values():
            dec.remove()
        self.decorators = {}
        for widget in self.selection:
            widget.unsubscribe(resize_role)

    def unselect(self) -> None:
        self.clear_decorations()
        for widget in self.selection:
            widget.highlight(False)
            if widget.isResizable():
                widget.unsubscribe(resize_role)
        self.selection = []
        self.outlines = []
        self.state = ResizeStates.NONE

    def select(self, widget) -> None:
        if widget in self.selection:
            return
        widget.highlight()
        self.selection.append(widget)

        if len(self.selection) == 1 and widget.isResizable():
            self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2", data_index=int(k), Class=handle_class)
                               for k in Orientations}
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
                _ = self.diagram.canvas <= d
                bind_decorator(d, orientation)

            widget.subscribe(resize_role, lambda w: moveAll(w, self.decorators))
            self.state = ResizeStates.DECORATED
        else:
            # Remove the decorations from the first selection
            self.clear_decorations()
            self.state = ResizeStates.MULTISELECT

    def onDrag(self, origin, original_size, delta) -> None:
        if len(self.selection) != 1:
            return
        widget = self.selection[0]
        dx, dy, sx, sy, mx, my = orientation_details[self.dragged_handle]
        d = self.decorators[self.dragged_handle]
        shape = widget
        movement = Point(x=delta.x * dx, y=delta.y * dy)
        # alert(f"{delta}, {dx}, {dy}, {sx}, {sy}")
        shape.setPos(origin + movement)
        resizement = Point(x=original_size.x + sx * delta.x, y=original_size.y + sy * delta.y)
        shape.setSize(resizement)

        moveHandles(self.decorators, shape, self.dragged_handle)
        self.diagram.rerouteConnections(shape)

    def onKeyDown(self, diagram, ev) -> None:
        if ev.key == 'Delete':
            # Check if the user indeed wants to delete something.
            if self.state != ResizeStates.NONE:
                widgets = self.selection
                if len(widgets) > 1:
                    d = Dialog(f'Delete selection', ok_cancel=True)
                    _ = d.panel <= f'Delete blocks'
                else:
                    d = Dialog(f'Delete {type(widgets[0]).__name__}', ok_cancel=True)
                    _ = d.panel <= f'Delete {type(widgets[0]).__name__}'
                names = ', '.join(getattr(f'"{w}"', 'name', f'[{type(w).__name__}]') for w in widgets)
                _ = d.panel <= f' {names}'

                @bind(d.ok_button, "click")
                def ok(ev):
                    d.close()
                    self.unselect()
                    for widget in widgets:
                        diagram.deleteBlock(widget)
        elif ev.key == 'Escape':
            if self.state not in [ResizeStates.NONE, ResizeStates.DECORATED]:
                self.state = ResizeStates.DECORATED


class ReroutingState(enum.IntEnum):
    NONE = enum.auto()
    DECORATED = enum.auto()
    HANDLE_SELECTED = enum.auto()
    POTENTIAL_DRAG = enum.auto()
    DRAGGING = enum.auto()

class RerouteStates(BehaviourFSM):
    States = ReroutingState
    def __init__(self, diagram):
        super().__init__()
        self.state = self.States.NONE
        self.diagram = diagram
        self.decorators = []
        self.dragged_index = None
        self.drag_start = Point(0, 0)
        self.initial_pos = Point(0, 0)

    def is_at_rest(self) -> bool:
        return self.state == self.States.NONE

    def mouseDownShape(self, diagram, widget, ev) -> None:
        # We need to change the state machine
        if self.state != self.States.NONE:
            self.clear_decorations()
        fsm = ResizeFSM(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownShape(diagram, widget, ev)


    def mouseDownConnection(self, diagram, widget, ev) -> None:
        if self.state != self.States.NONE:
            self.clear_decorations()
        self.widget = widget
        if not self.decorators:
            self.decorate()
        self.state = self.States.POTENTIAL_DRAG
        self.dragstart = getMousePos(ev)
        self.dragged_index = None
        ev.stopPropagation()
        ev.preventDefault()

    def mouseDownBackground(self, diagram, ev) -> None:
        if diagram.selection and ev.target == diagram.selection.shape:
            self.state = self.States.DRAGGING
            return
        if self.state != self.States.NONE:
            self.clear_decorations()
        self.state = self.States.NONE

    def handleDragStart(self, index, ev) -> None:
        self.state = self.States.DRAGGING
        ev.stopPropagation()
        ev.preventDefault()

    def dragHandle(self, ev) -> None:
        delta = getMousePos(ev) - self.drag_start
        new_pos = self.initial_pos + delta
        handle = self.decorators[self.dragged_index]
        if self.handle_orientation[self.dragged_index] == 'X':
            handle['x1'] = handle['x2'] = new_pos.x
            self.widget.waypoints[self.dragged_index] = Point(x=new_pos.x, y=inf)
        else:
            handle['y1'] = handle['y2'] = new_pos.y
            self.widget.waypoints[self.dragged_index] = Point(x=inf, y=new_pos.y)

    def onMouseUp(self, diagram, ev) -> None:
        if self.state in [self.States.POTENTIAL_DRAG, self.States.DRAGGING]:
            self.widget.router.dragEnd(self.diagram.canvas)
            if self.state == self.States.DRAGGING:
                self.state = self.States.HANDLE_SELECTED
            else:
                self.state = self.States.DECORATED
            diagram.updateElement(self.widget)

    def onMouseMove(self, diagram, ev) -> None:
        if self.state in [self.States.NONE, self.States.DECORATED, self.States.HANDLE_SELECTED]:
            return
        pos = getMousePos(ev)
        if self.state == self.States.POTENTIAL_DRAG:
            delta = pos - self.dragstart
            if delta.norm() > 10:
                self.widget.router.createWaypointByDrag(pos, self.widget, self.diagram.canvas)
                self.state = self.States.DRAGGING
        if self.state == self.States.DRAGGING:
            self.widget.router.dragHandle(pos)
            diagram.rerouteConnections(self.widget)

    def onKeyDown(self, diagram, ev) -> None:
        if ev.key == 'Delete':
            if self.state == self.States.DECORATED:
                # Delete the connection
                self.clear_decorations()
                self.state = self.States.NONE
                diagram.deleteConnection(self.widget)
            elif self.state != self.States.NONE:
                self.widget.router.deleteWaypoint()
                diagram.rerouteConnections(self.widget)

    def delete(self, diagram) -> None:
        if self.state != self.States.NONE:
            self.clear_decorations()

    def decorate(self) -> None:
        self.widget.router.decorate(self.widget, self.diagram.canvas)

    def clear_decorations(self) -> None:
        self.widget.router.clear_decorations()


class ConnectionStates(enum.IntEnum):
    NONE = enum.auto()
    A_SELECTED = enum.auto()
    RECONNECTING = enum.auto()

class ConnectionRoles(enum.IntEnum):
    START = enum.auto()
    FINISH = enum.auto()

class ConnectionEditor(BehaviourFSM):
    States = ConnectionStates
    def __init__(self):
        self.state = self.States.NONE
        self.a_party = None
        self.connection: Optional[Relationship] = None
        self.b_connection_role = None
        self.path = None
    def is_at_rest(self) -> bool:
        return self.state == self.States.NONE
    def mouseDownShape(self, diagram, widget, ev) -> None:
        party = widget.getConnectionTarget(ev)
        if self.state in [self.States.A_SELECTED, self.States.RECONNECTING]:
            if diagram.allowsConnection(self.a_party, party):
                if self.state == self.States.A_SELECTED:
                    diagram.connect(self.a_party, party)
                elif self.state == self.States.RECONNECTING:
                    match self.b_connection_role:
                        case ConnectionRoles.START:
                            self.connection.start = party
                        case ConnectionRoles.FINISH:
                            self.connection.finish = party
                    diagram.reroute(self.connection)

                self.path.remove()
                self.state = self.States.NONE
        elif self.state == self.States.NONE:
            self.state = self.States.A_SELECTED
            self.a_party = party
            # Create a temporary path to follow the mouse
            x, y = [int(i) for i in (self.a_party.getPos() + self.a_party.getSize()/2).astuple()]
            self.path = svg.line(x1=x, y1=y, x2=x, y2=y, stroke_width=2, stroke="gray")
            _ = diagram.canvas <= self.path
    def onMouseMove(self, diagram, ev) -> None:
        if self.state == self.States.NONE:
            return
        pos = getMousePos(ev)
        # Let the temporary line follow the mouse.
        # But ensure it doesn't hide the B-shape
        v = pos - self.a_party.getPos()
        delta = (v.normalize()) * 2
        self.path['x2'], self.path['y2'] = [int(i) for i in (pos - delta).astuple()]
    def delete(self, diagram) -> None:
        if self.state != self.States.NONE:
            self.path.remove()
    def onKeyDown(self, diagram, ev) -> None:
        if ev.key == 'Escape':
            if self.state == self.States.A_SELECTED:
                # Delete the connection
                self.path.remove()
                self.state = self.States.NONE


@dataclass
class DiagramConfiguration:
    connections_from: Dict[type, Dict[type, List[type]]]
    all_entities: Dict[str, type]

    def get_allowed_connections(self, block_from_cls, block_to_cls) -> List[type]:
        return self.connections_from.get(block_from_cls, {}).get(block_to_cls, [])



class Diagram(OwnerInterface):
    """ Base Class that holds and manages the elements of a diagram. Child classes expose definitions for a
        specific type of diagram, like the blocks allowed in it.
        The class queries the classes of these elements to see how they should be treated.
        The actual interactions with elements are controlled through state machines.

    """
    ModifiedEvent = 'modified'
    ConnectionModeEvent = 'ConnectionMode'
    NormalModeEvent = 'NormalMode'
    default_block_details = dict(x=300, y=300, height=64, width=40)

    class Widget:
        """ Base class of "widgets", things that can be placed in a diagram to trigger various actions.
            Like creating new blocks, or switch between different editing states.
        """
        def __init__(self, diagram: 'Diagram'):
            pass

    def __init__(self, config: DiagramConfiguration, widgets: List[Widget]):
        self.mouse_events_fsm: Optional[BehaviourFSM] = ResizeFSM(self)
        self.children: List[Shape] = []
        self.connections: List[Relationship] = []
        self.widgets: List[Diagram.Widget] = widgets
        self.config: DiagramConfiguration = config
        self.diagram_id: int = 0
        self.canvas: Optional[DOMNode] = None  # The SVG element in which the diagram is drawn.

    def get_representation_category(self, block_cls) -> ReprCategory:
        return ReprCategory.block

    def close(self):
        """ Close the diagram """
        # Release the resources of this diagram and delete references to it.
        self.children = []
        self.connections = []
        if self in diagrams:
            diagrams.remove(self)

    def getCanvas(self) -> DOMNode:
        return self.canvas

    def onChange(self) -> None:
        self.canvas.dispatchEvent(window.CustomEvent.new("modified", {
            "bubbles": True
        }))

    @classmethod
    def get_allowed_blocks(cls, block_cls_name: str, for_drop=False) -> Dict[str, Type[Shape]]:
        raise NotImplementedError()

    def createNewBlock(self, template: Shape) -> Shape:
        """ Function to create a totally new block from a template.
            Called by e.g. the BlockCreateWidget.
            The template is already a shape (the one in the create widget) that was clicked on.
            Some of its elements need to be copied to the new shape.
        """
        # Simply create a new block at the default position.
        block_cls = template.logical_class
        details = self.default_block_details.copy()
        category = self.get_representation_category(block_cls)
        details['category'] = category
        self.place_block(block_cls, details)

        repr_cls = block_cls.get_representation_cls(category)
        instance = repr_cls(diagram=self.diagram_id, **details)
        instance.model_entity = block_cls(parent=self.diagram_id)
        self.addBlock(instance)
        return instance

    def place_block(self, block_cls: Type[Shape], details):
        """ Called to allow a new block to be located by the diagram. For example snapping. """
        pass

    def addBlock(self, block: Shape) -> None:
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)

        block.create(self)
        self.children.append(block)

    def addConnection(self, connection: Relationship) -> None:
        """ Handle a completed connection and add it to the diagram. """
        self.connections.append(connection)
        connection.create(self, self.children)

    def deleteConnection(self, connection: Relationship) -> None:
        if connection in self.connections:
            connection.delete()
            self.connections.remove(connection)

    def deleteBlock(self, block: Shape) -> None:
        block.delete()
        if block.repr_category() == ReprCategory.block:
            # Remove the block from the diagram's list of children
            if owner := block.owner():
                if block in owner.children:
                    owner.children.remove(block)
        elif block.repr_category() == ReprCategory.message:
            # Remove the message from the relationship's list of messages
            for c in self.connections:
                if c.Id == block.parent:
                    if block in c.messages:
                        c.messages.remove(block)

        # Also delete all connections with this block or its ports
        to_remove = []
        ports = getattr(block, 'ports', [])
        for c in self.connections:
            if c.start == block or c.start in ports or c.finish == block or c.finish in ports:
                to_remove.append(c)
        for c in to_remove:
            self.deleteConnection(c)

    def allowsConnection(self, a, b) -> bool:
        return True

    def connect(self, a, b) -> None:
        """ Connect two blocks a and b.. """
        raise NotImplementedError()

    def changeFSM(self, fsm) -> None:
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)
        self.mouse_events_fsm = fsm

    def getConnectionsToShape(self, widget) -> List[Relationship]:
        result = [c for c in self.connections if widget.isConnected(c.start) or widget.isConnected(c.finish)]
        return result

    def rerouteConnections(self, widget) -> None:
        if isinstance(widget, Relationship):
            widget.reroute(self.children)
        else:
            for c in self.getConnectionsToShape(widget):
                c.reroute(self.children)

    def bind(self, canvas) -> None:
        mk_scrollable(canvas)
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

    def clickChild(self, widget, ev) -> None:
        # Check if the ownership of the block has changed
        print("Click Child")
        pos = getMousePos(ev)
        self.takeOwnership(widget, pos, self)

    def dblclickChild(self, widget, ev) -> None:
        # To be overloaded by child classes
        pass

    def mouseDownChild(self, widget, ev) -> None:
        print("Mousedown Child")
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = ResizeFSM(self)
        self.mouse_events_fsm.mouseDownShape(self, widget, ev)

    def trigger_event(self, widget, event_name, event_detail) -> None:
        self.canvas.dispatchEvent(window.CustomEvent.new(event_name, {
            "bubbles":True,
            "detail": event_detail
        }))


    def mouseDownConnection(self, connection, ev, update_function=None) -> None:
        if not self.mouse_events_fsm or self.mouse_events_fsm.is_at_rest():
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

    def takeOwnership(self, widget, pos, ex_owner) -> None:
        pass

    def onClick(self, ev) -> None:
        pass

    def onMouseDown(self, ev) -> None:
        self.mouse_events_fsm and self.mouse_events_fsm.mouseDownBackground(self, ev)

    def onMouseUp(self, ev) -> None:
        self.mouse_events_fsm and self.mouse_events_fsm.onMouseUp(self, ev)

    def onMouseMove(self, ev) -> None:
        self.mouse_events_fsm and self.mouse_events_fsm.onMouseMove(self, ev)

    def onKeyDown(self, ev) -> None:
        self.mouse_events_fsm and self.mouse_events_fsm.onKeyDown(self, ev)

    def handleDragStart(self, ev) -> None:
        self.mouse_events_fsm and self.mouse_events_fsm.handleDragStart(self, ev)

    def onHover(self) -> None:
        pass

    def onDrop(self, ev) -> None:
        """ Handler for the 'drop' event.
            Without having a modelling context, a "drop" is meaningless.
            Child classes can implement this function.
        """
        pass


    def serialize(self) -> str:
        # Output the model in JSON format
        details = {'blocks': self.children,
                   'connections': self.connections}
        return json.dumps(details, cls=ExtendibleJsonEncoder)

    def selectConnectionClass(self, clss, cb) -> None:
        """ Function that builds a dialog for selecting a specific connection type.
            When a selection is made, a callback is called with the selected class.
        """
        d = Dialog('Select relationship')
        _ = d.panel <= html.DIV("Please select the type of connection")
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
            _ = l <= add_option(cls)
        _ = d.panel <= l

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
        r = svg.rect(id=cb.__name__, x=xi, y=y, width=width, height=width, fill='#EFF0F1', stroke='#000000',
                           stroke_width='1', ry='2')
        g = icon(xi+2*margin, y+2*margin, width-4*margin)
        _ = canvas <= r
        _ = canvas <= g
        r.bind('click', cb)
        g.bind('click', cb)


class EditingModeWidget(Diagram.Widget):
    btn_size = 20

    def __init__(self, diagram: Diagram):
        self.diagram = ref(diagram)
        createSvgButtonBar(diagram.canvas, [svg_shapes.pointer_icon, svg_shapes.chain_icon],
                           [self.onBlockMode, self.onConnectMode], x=100, y=5)

    def onBlockMode(self, ev):
        self.diagram().changeFSM(None)
    def onConnectMode(self, ev):
        self.diagram().changeFSM(ConnectionEditor())


class BlockCreateWidget(Diagram.Widget):
    height = 40
    margin = 10
    def __init__(self, diagram: Diagram):
        def bindFunc(index, representation):
            """ Create a lambda function for creating a specific block type """
            return lambda ev: self.onMouseDown(ev, index, representation)

        self.diagram = ref(diagram)
        self.diagram_id = diagram.diagram_id
        blocks = {k: b for k, b in diagram.get_allowed_blocks().items() if not b.is_instance_of()}

        g = svg.g(id=type(self).__name__)
        # Draw the border of the widget
        _ = g <= svg.rect(x=0, width=2*self.margin+1.6*self.height, y=0, height=len(blocks)*(self.height+self.margin)+self.margin,
                      fill='white', stroke='black', stroke_width="2")
        for i, (name, block_cls) in enumerate(blocks.items()):
            entity = block_cls()
            repr_cls = entity.get_representation_cls(ReprCategory.block)
            representation = repr_cls(x=self.margin, y=i*(self.height+self.margin)+self.margin,
                         height=self.height, width=1.6*self.height, model_entity=entity)
            representation.logical_class = block_cls
            shape = representation.getShape()
            shape.attrs['id'] = f'create_{name}_btn'
            _ = g <= shape
            _ = g <= svg.text(name, x=self.margin+5, y=i*(self.height+self.margin)+self.margin + self.height/1.5,
                font_size=12, font_family='arial')

            shape.bind('mousedown', bindFunc(i, representation))
        _ = diagram.canvas <= g

    def onMouseDown(self, ev, index, representation):
        diagram = self.diagram()
        if diagram is None:
            return
        diagram.createNewBlock(representation)


def load_diagram(diagram_id: int, diagram_cls: Diagram, config: DiagramConfiguration, datastore, canvas):
    diagram: Diagram = diagram_cls(config, [BlockCreateWidget, EditingModeWidget], datastore, diagram_id)
    diagrams.append(diagram)
    diagram.bind(canvas)
    diagram.load_diagram()

    canvas.bind(Diagram.ConnectionModeEvent, lambda ev: diagram.changeFSM(ConnectionEditor()))
    canvas.bind(Diagram.NormalModeEvent, lambda ev: diagram.changeFSM(None))
    return diagram

