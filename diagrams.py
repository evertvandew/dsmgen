import json

try:
    from browser import document, alert, svg, console, window
except:
    document = {}
    alert = None
    class svg:
        pass
    svg_elements = ['line', 'circle', 'path', 'rect']
    functions = {k: (lambda self, **kargs: kwargs) for k in svg_elements}
    svg.__dict__.update(functions)



from typing import Union, Any, List, Self
from dataclasses import dataclass, field, asdict
from weakref import ref
import enum
import math
from math import inf
from square_routing import routeSquare
from point import Point
from fontsizes import font_sizes

###############################################################################
## Primitive shapes

resize_role = 'resize_decorator'

class Orientations(enum.IntEnum):
    TL = 1
    TOP = 2
    TR = 3
    RIGHT = 4
    BR = 5
    BOTTOM = 6
    BL = 7
    LEFT = 8


@dataclass
class Shape:
    x: float
    y: float
    height: float
    width: float
    name: str

    def isResizable(self):
        return True

    def getPos(self):
        return Point(x=self.x, y=self.y)
    def setPos(self, new):
        self.x, self.y = new.astuple()
        self.updateShape(self.shape)
        for s in self.subscribers.values():
            s(self)
    def getSize(self):
        return Point(x=self.width, y=self.height)
    def setSize(self, new):
        self.width, self.height = new.astuple()
        self.updateShape(self.shape)
    def updateShape(self, shape):
        shape['width'], shape['height'] = self.width, self.height
        shape['x'], shape['y'] = self.x, self.y
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
        if diagram := self.diagram():
            diagram.clickChild(self, ev)

    def onMouseDown(self, ev):
        if diagram := self.diagram():
            diagram.mouseDownChild(self, ev)

    #################################
    ## Low level handlers
    ## These handlers are used to determine high-level events.
    def onMouseEnter(self, ev):
        # This becomes a "hover" event when no mouse button is clicked.
        if ev.buttons == 0:
            self.onHover(ev)

    def getShape(self):
        return svg.rect(x=self.x,y=self.y, width=self.width, height=self.height, stroke_width="2",stroke="black",fill="white")
    def create(self, diagram):
        self.diagram = ref(diagram)

        canvas = diagram.canvas
        self.subscribers = {}
        self.shape = self.getShape()
        canvas <=  self.shape

        self.shape.bind('click', self.onClick)
        self.shape.bind('mousedown', self.onMouseDown)

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

@dataclass
class CP:
    orientation: Orientations
    order: int

    def onHover(self):
        pass

    def onConnect(self):
        pass

    def onDrag(self):
        pass

class RoutingMethod(enum.IntEnum):
    CenterTCenter = 1
    Squared = 2

class RoutingStragegy:
    def decorate(self, connection, canvas):
        raise NotImplementedError
    def route(self, shape, all_blocks):
        raise NotImplementedError
    def dragEnd(self, canvas):
        pass

class RouteCenterToCenter(RoutingStragegy):
    def __init__(self):
        self.decorators = []
        self.widget = None
        self.drag_start = None

    def createWaypointByDrag(self, ev, connection, canvas):
        pos = getMousePos(ev)
        self.dragged_index = self.widget.insertWaypoint(pos)
        self.initial_pos = self.drag_start = self.widget.waypoints[self.dragged_index]
        self.clear_decorations()
        self.decorate(connection, canvas)

    def dragHandle(self, ev):
        console.log(f"Dragging handle: {self.dragged_index}")
        delta = getMousePos(ev) - self.drag_start
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
        self.decorators = [svg.circle(cx=p.x, cy=p.y, r=5, stroke_width=0, fill="#29B6F2") for p in self.widget.waypoints]
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


