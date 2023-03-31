

try:
    from browser import document, alert, svg, console
except:
    document = {}
    alert = None
    class svg:
        pass
    svg_elements = ['line', 'circle', 'path', 'rect']
    functions = {k: (lambda self, **kargs: kwargs) for k in svg_elements}
    svg.__dict__.update(functions)



from typing import Union, Any, List, Self
from dataclasses import dataclass, field
from weakref import ref
import enum
import math


###############################################################################
## Primitive shapes

resize_role = 'resize_decorator'

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

    def getShape(self, diagram):
        return svg.rect(x=self.x,y=self.y, width=self.width, height=self.height, stroke_width="2",stroke="black",fill="white")
    def create(self, diagram, parent):
        self.diagram = ref(diagram)

        canvas = diagram.canvas
        self.subscribers = {}
        self.shape = self.getShape(diagram)
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

@dataclass
class CP:
    x: float
    y: float

    def onHover(self):
        pass

    def onConnect(self):
        pass

    def onDrag(self):
        pass


@dataclass
class Point:
    x: float
    y: float
    def __str__(self):
        return f"({self.x}, {self.y})"
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    def __truediv__(self, scalar):
        return Point(self.x/scalar, self.y/scalar)
    def __mul__(self, scalar):
        return Point(self.x*scalar, self.y*scalar)
    def __len__(self):
        return math.sqrt(self.x*self.x + self.y*self.y)
    def dot(self, other):
        return self.x*other.x + self.y*other.y
    def astuple(self):
        return (int(self.x), int(self.y))



def routeCenterToCenter(shape, all_blocks):
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


Directions = enum.IntEnum('Directions', "TOP LEFT BOTTOM RIGHT")

def routeSquare(shape, all_blocks):
    current_range = (shape.start.getPos(), shape.start.getPos() + shape.start.getSize())
    current_center = (current_range[0] + current_range[1])/2
    for wp in shape.waypoints:
        next_range = (wp, wp)
    next_range = (shape.finish.getPos(), shape.finish.getPos() + shape.finish.getSize())
    next_center = (next_range[0] + next_range[1])/2

    v = next_center - current_center
    if abs(v.y) > abs(v.x):
        if v.y > 0:
            quadrant = Directions.TOP
            start = Point(current_center.x, current_range[1].y)
            end = Point(next_center.x, next_range[0].y)
        else:
            quadrant = Directions.BOTTOM
            start = Point(current_center.x, current_range[0].y)
            end = Point(next_center.x, next_range[1].y)
    elif v.x > 0:
        quadrant = Directions.RIGHT
        start = Point(current_range[1].x, current_center.y)
        end = Point(next_range[0].x, next_center.y)
    else:
        quadrant = Directions.LEFT
        start = Point(current_range[0].x, current_center.y)
        end = Point(next_range[1].x, next_center.y)

    middle = (start + end) / 2
    if quadrant in [Directions.TOP, Directions.BOTTOM]:
            p1 = Point(current_center.x, middle.y)
            p2 = Point(next_center.x, middle.y)
    else:
            p1 = Point(middle.x, current_center.y)
            p2 = Point(middle.x, next_center.y)

    points = [p1, p2, end]
    waypoints = ''.join(f'L {p.x} {p.y} ' for p in points)
    shape.path['d'] = f"M {start.x} {start.y} {waypoints}"
    shape.selector['d'] = f"M {start.x} {start.y} {waypoints}"
    shape.terminations = (start, end)

    console.log(f"Quadrant: {quadrant}, {start} {points} {end}")

    return

    outside = []
    outside.append(next_range[1].x < current_range[0].x)
    outside.append(next_range[0].x > current_range[1].x)
    outside.append(next_range[1].y < current_range[0].y)
    outside.append(next_range[0].y > current_range[1].y)


    nr_outside = len([o for o in outside if o])
    console.log(f'Nr outside: {nr_outside}')
    if nr_outside <= 2:
        # Overlapping objects. Don't draw this line.
        pass
    elif nr_outside == 3:
        # Determine which side is inside
        i = outside.index(False)
        # zig-zag to the next bit.
        if i+1 == indices.LEFT:
            start = Point(current_range[1].x, (current_range[1].y+current_range[0].y)/2)
            end = Point(next_range[0].x, (next_range[1].y + next_range[0].y) / 2)
            middle = (start + end) / 2
            points = [start, Point(middle.x, start.y), Point(middle.x, end.y), end]

            waypoints = ''.join(f'L {p.x} {p.y} ' for p in points[1:])
            shape.path['d'] = f"M {points[0].x} {points[0].y} {waypoints}"
            shape.selector['d'] = f"M {points[0].x} {points[0].y} {waypoints}"
            self.terminations = (start, end)



