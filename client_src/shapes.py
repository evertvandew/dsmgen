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
from browser import svg, window, console, html
from context_menu import mk_context_menu
import enum
from weakref import ref
import math
from math import inf
from dataclasses import dataclass, field
import json
from typing import List, Dict, Self, Optional
from square_routing import routeSquare
from point import Point
from svg_shapes import (BasicShape, renderText, VAlign, HAlign, line_patterns, path_ending, path_origin)
from storable_element import StorableElement, ReprCategory
from copy import copy

# CSS class given to all handles shapes are decorated with.
handle_class = 'line_handle'


def getMousePos(ev):
    CTM = ev.target.getScreenCTM()
    return Point(x=int((ev.clientX - CTM.e)/CTM.a), y=int((ev.clientY-CTM.f)/CTM.d))


class Orientations(enum.IntEnum):
    TL = 1
    TOP = 2
    TR = 3
    RIGHT = 4
    BR = 5
    BOTTOM = 6
    BL = 7
    LEFT = 8

class BlockOrientations(enum.IntEnum):
    TOP = Orientations.TOP
    RIGHT = Orientations.RIGHT
    BOTTOM = Orientations.BOTTOM
    LEFT = Orientations.LEFT


id_counter = 0
def getId():
    global id_counter
    id_counter += 1
    return id_counter


class HIDDEN:
    def __init__(self, t):
        self.type = t

def Text(text_attr):
    """ Depending on the shape, the text is obtained from any attribute in the details.
        So we make the text widget available though a function that bind it to an attribute.
    """
    class TextWidget(BasicShape):
        style_items = dict(font='Arial', fontsize='16', textcolor='#000000', xmargin=2, ymargin=2, halign=HAlign.CENTER, valign=VAlign.CENTER)
        @classmethod
        def getShape(cls, details):
            # The text lines are wrapped in a group.
            g = svg.g()
            g <= renderText(getattr(details, text_attr, ''), details)
            return g
        @classmethod
        def updateShape(cls, shape, details):
            # Simply delete the previous text and write anew.
            shape.clear()
            shape <= renderText(getattr(details, text_attr, ''), details)
    return TextWidget

class UpdateType(enum.IntEnum):
    add = enum.auto()
    update = enum.auto()
    delete = enum.auto()

class OwnerInterface:
    """ Define an interface through which a shape interacts with its parent.
        A parent can either be another shape, or the SVG canvas itself.

        Python doesn't need interfaces, this is added for documentation purposes.
    """
    def clickChild(self, widget, ev):
        raise NotImplementedError()
    def dblclickChild(self, widget, ev):
        raise NotImplementedError()
    def mouseDownChild(self, widget, ev):
        raise NotImplementedError()
    def mouseDownConnection(self, connection, ev):
        raise NotImplementedError()
    def getCanvas(self):
        raise NotImplementedError()
    def child_update(self, action: UpdateType, child: StorableElement):
        """ Call this function when a child is updated in a way that needs to be persisted. """
        # The default action is to do nothing. Diagrams with persistent storage should overload this.
        pass
    def __le__(self, svg_widget):
        raise NotImplementedError()
    def evaluateOwnership(self, widget, pos, ex_owner):
        # Check this widget is dropped on me
        if hasattr(self, 'owner'):
            if pos.x < self.x or pos.x > self.x+self.width or pos.y < self.y or pos.y > self.y+self.height:
                owner = self.owner()
                return owner.evaluateOwnership(widget, pos, ex_owner)
        # Check if this widget is actually dropped on a child container.
        containers: List[OwnerInterface] = [c for c in self.children if isinstance(c, OwnerInterface)]
        for c in containers:
            # A container can not contain itself
            if c == widget:
                continue
            if pos.x < c.x or pos.x > c.x+c.width or pos.y < c.y or pos.y > c.y+c.height:
                continue
            # The release point is inside this container. Make it the owner.
            return c.evaluateOwnership(widget, pos, self)

        # We are to take ownership of this shape.
        if owner := widget.owner():
            # If we already were the owner, do nothing.
            if owner == self:
                return
            owner.children.remove(widget)
            widget.delete()
        self.children.append(widget)
        widget.create(self)