class RouteSquare(RoutingStragegy):
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
    def dragHandle(self, ev):
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
        delta = getMousePos(ev) - self.drag_start
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
        for p1, p2 in zip(self.widget.points[:-1], self.widget.points[1:]):
            v = (p2 - p1)
            vn = v / len(v)
            c = (p1 + p2) / 2
            n = vn.transpose()
            self.handle_orientation.append('X' if abs(n.x) > abs(n.y) else 'Y')
            p1 = c + 10 * n - 20 * vn
            p2 = c + 10 * n + 20 * vn
            self.original_handle_pos.append((p1, p2))
            decorator = svg.line(x1=p1.x, y1=p1.y, x2=p2.x, y2=p2.y, stroke_width=6, stroke="#29B6F2")
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
        # Therefore it is delegated to a separate function.
        shape.points = routeSquare((shape.start.getPos(), shape.start.getSize()),
                                   (shape.finish.getPos(), shape.finish.getSize()),
                                   shape.waypoints)

        waypoints = ''.join(f'L {p.x} {p.y} ' for p in shape.points[1:])
        start, end = shape.points[0], shape.points[-1]
        shape.path['d'] = f"M {start.x} {start.y} {waypoints}"
        shape.selector['d'] = f"M {start.x} {start.y} {waypoints}"
        shape.terminations = (start, end)


router_classes = {RoutingMethod.CenterTCenter: RouteCenterToCenter, RoutingMethod.Squared: RouteSquare}

@dataclass
class Relationship:
    start: Point
    finish: Point
    waypoints: List[Point]
    routing_method: RoutingMethod

    @property
    def canvas(self):
        return self.diagram.canvas

    def onHover(self):
        pass

    def onDrag(self):
        pass

    def getMenu(self):
        pass

    def onMouseDown(self, ev):
        self.diagram.mouseDownConnection(self, ev)

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

    def reroute(self, all_blocks):
        router = getattr(self, 'router', None) or router_classes[self.routing_method]()
        router.route(self, all_blocks)
        self.router = router

    def route(self, diagram, all_blocks):
        """ The default routing is center-to-center. """
        self.diagram = diagram
        # Create the line
        self.path = svg.path(d="", stroke="black", stroke_width="2", marker_end="url(#endarrow)",
                             marker_start="url(#startarrow)", fill="none")
        # Above the visible path, there is an invisible one used to give a wider selection region.
        self.selector = svg.path(d="", stroke="gray", stroke_width="10", fill="none", opacity="0.0")
        self.reroute(all_blocks)
        self.path.bind('mousedown', self.onMouseDown)
        self.selector.bind('mousedown', self.onMouseDown)
        self.diagram.canvas <= self.selector
        self.diagram.canvas <= self.path

    def delete(self):
        self.selector.remove()
        self.path.remove()


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

def getMousePos(ev):
    CTM = ev.target.getScreenCTM()
    return Point(x=int((ev.clientX - CTM.e)/CTM.a), y=int((ev.clientY-CTM.f)/CTM.d))

def moveSingleHandle(decorators, widget, orientation):
    d = decorators[orientation]
    x, y, width, height = [getattr(widget, k) for k in ['x', 'y', 'width', 'height']]
    d['cx'], d['cy'] = locations[orientation](x, y, width, height)

def moveHandles(decorators, widget, orientation):
    # Determine which markers to move
    for o in to_update[orientation]:
        moveSingleHandle(decorators, widget, o)

def moveAll(widget, decorators):
    for o in Orientations:
        moveSingleHandle(decorators, widget, o)


class VAlign(enum.IntEnum):
    TOP = 1
    CENTER = 2
    BOTTOM = 3

class HAlign(enum.IntEnum):
    LEFT = 10
    CENTER = 11
    RIGHT = 12
    JUSTIFIED = 13

POINT_TO_PIXEL = 1.3333