@dataclass
class Relationship:
    start: Point
    finish: Point
    waypoints: List[Point]

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
        router = getattr(self, 'router', routeCenterToCenter)
        router(self, all_blocks)

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


Orientations = enum.IntEnum("Orientations", "TL TOP TR RIGHT BR BOTTOM BL LEFT")
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

def moveSingleHandle(decorators, shape, orientation):
    d = decorators[orientation]
    x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]
    d['cx'], d['cy'] = locations[orientation](x, y, width, height)

def moveHandles(decorators, shape, orientation):
    # Determine which markers to move
    for o in to_update[orientation]:
        moveSingleHandle(decorators, shape, o)

def moveAll(shape, decorators):
    for o in Orientations:
        moveSingleHandle(decorators, shape, o)



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
            self.unselect(self.widget)
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
            self.unselect(self.widget)
        fsm = RerouteStates(self.diagram)
        self.diagram.changeFSM(fsm)
        fsm.mouseDownConnection(diagram, widget, ev)

    def mouseDownBackground(self, diagram, ev):
        if self.widget and ev.target == self.widget.shape:
            self.state = self.States.MOVING
            return
        if ev.target == diagram.canvas:
            if self.state == self.States.DECORATED:
                self.unselect(diagram.selection)
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
            self.unselect(self.widget)

    def startResize(self, widget, orientation, ev):
        self.dragstart = getMousePos(ev)
        self.state = self.States.RESIZING
        self.initial_pos = widget.getPos()
        self.initial_size = widget.getSize()

    def unselect(self, widget):
        for dec in self.decorators.values():
            dec.remove()
        self.decorators = {}
        if self.widget:
            self.widget.unsubscribe(resize_role)
        self.widget = None
        self.state = self.States.NONE

    def select(self, widget):
        self.widget = widget
        shape = widget.shape

        self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2") for k in Orientations}
        x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]

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

        widget.subscribe(resize_role, lambda w: moveAll(w.shape, self.decorators))

    def onDrag(self, origin, original_size, delta):
        dx, dy, sx, sy, mx, my = orientation_details[self.dragged_handle]
        d = self.decorators[self.dragged_handle]
        shape = self.widget
        movement = Point(x=delta.x * dx, y=delta.y * dy)
        # alert(f"{delta}, {dx}, {dy}, {sx}, {sy}")
        shape.setPos(origin + movement)
        resizement = Point(x=original_size.x + sx * delta.x, y=original_size.y + sy * delta.y)
        shape.setSize(resizement)

        moveHandles(self.decorators, shape.shape, self.dragged_handle)
        self.diagram.rerouteConnections(shape)



class RerouteStates(BehaviourFSM):
    States = enum.IntEnum('States', 'NONE DECORATED POTENTIAL_DRAG DRAGGING')
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

    def mouseDownHandle(self, index, ev):
        self.dragged_index = index
        self.state = self.States.DRAGGING
        self.dragstart = getMousePos(ev)
        self.initial_pos = self.widget.waypoints[index]
        ev.stopPropagation()
        ev.preventDefault()

    def onMouseUp(self, diagram, ev):
        if self.state in [self.States.POTENTIAL_DRAG, self.States.DRAGGING]:
            self.state = self.States.DECORATED

    def onMouseMove(self, diagram, ev):
        if self.state in [self.States.NONE, self.States.DECORATED]:
            return
        delta = getMousePos(ev) - self.dragstart
        if self.state == self.States.POTENTIAL_DRAG:
            if len(delta) > 10:
                pos = getMousePos(ev)
                self.dragged_index = self.widget.insertWaypoint(pos)
                self.initial_pos = self.dragstart = self.widget.waypoints[self.dragged_index]
                self.clear_decorations()
                self.decorate()
                self.state = self.States.DRAGGING
        if self.state == self.States.DRAGGING:
            new_pos = self.initial_pos + delta
            handle = self.decorators[self.dragged_index]
            handle['cx'], handle['cy'] = new_pos.x, new_pos.y
            self.widget.waypoints[self.dragged_index] = new_pos
            diagram.rerouteConnections(self.widget)

    def onKeyDown(self, diagram, ev):
        if ev.key == 'Delete':
            if self.state != self.States.NONE and self.dragged_index is not None:
                self.widget.waypoints.pop(self.dragged_index)
                self.clear_decorations()
                self.decorate()
                diagram.rerouteConnections(self.widget)

    def delete(self, diagram):
        if self.state != self.States.NONE:
            self.clear_decorations()

    def clear_decorations(self):
        for d in self.decorators:
            d.remove()
        self.decorators = []

    def decorate(self):
        self.decorators = [svg.circle(cx=p.x, cy=p.y, r=5, stroke_width=0, fill="#29B6F2") for p in self.widget.waypoints]
        def bind(i, d):
            d.bind('mousedown', lambda ev: self.mouseDownHandle(i, ev))
        for i, d in enumerate(self.decorators):
            self.diagram.canvas <= d
            # Python shares variables inside a for loop by reference
            # So to avoid binding to the same handle x times, we need to call a function to make permanent copies.
            bind(i, d)


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
        if self.state in [self.States.A_SELECTED, self.States.RECONNECTING]:
            if diagram.allowsConnection(self.a_party, widget):
                if self.state == self.States.A_SELECTED:
                    diagram.connect(self.a_party, widget, self.connectionFactory)
                elif self.state == self.States.RECONNECTING:
                    match self.b_connection_role:
                        case self.ConnectionRoles.START:
                            self.connection.start = widget
                        case self.ConnectionRoles.FINISH:
                            self.connection.start = widget
                    diagram.reroute(self.connection)

                self.path.remove()
                self.state = self.States.NONE
        elif self.state == self.States.NONE:
            self.state = self.States.A_SELECTED
            self.a_party = widget
            # Create a temporary path to follow the mouse
            x, y = (widget.getPos() + widget.getSize()/2).astuple()
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