class Stylable:
    """ Implement the styling interface.
        The class that inherits these functions must have an attribute `styling`.
        The class method `getDefaultStyle` must be implemented by the inheritor.
        This would return the combination of the styles for each part of the shape.
    """
    def getStyle(self, key, default=None):
        if key in self.styling:
            return self.styling[key]
        defaults = self.getDefaultStyle()
        if key in defaults:
            return defaults[key]
        if default is not None:
            return default
        raise RuntimeError(f"Trying to retrieve unknown styling element {key}")

    @classmethod
    def getDefaultStyle(cls):
        raise NotImplementedError()

    def getAllStyle(self):
        style = self.getDefaultStyle()
        style.update(self.styling)
        return style

    def dumpStyle(self) -> str:
        """ Return a json-encoded string with those style bits that differ from the default """
        default_style = self.getDefaultStyle()
        styling_update = {k: v for k, v in self.getAllStyle().items() if default_style[k] != v}
        return json.dumps(styling_update)

    def loadStyle(self, s):
        """ Load a styling dictionary from a JSON-encoded string. """
        details = json.loads(s)
        self.styling = details

    def getStyleKeys(self):
        keys = list(self.getDefaultStyle())
        keys.sort()
        return keys

    def updateShape(self):
        raise NotImplementedError()

    def updateStyle(self, **updates) -> bool:
        """ Returns True if the style was actually changed. """
        current_style = self.getDefaultStyle()
        current_style.update(self.styling)
        update = {k:v for k, v in updates.items() if current_style.get(k, None) != v}
        if update:
            self.styling.update(update)
            self.updateShape()

@dataclass
class Shape(Stylable, StorableElement):
    x: float = 0.0
    y: float = 0.0
    height: float = 0.0
    width: float = 0.0
    z: float = 0.0
    order: int = 0
    styling: Dict[str, str] = field(default_factory=dict)
    parent: Optional[Self] = None
    Id: int = 0

    default_style = dict()
    owner = None

    def __post_init__(self):
        if not isinstance(self.styling, dict):
            if not self.styling:
                self.styling = {}
            else:
                self.styling = json.loads(self.styling)

    def isResizable(self) -> bool:
        return True

    def getPos(self) -> Point:
        return Point(x=self.x, y=self.y)
    def setPos(self, new: Point):
        self.x, self.y = new.astuple()
        self.updateShape(self.shape)
        for s in self.subscribers.values():
            s(self)
    def getSize(self) -> Point:
        return Point(x=self.width, y=self.height)
    def setSize(self, new: Point):
        self.width, self.height = new.astuple()
        self.updateShape(self.shape)

    def getShape(self):
        shape_type = self.getShapeDescriptor()
        return shape_type.getShape(self)

    def updateShape(self, shape=None):
        shape = shape or self.shape
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(shape, self)

    def delete(self):
        self.shape.remove()

    def subscribe(self, role, f):
        self.subscribers[role] = f

    def unsubscribe(self, role):
        if role in self.subscribers:
            del self.subscribers[role]

    def onHover(self, ev):
        pass

    def onClick(self, ev):
        if owner := self.owner():
            owner.clickChild(self, ev)

    def onDblClick(self, ev):
        if owner := self.owner():
            owner.dblclickChild(self, ev)

    def onMouseDown(self, ev):
        match ev.button:
            case 0:
                if owner := self.owner():
                    owner.mouseDownChild(self, ev)
            case 2:
                self.onContextMenu(ev)

    def onContextMenu(self, ev):
        pass

    #################################
    ## Low level handlers
    ## These handlers are used to determine high-level events.
    def onMouseEnter(self, ev):
        # This becomes a "hover" event when no mouse button is clicked.
        if ev.buttons == 0:
            self.onHover(ev)

    def create(self, owner):
        self.owner = ref(owner)

        canvas = owner.getCanvas()
        self.subscribers = {}

        self.shape = self.getShape()
        self.shape.attrs['data-class'] = type(self).__name__
        canvas <=  self.shape

        self.shape.bind('click', self.onClick)
        self.shape.bind('mousedown', self.onMouseDown)
        self.shape.bind('dblclick', self.onDblClick)

    def destroy(self):
        pass

    def getCenter(self):
        return self.getPos() + self.getSize()/2

    def getIntersection(self, b):
        halfsize = self.getSize()/2
        a = self.getCenter()
        delta = b - a
        if abs(delta.x) > 1:
            rc = delta.y / delta.x
            i_left = Point(math.copysign(halfsize.x, delta.x), math.copysign(rc*halfsize.x, delta.y))
            if abs(i_left.y) < halfsize.y:
                return i_left + a
        rc = delta.x / delta.y
        i_top = Point(math.copysign(rc*halfsize.y, delta.x), math.copysign(halfsize.y, delta.y))
        return i_top + a

    def getConnectionTarget(self, ev):
        """ Determine if the user clicked on a child like a port """
        # A basic shape has only one connection
        return self

    def isConnected(self, target):
        return target == self

    def update(self, values_json):
        values = json.loads(values_json)
        for key, value in values.items():
            setattr(self, key, value)
        self.updateShape(self.shape)

    def load(self, diagram):
        diagram.addBlock(self)

    @classmethod
    def getDefaultStyle(cls):
        # Don't return the original, to prevent unwanted changes that affect all instances.
        return dict(cls.default_style)

    @classmethod
    def getShapeDescriptor(cls):
        return BasicShape.getDescriptor("rect")

    def getEntityForConnection(self):
        """ Called to determine """
        return getattr(self, 'logical_class', None)
    def getLogicalClass(self):
        """ Called to determine what class stores the logical details of this element.
            In most cases, this is set by the object representing the entity. In some cases,
            like the PortLabel, this must be determined runtime.
        """
        return getattr(self, 'logical_class', None)