def wrapText(text, width, font='Arial.ttf', fontsize=10):
    # Separate into words and determine the size of each part
    font = font_sizes['Arial.ttf']['sizes']
    parts = text.split()
    normalized_width = width / POINT_TO_PIXEL / fontsize
    sizes = [sum(font[ord(ch)] for ch in part) for part in parts]

    # Now fill the lines
    line_length = 0
    lines = []
    current_line = []
    for size, part in zip(sizes, parts):
        if line_length + size + font[32]*(len(current_line)-1) > normalized_width:
            lines.append(' '.join(current_line))
            current_line = []
            line_length = 0
        current_line.append(part)
        line_length += size
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def renderText(text, x, y, width, height, xmargin=2, ymargin=2, halign=HAlign.CENTER, valign=VAlign.CENTER, font='Arial', fontsize=16):
    font_file = font+'.ttf'
    lines = wrapText(text, width, font_file, fontsize)
    # Now render these lines
    anchor = {HAlign.LEFT: 'start', HAlign.CENTER: 'middle', HAlign.RIGHT: 'end'}[halign]
    lineheight = font_sizes[font_file]['lineheight'] * fontsize
    # Calculate where the text must be placed.
    xpos = int({HAlign.LEFT: x+xmargin, HAlign.CENTER: x+width/2, HAlign.RIGHT: x+width-xmargin}[halign])
    ypos = {#VAlign.TOP: y+ymargin,
            VAlign.CENTER: y+(height-len(lines)*lineheight)/2
            #VAlign.BOTTOM: y+height-len(lines)*lineheight*fontsize - ymargin
           }[valign]

    rendered = [svg.text(line, x=xpos, y=int(ypos+lineheight*(i+1)), text_anchor=anchor, font_size=fontsize, font_family='Arial')
                for i, line in enumerate(lines)]
    return rendered

class BehaviourFSM:
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