class Diagram:
    def __init__(self):
        self.selection = None
        self.mouse_events_fsm = None
        self.children = []
        self.connections = []
        self.decorators = []

    def drop(self, block):
        block.create(self, None)
        self.children.append(block)

    def allowsConnection(self, a, b):
        return True

    def connect(self, a, b, cls):
        connection = cls(start=a, finish=b, waypoints=[])
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
                if c.start == widget or c.finish == widget:
                    c.reroute(self.children)

    def bind(self, canvas):
        self.canvas = canvas
        canvas.bind('click', self.onClick)
        canvas.bind('mouseup', self.onMouseUp)
        canvas.bind('mousemove', self.onMouseMove)
        canvas.bind('mousedown', self.onMouseDown)
        document.bind('keydown', self.onKeyDown)

    def clickChild(self, widget, ev):
        pass

    def mouseDownChild(self, widget, ev):
        if not self.mouse_events_fsm:
            self.mouse_events_fsm = ResizeStates(self)
        self.mouse_events_fsm.mouseDownShape(self, widget, ev)

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

    def onHover(self):
        pass

    def getMenu(self):
        pass

    def onDrop(self):
        pass



###############################################################################
## Diagrams and shapes
@dataclass
class Note(Shape):
    description: str
    fold_size = 10
    def getPoints(self):
        x, y, w, h = self.x, self.y, self.width, self.height
        f = self.fold_size
        return ' '.join(f'{x+a},{y+b}' for a, b in [(0,0), (w-f,0), (w,f), (w-f,f), (w-f,0), (w,f), (w,h), (0,h)])
    def getShape(self):
        return svg.polygon(points=self.getPoints(), fill="yellow", stroke="black")
    def updateShape(self, shape):
        shape['points'] = self.getPoints()

@dataclass
class Constraint(Note):
    pass

@dataclass
class Anchor(Relationship):
    source: Union[Note, Constraint]
    dest: Any
    name: str = ''


@dataclass
class FlowPort(CP):
    name: str

@dataclass
class FullPort(CP):
    name: str

@dataclass
class Block(Shape):
    name: str
    description: str = ''
    ports: List[Union[FlowPort, FullPort]] = field(default_factory=list)
    children: List[Self] = field(default_factory=list)

@dataclass
class FullPortConnection(Relationship):
    name: str
    source: FullPort
    Dest: FullPort

@dataclass
class FlowPortConnection(Relationship):
    name: str
    source: FlowPort
    Dest: FlowPort


class BlockDefinitionDiagram(Diagram):
    allowed_blocks = [Note, Block]

diagrams = []

def test():
    canvas = document['canvas']
    #canvas.bind("click", lambda ev: alert("CLICK"))
    diagram = BlockDefinitionDiagram()
    diagrams.append(diagram)
    diagram.bind(canvas)
    b1 = Block(x=100, y=40, width=100, height=40, name='MyBlock1')
    b2 = Block(x=300, y=40, width=100, height=40, name='MyBlock2')
    diagram.drop(b1)
    diagram.drop(b2)
    diagram.connect(b1, b2, Relationship)
    diagram.connections[0].router = routeSquare

    document['NormalEditBtn'].bind('click', lambda ev: diagram.changeFSM(None))
    document['EditConnectionsBtn'].bind('click', lambda ev: diagram.changeFSM(ConnectionEditor(Relationship)))

test()