@dataclass
class CP:
    orientation: BlockOrientations = BlockOrientations.RIGHT
    order: int = 0
    styling: Dict[str, str] = field(default_factory=dict)

    def onHover(self):
        pass

    def onConnect(self):
        pass

    def onDrag(self):
        pass

class RoutingStrategy:
    def decorate(self, connection, canvas):
        raise NotImplementedError
    def route(self, shape, all_blocks):
        raise NotImplementedError
    def dragEnd(self, canvas):
        pass

class RouteCenterToCenter(RoutingStrategy):
    def __init__(self):
        self.decorators = []
        self.widget = None
        self.drag_start = None

    def createWaypointByDrag(self, pos, connection, canvas):
        self.dragged_index = self.widget.insertWaypoint(pos)
        self.initial_pos = self.drag_start = self.widget.waypoints[self.dragged_index]
        self.clear_decorations()
        self.decorate(connection, canvas)

    def dragHandle(self, pos):
        delta = pos - self.drag_start
        new_pos = self.initial_pos + delta
        handle = self.decorators[self.dragged_index]
        handle['cx'], handle['cy'] = new_pos.x, new_pos.y
        self.widget.waypoints[self.dragged_index] = new_pos

    def mouseDownHandle(self, decorator_id, ev):
        self.dragged_index = decorator_id
        self.drag_start = getMousePos(ev)
        self.initial_pos = self.widget.waypoints[decorator_id]
        current = ev.target
        current.dispatchEvent(window.CustomEvent.new("handle_drag_start", {"bubbles":True, "detail": {'router': self}}))
        ev.stopPropagation()
        ev.preventDefault()

    def deleteWaypoint(self):
        if self.dragged_index is not None and self.dragged_index < len(self.widget.waypoints):
            self.widget.waypoints.pop(self.dragged_index)
            self.clear_decorations()
            self.decorate(self.widget, self.widget.canvas)

    def decorate(self, connection, canvas):
        self.widget = connection
        self.decorators = [svg.circle(cx=p.x, cy=p.y, r=5, stroke_width=0, fill="#29B6F2", Class=handle_class,
                                      data_index=i)
                           for i, p in enumerate(self.widget.waypoints)]
        def bind(i, d):
            d.bind('mousedown', lambda ev: self.mouseDownHandle(i, ev))
        for i, d in enumerate(self.decorators):
            canvas <= d
            # Python shares variables inside a for loop by reference
            # So to avoid binding to the same handle x times, we need to call a function to make permanent copies.
            bind(i, d)

    def clear_decorations(self):
        for d in self.decorators:
            d.remove()
        self.decorators = []

    def route(self, shape, all_blocks):
        # Determine the centers of both blocks
        c_a = shape.start.getCenter()
        c_b = shape.finish.getCenter()

        # Get the points where the line intersects both blocks
        i_a = shape.start.getIntersection(c_b if not shape.waypoints else shape.waypoints[0])
        i_b = shape.finish.getIntersection(c_a if not shape.waypoints else shape.waypoints[-1])

        # Move the line
        waypoints = ''.join(f'L {p.x} {p.y} ' for p in shape.waypoints)
        shape.path['d'] = f"M {i_a.x} {i_a.y} {waypoints}L {i_b.x} {i_b.y}"
        shape.selector['d'] = f"M {i_a.x} {i_a.y} {waypoints}L {i_b.x} {i_b.y}"

        # Store the actual intersection points
        shape.terminations = (i_a, i_b)