class ResizeStates(BehaviourFSM):
    States = enum.IntEnum("States", "NONE DECORATED MOVING RESIZING")

    def __init__(self, diagram):
        super(self).__init__(self)
        self.state = self.States.NONE
        self.diagram = diagram
        self.widget = None
        self.decorators = []

    def mouseDownShape(self, diagram, widget, ev):
        if self.state != self.States.NONE and self.widget != widget:
            self.unselect()
        if self.state == self.States.NONE:
            self.select(widget)
        self.state = self.States.MOVING
        self.dragstart = getMousePos(ev)
        self.initial_pos = widget.getPos()
        ev.stopPropagation()
        ev.preventDefault()

    def mouseDownConnection(self, diagram, widget, ev):
        # We need to change the state machine
        if self.state != self.States.NONE:
            self.unselect()
        fsm = RerouteStates(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownConnection(diagram, widget, ev)

    def mouseDownBackground(self, diagram, ev):
        if self.widget and ev.target == self.widget.shape:
            self.state = self.States.MOVING
            return
        if ev.target == diagram.canvas:
            if self.state == self.States.DECORATED:
                self.unselect()
        self.state = self.States.NONE
        return
        self.dragstart = getMousePos(ev)
        if self.widget:
            self.initial_pos = diagram.selection.getPos()
            self.initial_size = diagram.selection.getSize()


    def onMouseUp(self, diagram, ev):
        if self.state in [self.States.MOVING, self.States.RESIZING]:
            self.state = self.States.DECORATED

    def onMouseMove(self, diagram, ev):
        if self.state in [self.States.NONE, self.States.DECORATED]:
            return
        delta = getMousePos(ev) - self.dragstart
        if self.state == self.States.RESIZING:
            self.onDrag(self.initial_pos, self.initial_size, delta)
        if self.state == self.States.MOVING:
            self.widget.setPos(self.initial_pos + delta)
            diagram.rerouteConnections(self.widget)

    def delete(self, diagram):
        """ Called when the FSM is about to be deleted"""
        if self.state != self.States.NONE:
            self.unselect()

    def startResize(self, widget, orientation, ev):
        self.dragstart = getMousePos(ev)
        self.state = self.States.RESIZING
        self.initial_pos = widget.getPos()
        self.initial_size = widget.getSize()

    def unselect(self):
        for dec in self.decorators.values():
            dec.remove()
        self.decorators = {}
        if self.widget:
            self.widget.unsubscribe(resize_role)
        self.widget = None
        self.state = self.States.NONE

    def select(self, widget):
        self.widget = widget

        self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2") for k in Orientations}
        x, y, width, height = [getattr(widget, k) for k in ['x', 'y', 'width', 'height']]

        for k, d in self.decorators.items():
            d['cx'], d['cy'] = locations[k](x, y, width, height)

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
            if self.state != self.States.NONE:
                widget = self.widget
                self.unselect()
                widget.delete()
                diagram.deleteBlock(widget)


class RerouteStates(BehaviourFSM):
    States = enum.IntEnum('States', 'NONE DECORATED HANDLE_SELECTED POTENTIAL_DRAG DRAGGING')
    def __init__(self, diagram):
        super(self).__init__(self)
        self.state = self.States.NONE
        self.diagram = diagram
        self.decorators = []
        self.dragged_index = None

    def mouseDownShape(self, diagram, widget, ev):
        # We need to change the state machine
        if self.state != self.States.NONE:
            self.clear_decorations()
        fsm = ResizeStates(self.diagram)
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
        console.log("Handle Drag Start")
        self.state = self.States.DRAGGING
        ev.stopPropagation()
        ev.preventDefault()

    def dragHandle(self, ev):
        console.log(f"Dragging handle: {self.dragged_index}")
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

    def onMouseMove(self, diagram, ev):
        if self.state in [self.States.NONE, self.States.DECORATED, self.States.HANDLE_SELECTED]:
            return
        if self.state == self.States.POTENTIAL_DRAG:
            delta = getMousePos(ev) - self.dragstart
            if len(delta) > 10:
                self.widget.router.createWaypointByDrag(ev, self.widget, self.diagram.canvas)
                self.state = self.States.DRAGGING
        if self.state == self.States.DRAGGING:
            self.widget.router.dragHandle(ev)
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
    def __init__(self, connectionFactory):
        self.connectionFactory = connectionFactory
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
                    diagram.connect(self.a_party, party, self.connectionFactory)
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
            x, y = (self.a_party.getPos() + self.a_party.getSize()/2).astuple()
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
        self.path['x2'], self.path['y2'] = (pos - delta).astuple()
    def delete(self, diagram):
        if self.state != self.States.NONE:
            self.path.remove()
    def onKeyDown(self, diagram, ev):
        if ev.key == 'Escape':
            if self.state == self.States.A_SELECTED:
                # Delete the connection
                self.path.remove()
                self.state = self.States.NONE


class Diagram:
    def __init__(self, widgets):
        self.selection = None
        self.mouse_events_fsm = None
        self.children = []
        self.connections = []
        self.widgets = widgets

    def drop(self, block):
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)
        block.create(self)
        self.children.append(block)

    def deleteConnection(self, connection):
        if connection in self.connections:
            connection.delete()
            self.connections.remove(connection)

    def deleteBlock(self, block):
        if block in self.children:
            block.delete()
            self.children.remove(block)

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

    def connect(self, a, b, cls):
        connection = cls(start=a, finish=b, waypoints=[], routing_method=RoutingMethod.Squared)
        #connection = cls(start=a, finish=b, waypoints=[], routing_method=RoutingMethod.CenterTCenter)
        self.connections.append(connection)
        connection.route(self, self.children)

    def changeFSM(self, fsm):
        if self.mouse_events_fsm is not None:
            self.mouse_events_fsm.delete(self)
        self.mouse_events_fsm = fsm

    def rerouteConnections(self, widget):
        if isinstance(widget, Relationship):
            widget.reroute(self.children)
        else:
            for c in self.connections:
                if widget.isConnected(c.start) or widget.isConnected(c.finish):
                    c.reroute(self.children)

    def bind(self, canvas):
        self.canvas = canvas
        canvas.bind('click', self.onClick)
        canvas.bind('mouseup', self.onMouseUp)
        canvas.bind('mousemove', self.onMouseMove)
        canvas.bind('mousedown', self.onMouseDown)
        canvas.bind('handle_drag_start', self.handleDragStart)
        document.bind('keydown', self.onKeyDown)
        for widget in self.widgets:
            widget(self)

    def clickChild(self, widget, ev):
        pass

    def mouseDownChild(self, widget, ev):
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = ResizeStates(self)
        self.mouse_events_fsm.mouseDownShape(self, widget, ev)


        # Also notify any listeners that an object was selected
        details = json.dumps(asdict(widget))
        self.canvas.dispatchEvent(window.CustomEvent.new("shape_selected", {
            "bubbles":True,
            "detail": {
                "values": details,
                "update": widget.update,
                "object": widget
            }
        }))


    def mouseDownConnection(self, connection, ev):
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = RerouteStates(self)
        self.mouse_events_fsm.mouseDownConnection(self, connection, ev)

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
        console.log(f"Handle Drag Start {list(ev.__dict__.keys())}")
        self.mouse_events_fsm and self.mouse_events_fsm.handleDragStart(self, ev)

    def onHover(self):
        pass

    def getMenu(self):
        pass

    def onDrop(self):
        pass

    def serialize(self):
        # Output the model in JSON format
        details = {'blocks': [asdict(b) for b in self.children],
                   'connections': [asdict(c) for c in self.connections]}
        return json.dumps(details)