class RouteSquare(RoutingStrategy):
    def __init__(self):
        self.decorators = []
        self.dragged_index = None
    def mouseDownHandle(self, decorator_id, ev):
        self.dragged_index = decorator_id
        self.drag_start = getMousePos(ev)
        current = ev.target
        current.dispatchEvent(window.CustomEvent.new("handle_drag_start", {"bubbles":True, "detail": {'router': self}}))
        ev.stopPropagation()
        ev.preventDefault()
    def createWaypointByDrag(self, ev, connection, canvas):
        # WIth this router, new line segments are created differenly.
        pass
    def dragHandle(self, pos):
        wp_index = self.handle_wp_index[self.dragged_index]
        # Create a new waypoint if necessary
        if (new := math.ceil(wp_index)) != wp_index:
            # We need to create a new waypoint
            if self.handle_orientation[self.dragged_index] == 'X':
                waypoint = Point(x=self.widget.points[self.dragged_index].x, y=inf)
            else:
                waypoint = Point(x=inf, y=self.widget.points[self.dragged_index].y)
            self.widget.waypoints.insert(new, waypoint)
            self.handle_wp_index = self.getHandleWpIndices(self.widget.waypoints, self.widget.points)
            wp_index = new
        # Now we can start moving the waypoint.
        delta = pos - self.drag_start
        new_pos = self.initial_pos[self.dragged_index] + delta
        h = self.decorators[self.dragged_index]
        if self.widget.waypoints[wp_index].x == inf:
            self.widget.waypoints[wp_index].y = new_pos.y
            h['y1'] = int(self.original_handle_pos[self.dragged_index][0].y + delta.y)
            h['y2'] = int(self.original_handle_pos[self.dragged_index][0].y + delta.y)
        else:
            self.widget.waypoints[wp_index].x = new_pos.x
            h['x1'] = int(self.original_handle_pos[self.dragged_index][0].x + delta.x)
            h['x2'] = int(self.original_handle_pos[self.dragged_index][0].x + delta.x)

    def dragEnd(self, canvas):
        self.clear_decorations()
        self.decorate(self.widget, canvas)

    def deleteWaypoint(self):
        wp_index = self.handle_wp_index[self.dragged_index]
        if (new := math.ceil(wp_index)) != wp_index:
            # There is no waypoint associated with this handle
            return
        self.widget.waypoints.pop(wp_index)
        self.clear_decorations()

    @staticmethod
    def getHandleWpIndices(waypoints, points):
        if not waypoints:
            return [-0.5 for _ in points[:-1]]

        current_wp_index = 0
        indices = []
        for p in points[:-1]:
            if current_wp_index >= len(waypoints):
                indices.append(len(waypoints)-0.5)
                continue
            wp = waypoints[current_wp_index]
            if wp.x == inf:
                if wp.y == p.y:
                    indices.append(current_wp_index)
                    current_wp_index += 1
                else:
                    indices.append(current_wp_index-0.5)
            else:
                if wp.x == p.x:
                    indices.append(current_wp_index)
                    current_wp_index += 1
                else:
                    indices.append(current_wp_index-0.5)
        return indices

    def decorate(self, connection, canvas):
        def bind(i, d):
            d.bind('mousedown', lambda ev: self.mouseDownHandle(i, ev))
        # Show a little stripe next to each line-piece
        self.decorators = []
        self.initial_pos = {}
        self.widget = connection
        self.handle_orientation = []
        self.handle_wp_index = self.getHandleWpIndices(self.widget.waypoints, self.widget.points)
        self.original_handle_pos = []
        for i, (p1, p2) in enumerate(zip(self.widget.points[:-1], self.widget.points[1:])):
            v = (p2 - p1)
            vn = v / v.norm()
            c = (p1 + p2) / 2
            n = vn.transpose()
            orientation = 'X' if abs(n.x) > abs(n.y) else 'Y'
            self.handle_orientation.append(orientation)
            p1 = c + 10 * n - 20 * vn
            p2 = c + 10 * n + 20 * vn
            self.original_handle_pos.append((p1, p2))
            decorator = svg.line(x1=p1.x, y1=p1.y, x2=p2.x, y2=p2.y, stroke_width=6, stroke="#29B6F2",
                                 data_orientation=orientation, data_index=i, Class=handle_class)
            bind(len(self.decorators), decorator)
            self.initial_pos[len(self.decorators)] = c
            canvas <= decorator
            self.decorators.append(decorator)

    def clear_decorations(self):
        for d in self.decorators:
            d.remove()
        self.decorators = []

    def route(self, shape, all_blocks):
        # The actual algorithm for routing squared paths is quite complicated.
        # Therefor it is delegated to a separate function.
        shape.points = routeSquare((shape.start.getPos(), shape.start.getSize()),
                                   (shape.finish.getPos(), shape.finish.getSize()),
                                   shape.waypoints)

        waypoints = ''.join(f'L {p.x} {p.y} ' for p in shape.points[1:])
        start, end = shape.points[0], shape.points[-1]
        shape.path['d'] = f"M {start.x} {start.y} {waypoints}"
        shape.selector['d'] = f"M {start.x} {start.y} {waypoints}"
        shape.terminations = (start, end)

RoutingMethod = ['square', 'center2center']
router_classes = {'center2center': RouteCenterToCenter, 'square': RouteSquare}

@dataclass
class Relationship(Stylable):
    start: Shape = None
    finish: Shape = None
    waypoints: List[Point] = field(default_factory=list)
    id: HIDDEN(int) = field(default_factory=getId)
    z: float = 0.0
    styling: dict = field(default_factory=dict)
    default_style = dict(linecolor='#000000', linewidth='2', endmarker='arrow', startmarker='', routing_method='square')

    def __hash__(self):
        return id(self)

    def __post_init__(self):
        # Also set the routing_method strategy object and message container.
        self.routing_method = router_classes.get(self.getStyle('routing_method', 'square'), RouteSquare)
        self.messages = []
        self.points = None
        self.owner = None

    @property
    def canvas(self):
        return self.owner.canvas

    def onHover(self):
        pass

    def onDrag(self):
        pass

    def onMouseDown(self, ev):
        if ev.button == 0:
            self.owner.mouseDownConnection(self, ev)

    def onContextMenu(self, ev):
        pass

    def insertWaypoint(self, pos):
        # Find the spot to insert the waypoint.
        # We insert it where the distance to the line between the two adjacent points is smallest
        allpoints = [self.terminations[0]] + self.waypoints + [self.terminations[1]]
        adjacents = zip(allpoints[:-1], allpoints[1:])
        distances = []
        for a, b in adjacents:
            v = b - a
            vmin = a - b
            n = Point(x=v.y, y=-v.x)
            d1 = pos - a
            d2 = pos - b
            # Check if the point is "behind" the segment
            # These we give infinite distance
            if v.dot(d1) < 0 or vmin.dot(d2) < 0:
                distances.append(math.inf)
            else:
                distances.append(abs(n.dot(d1)))
        # Find the smallest distance
        minimum = min(distances)
        index = distances.index(minimum)
        self.waypoints.insert(index, pos)
        return index

    def create(self, owner, all_blocks):
        self.owner = owner
        self.route(all_blocks)
        # Also render the messages
        for m in self.messages:
            m.create(owner)

        self.reroute(all_blocks)

    def reroute(self, all_blocks):
        if self.points:
            first_point = copy(self.points[0])
            last_point = copy(self.points[-1])
        else:
            first_point = None
            last_point = None

        router = getattr(self, 'router', None) or router_classes.get(self.getStyle('routing_method', 'square'), RouteSquare)()
        router.route(self, all_blocks)
        self.router = router
        if first_point is not None:
            first_delta = self.points[0] - first_point
            last_delta = self.points[-1] - last_point
        else:
            first_delta = Point(0,0)
            last_delta = Point(0,0)
        for m in self.messages:
            # Move the shape with the point it is linked to
            if m.direction == MsgDirection.source_2_target:
                # Linked to the first point
                m.setPos(m.getPos() + first_delta)
            else:
                # Linked to the last point
                m.setPos(m.getPos() + last_delta)
            m.updateShape()

    def route(self, all_blocks):
        """ The default routing is center-to-center. """
        # Create the line
        details = dict(d="", stroke=self.getStyle('linecolor'), stroke_width=self.getStyle('linewidth'),
                             marker_end=f"url('#{self.getStyle('endmarker')}')",
                             marker_start=f"url('#{self.getStyle('startmarker')}')", fill="none")
        pattern = line_patterns[self.getStyle('pattern', 'solid')]
        if pattern:
            details['stroke_dasharray'] = pattern
        self.path = svg.path(**details)
        self.path.attrs['data-class'] = type(self).__name__
        # Above the visible path, there is an invisible one used to give a wider selection region.
        self.selector = svg.path(d="", stroke="gray", stroke_width="10", fill="none", opacity="0.0")
        self.path.bind('mousedown', self.onMouseDown)
        self.path.bind('contextmenu', self.onContextMenu)
        self.selector.bind('mousedown', self.onMouseDown)
        self.selector.bind('contextmenu', self.onContextMenu)
        self.owner.canvas <= self.selector
        self.owner.canvas <= self.path

    def delete(self):
        self.selector.remove()
        self.path.remove()

    @classmethod
    def getDefaultStyle(cls):
        # Don't return the original, to prevent unwanted changes that affect all instances.
        return dict(cls.default_style)

    def load(self, diagram):
        diagram.addConnection(self)

    def updateShape(self):
        items = {
            'stroke': self.getStyle('linecolor'),
            'stroke-width': self.getStyle('linewidth'),
            'marker-end': f"url('#{self.getStyle('endmarker')}')",
            'marker-start': f"url('#{self.getStyle('startmarker')}')"
        }
        for k, v in items.items():
            self.path.attrs[k] = v

    def update(self, values_json):
        values = json.loads(values_json)
        for key, value in values.items():
            setattr(self, key, value)
        self.updateShape()

    def getLogicalClass(self):
        return getattr(self, 'logical_class', None)

    def add_message(self, msg):
        # Calculate initial orientation and orientation.
        if msg.direction == MsgDirection.source_2_target:
            # Use the first point of the path as reference
            origin, orientation = path_origin(self.path.attrs['d'])
        else:
            origin, orientation = path_ending(self.path.attrs['d'])
        # Place the message and render it.
        offset = Point(5, -15).rot(orientation)
        msg.x = origin.x + offset.x
        msg.y = origin.y + offset.y
        msg.orientation = orientation
        self.messages.append(msg)