###############################################################################
## Diagrams and shapes
@dataclass
class Note(Shape):
    description: str = ''
    fold_size = 10
    def getPoints(self):
        x, y, w, h = self.x, self.y, self.width, self.height
        f = self.fold_size
        return ' '.join(f'{x+a},{y+b}' for a, b in [(0,0), (w-f,0), (w,f), (w-f,f), (w-f,0), (w,f), (w,h), (0,h)])
    def getShape(self):
        g = svg.g()
        outline = svg.polygon(points=self.getPoints(), fill="#FFFBD6", stroke="black")
        g <= outline
        for line in renderText(self.description, self.x, self.y, self.width, self.height, 2, 2,
                                HAlign.CENTER, VAlign.CENTER):
            g <= line
        return g

    def updateShape(self, shape):
        rect = shape.children[0]
        rect['points'] = self.getPoints()
        xpos = self.x + self.width / 2
        lineheight = font_sizes['Arial.ttf']['lineheight']
        for i, line in enumerate(shape.children[1:]):
            # Remove the text elements
            shape.removeChild(line)
        for line in renderText(self.description, self.x, self.y, self.width, self.height):
            shape <= line

@dataclass
class Constraint(Note):
    pass

@dataclass
class Anchor(Relationship):
    source: (Note, Constraint) = None
    dest: Any = None
    name: str = ''


@dataclass
class FlowPort(CP):
    name: str = ''

    def getShape(self):
        p = self.pos
        return svg.rect(x=p.x-5, y=p.y-5, width=10, height=10, stroke_width=1, stroke='black', fill='lightgreen')
    def updateShape(self, shape):
        p = self.pos
        shape['x'], shape['y'], shape['width'], shape['height'] = int(p.x-5), int(p.y-5), 10, 10

    def getPos(self):
        return self.pos
    def getSize(self):
        return Point(1,1)

@dataclass
class FlowPortIn(FlowPort):
    pass

@dataclass
class FlowPortOut(FlowPort):
    pass

@dataclass
class FullPort(FlowPort):
    pass

@dataclass
class Block(Shape):
    description: str = ''
    ports: [FlowPort, FullPort] = field(default_factory=list)
    children: [Self] = field(default_factory=list)

    def getPointPosFunc(self, orientation, ports):
        match orientation:
            case Orientations.LEFT:
                return lambda i: Point(x=self.x, y=self.y + self.height / len(ports) / 2 * (2 * i + 1))
            case Orientations.RIGHT:
                return lambda i: Point(x=self.x + self.width,
                                                y=self.y + self.height / len(ports) / 2 * (2 * i + 1))
            case Orientations.TOP:
                return lambda i: Point(x=self.x + self.width / len(ports) / 2 * (2 * i + 1), y=self.y)
            case Orientations.BOTTOM:
                return lambda i: Point(x=self.x + self.width / len(ports) / 2 * (2 * i + 1), y=self.y + self.height)

    def getShape(self):
        g = svg.g()
        # Add the core rectangle
        g <= svg.rect(x=self.x,y=self.y, width=self.width, height=self.height, stroke_width="2",stroke="black",fill="white")
        # Add the ports
        port_shape_lookup = {}      # A lookup for when the port is clicked.
        sorted_ports = {orientation: sorted([p for p in self.ports if p.orientation == orientation], key=lambda x: x.order) \
                       for orientation in Orientations}
        for orientation in [Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM, Orientations.TOP]:
            ports = sorted_ports[orientation]
            pos_func = self.getPointPosFunc(orientation, ports)

            for i, p in enumerate(ports):
                p.pos = pos_func(i)
                s = p.getShape()
                g <= s
                port_shape_lookup[s] = p
        self.port_shape_lookup = port_shape_lookup

        # Add the text
        g <= renderText(self.name, x=self.x, y=self.y, width=self.width, height=self.height)

        # Return the group of objects
        return g

    def updateShape(self, shape):
        # Update the rect
        rect = shape.children[0]
        rect['x'], rect['y'], rect['width'], rect['height'] = self.x, self.y, self.width, self.height

        # Update the ports
        sorted_ports = {orientation: sorted([p for p in self.ports if p.orientation == orientation], key=lambda x: x.order) \
                       for orientation in Orientations}
        count = 0
        for orientation in [Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM, Orientations.TOP]:
            ports = sorted_ports[orientation]
            pos_func = self.getPointPosFunc(orientation, ports)

            for i, p in enumerate(ports):
                p.pos = pos_func(i)
                p.updateShape(shape.children[i+1+count])
            count += len(ports)

        # Delete the previous
        for i, line in enumerate(shape.children[1 + len(self.ports):]):
            # Remove the text elements
            shape.removeChild(line)
        for line in renderText(self.name, self.x, self.y, self.width, self.height):
            shape <= line

    def getConnectionTarget(self, ev):
        # Determine if one of the ports was clicked on.
        port = self.port_shape_lookup.get(ev.target, None)
        if port is None:
            return self
        return port

    def isConnected(self, target):
        return (target == self) or target in self.ports