class MsgDirection(enum.IntEnum):
    source_2_target = enum.auto()
    target_2_source = enum.auto()

@dataclass
class Container(Shape, OwnerInterface):
    """
    A container is very similar to a regular shape, with a few exceptions.
    The biggest is that when a container is moved, its children move as well.
    A second one is that waypoints for internal connections are constrained to the container.
    """
    children: Shape = field(default_factory=list)

    def clickChild(self, widget, ev):
        if owner := self.owner():
            owner.clickChild(widget, ev)
    def mouseDownChild(self, widget, ev):
        if owner := self.owner():
            owner.mouseDownChild(widget, ev)

    def mouseDownConnection(self, connection, ev):
        if owner := self.owner():
            owner.mouseDownConnection(connection, ev)

    def getCanvas(self):
        if owner := self.owner():
            return owner.getCanvas()

    def __le__(self, svg_widget):
        if owner := self.owner():
            return owner <= svg_widget

    # Function to manipulate the schematic
    def setPos(self, new):
        # Determine the delta
        delta = Point(new.x - self.x, new.y - self.y)

        # Also update the positions for all the children
        for child in self.children:
            child.setPos(child.getPos() + delta)

        # Find all connections affected by this move.
        connections = set(c for s in self.children for c in self.getConnectionsToShape(s))
        connections = list(connections)
        internal_connections = [c for c in connections if c.start in self.children and c.finish in self.children]

        # Move any waypoints inside this container with the container
        for c in connections:
            if c in internal_connections:
                wp = c.waypoints
            else:
                wp = [p for p in c.waypoints
                      if self.x <= p.x <= self.x + self.width and self.y <= p.y <= self.y + self.height]
            for p in wp:
                p.x += delta.x
                p.y += delta.y

        # Re-route any relationships to the children
        for c in connections:
            # For now, routing does not automatically avoid blocks.
            c.reroute([])

        # Set the new position of this shape
        super().setPos(new)

    def setSize(self, new):
        # Keep the rect large enough to fit all children.
        if self.children:
            min_width = max([c.x+c.width-self.x for c in self.children]) + 5
            min_height = max([c.y+c.height-self.y for c in self.children]) + 5
            if new.x < min_width:
                new.x = min_width
            if new.y < min_height:
                new.y = min_height
        super().setSize(new)

    def getConnectionsToShape(self, widget):
        # For now, all connections are stored at the diagram level.
        if owner := self.owner():
            return owner.getConnectionsToShape(widget)
        return []