@dataclass
class FullPortConnection(Relationship):
    name: str = ''
    source: (FlowPort, FlowPortOut) = field(default_factory=list)
    Dest: (FlowPort, FlowPortIn) = field(default_factory=list)

class BlockDefinitionDiagram(Diagram):
    allowed_blocks = [Note, Block]

diagrams = []


class BlockCreateWidget:
    height = 40
    margin = 10
    def __init__(self, diagram):
        self.diagram = ref(diagram)
        blocks = diagram.__class__.allowed_blocks
        g = svg.g()
        g <= svg.rect(x=0, width=2*self.margin+1.6*self.height, y=0, height=len(blocks)*(self.height+self.margin)+self.margin,
                      fill='white', stroke='black', stroke_width="2")
        for i, b in enumerate(blocks):
            instance = b(name=b.__name__, x=self.margin, y=i*(self.height+self.margin)+self.margin,
                         height=self.height, width=1.6*self.height)
            shape = instance.getShape()
            g <= shape

            def bindFunc(index, block):
                return lambda ev: self.onMouseDown(ev, index, block)

            shape.bind('mousedown', bindFunc(i, b))
        diagram.canvas <= g

    def onMouseDown(self, ev, index, block):
        diagram = self.diagram()
        if diagram is None:
            return
        # Simply create a new block at the default position.
        instance = block(name='', x=300, y=300, height=self.height, width=int(1.6*self.height))
        diagram.drop(instance)


def createDiagram(canvas_id, properties_id):
    canvas = document[canvas_id]
    diagram = BlockDefinitionDiagram(widgets=[BlockCreateWidget])
    diagrams.append(diagram)
    diagram.bind(canvas)





def test():
    canvas = document['canvas']
    #canvas.bind("click", lambda ev: alert("CLICK"))
    diagram = BlockDefinitionDiagram(widgets=[BlockCreateWidget])
    diagrams.append(diagram)
    diagram.bind(canvas)
    b1 = Note(x=100, y=400, width=100, height=40, name='MyBlock1', description="Dit is een test blok.")
    b2 = Block(x=300, y=40, width=100, height=40, name='MyBlock2', ports=[
        FlowPort(orientation=Orientations.LEFT, order=0, name='i1'),
        FlowPort(orientation=Orientations.RIGHT, order=1, name='o2'),
    ])
    b3 = Block(x=600, y=40, width=100, height=40, name='MyBlock3', ports=[
        FlowPort(orientation=Orientations.LEFT, order=0, name='i1'),
        FlowPort(orientation=Orientations.RIGHT, order=1, name='o2'),
    ])

    diagram.drop(b1)
    diagram.drop(b2)
    diagram.drop(b3)
    diagram.connect(b1, b2, Relationship)
    c = diagram.connections[0]
    c.waypoints = [Point(x=570, y=inf), Point(x=inf, y=100)]
    c.reroute([])

    document['NormalEditBtn'].bind('click', lambda ev: diagram.changeFSM(None))
    document['EditConnectionsBtn'].bind('click', lambda ev: diagram.changeFSM(ConnectionEditor(Relationship)))

window.createDiagram = createDiagram
