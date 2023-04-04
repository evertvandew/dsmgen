

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
from dataclasses import dataclass, field
from weakref import ref
import enum
import math
from math import inf


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
    def __rmul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)
    def __len__(self):
        return math.sqrt(self.x*self.x + self.y*self.y)
    def dot(self, other):
        return self.x*other.x + self.y*other.y
    def astuple(self):
        return (int(self.x), int(self.y))
    def transpose(self):
        return Point(x=self.y, y=-self.x)


class RoutingMethod(enum.IntEnum):
    CenterTCenter = 1
    Squared = 2

class RoutingStragegy:
    def decorate(self, connection, canvas):
        raise NotImplementedError
    def route(self, shape, all_blocks):
        raise NotImplementedError

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
        console.log("Handle was clicked on")
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


class XP(enum.IntEnum):
    LEFT = 1
    OVERLAP = 2
    RIGHT = 3
class YP(enum.IntEnum):
    BELOW = 1
    OVERLAP = 2
    ABOVE = 3

Directions = enum.IntEnum('Directions', "TOP LEFT BOTTOM RIGHT")

def routeSquare(start_block, finish_block, waypoints):
    def extend_wp(w):
        # Each wp will have one co-ordinate at infinity.
        if abs(w.x) == inf:
            return (Point(x=-inf, y=w.y), Point(x=inf, y=w.y))
        return (Point(x=w.x, y=-inf), Point(x=w.x, y=inf))

    ranges = [(start_block[0], start_block[0] + start_block[1])]
    ranges.extend([extend_wp(wp) for wp in waypoints])
    ranges.append((finish_block[0], finish_block[0] + finish_block[1]))
    centers = [(r[0]+r[1])/2 for r in ranges]

    points = []

    for i, j in zip(range(len(ranges)-1), range(1, len(ranges))):

        current_range, next_range = ranges[i], ranges[j]
        current_center, next_center = centers[i], centers[j]

        # Check if there can be a direct line between the ranges
        xpos = XP.LEFT if next_range[1].x < current_range[0].x else (
            XP.RIGHT if next_range[0].x > current_range[1].x else XP.OVERLAP
        )
        ypos = YP.BELOW if next_range[1].y < current_range[0].y else (
            YP.ABOVE if next_range[0].y > current_range[1].y else YP.OVERLAP
        )

        # Detect a waypoint that runs through the start of finish object
        handled = False
        if i==0:
            if next_range[0].x == -inf and (current_range[0].y <= next_center.y <= current_range[1].y):
                # peek ahead to see which side of the object we need to be
                if centers[j+1].x < current_center.x:
                    points.append(Point(x=current_range[0].x, y=next_center.y))
                else:
                    points.append(Point(x=current_range[1].x, y=next_center.y))
                handled = True
            elif next_range[0].y == -inf and (current_range[0].x <= next_center.x <= current_range[1].x):
                # peek ahead to see which side of the object we need to be
                if centers[j + 1].y < current_center.y:
                    points.append(Point(x=next_center.x, y=current_range[0].y))
                else:
                    points.append(Point(x=next_center.x, y=current_range[1].y))
                handled = True
        if j == len(ranges)-1:
            if current_range[0].x == -inf and (next_range[0].y <= current_center.y <= next_range[1].y):
                # Look behind to see which side of the object we need to be
                if centers[i-1].x < next_center.x:
                    points.append(Point(x=next_range[0].x, y=current_center.y))
                else:
                    points.append(Point(x=next_range[1].x, y=current_center.y))
                handled = True
            elif current_range[0].y == -inf and (next_range[0].x <= current_center.x <= next_range[1].x):
                # look behind to see which side of the object we need to be
                if centers[i- 1].y < next_center.y:
                    points.append(Point(x=current_center.x, y=next_range[0].y))
                else:
                    points.append(Point(x=current_center.x, y=next_range[1].y))
                handled = True

        #Detect situations where there is overlap between objects or waypoints
        if handled:
            pass
        elif ypos == YP.OVERLAP:
            if current_center.x < next_center.x:
                x1 = current_range[1].x
                x2 = next_range[0].x
            else:
                x1 = current_range[0].x
                x2 = next_range[1].x

            # If the whole block is overlapped, draw the line from the center of the smallest
            if current_range[0].y < next_range[0].y:
                if current_range[1].y > next_range[1].y:
                    y = next_center.y
                else:
                    y = (current_range[1].y + next_range[0].y) / 2
            else:
                if current_range[1].y > next_range[1].y:
                    y = (next_range[1].y + current_range[0].y) / 2
                else:
                    y = current_center.y

            points.append(Point(x=x1, y=y))
            points.append(Point(x=x2, y=y))
        elif xpos == XP.OVERLAP:
            # A vertical line
            if current_center.y < next_center.y:
                y1 = current_range[1].y
                y2 = next_range[0].y
            else:
                y1 = current_range[0].y
                y2 = next_range[1].y

            # If the whole block is overlapped, draw the line from the center of the smallest
            if current_range[0].x < next_range[0].x:
                if current_range[1].x > next_range[1].x:
                    x = next_center.x
                else:
                    x = (current_range[1].x + next_range[0].x) / 2
            else:
                if current_range[1].x > next_range[1].x:
                    x = (next_range[1].x + current_range[0].x) / 2
                else:
                    x = current_center.x


            points.append(Point(x=x, y=y1))
            points.append(Point(x=x, y=y2))
        else:
            # No overlap: draw a line in three parts.

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

            points.extend([start, p1, p2, end])

    return points

class RouteSquare(RoutingStragegy):
    def __init__(self):
        self.decorators = []
        self.dragged_index = None
    def mouseDownHandle(self, decorator_id, ev):
        console.log("Handle was clicked on")
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
        pass
    def deleteWaypoint(self):
        pass

    def decorate(self, connection, canvas):
        def bind(i, d):
            d.bind('mousedown', lambda ev: self.mouseDownHandle(i, ev))
        # Show a little stripe next to each line-piece
        self.decorators = []
        self.initial_pos = {}
        self.widget = connection
        self.handle_orientation = []
        for p1, p2 in zip(self.widget.points[:-1], self.widget.points[1:]):
            v = (p2 - p1)
            vn = v / len(v)
            c = (p1 + p2) / 2
            n = vn.transpose()
            self.handle_orientation.append('X' if abs(n.x) > abs(n.y) else 'Y')
            p1 = c + 10 * n - 20 * vn
            p2 = c + 10 * n + 20 * vn
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
        current_range = (shape.start.getPos(), shape.start.getPos() + shape.start.getSize())
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

    def handleDragStart(self, index, ev):
        console.log("Handle Drag Start")
        self.state = self.States.DRAGGING
        ev.stopPropagation()
        ev.preventDefault()

    def onMouseUp(self, diagram, ev):
        if self.state in [self.States.POTENTIAL_DRAG, self.States.DRAGGING]:
            self.state = self.States.DECORATED

    def onMouseMove(self, diagram, ev):
        if self.state in [self.States.NONE, self.States.DECORATED]:
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
            if self.state != self.States.NONE:
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
                if c.start == widget or c.finish == widget:
                    c.reroute(self.children)

    def bind(self, canvas):
        self.canvas = canvas
        canvas.bind('click', self.onClick)
        canvas.bind('mouseup', self.onMouseUp)
        canvas.bind('mousemove', self.onMouseMove)
        canvas.bind('mousedown', self.onMouseDown)
        canvas.bind('handle_drag_start', self.handleDragStart)
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

    def handleDragStart(self, ev):
        console.log(f"Handle Drag Start {list(ev.__dict__.keys())}")
        self.mouse_events_fsm and self.mouse_events_fsm.handleDragStart(self, ev)

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


def testSquareRouter():
    def mkPoints(*args):
        return [Point(x=x, y=y) for x, y in args]

    # Straight horizontal center2center line
    e = mkPoints((200,60), (300,60))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), [])
    assert e==r, f"Asser error: {r} is not as expected {e}"

    # Straight vertical center2center line
    e = mkPoints((150,80), (150,150))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), [])
    assert e==r, f"Asser error: {r} is not as expected {e}"

    # Straight horizontal off-center line
    e = mkPoints((200, 65), (300, 65))
    r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((300, 50), (100, 40)), [])
    assert e == r, f"Asser error: {r} is not as expected {e}"

    # Straight vertical off-center line
    e = mkPoints((160, 80), (160, 150))
    r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((120, 150), (100, 40)), [])
    assert e == r, f"Asser error: {r} is not as expected {e}"

    # Horizontal stepped line
    e = mkPoints((200, 60), (350,60), (350,120), (500,120))
    r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((500, 100), (100, 40)), [])
    assert e == r, f"Asser error: {r} is not as expected {e}"

    # Vertical stepped line
    e = mkPoints((150,80), (150,210), (270,210), (270,340))
    r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((220, 340), (100, 40)), [])
    assert e == r, f"Asser error: {r} is not as expected {e}"

    # Horizontal by single waypoint above
    e = mkPoints((150,80), (150,100), (350,100), (350,80))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), mkPoints((inf,100)))
    assert e==r, f"Asser error: {r} is not as expected {e}"

    # Horizontal by single waypoint below
    e = mkPoints((150,40), (150,20), (350,20), (350,40))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), mkPoints((inf,20)))
    assert e==r, f"Asser error: {r} is not as expected {e}"

    # Vertical by single waypoint to left
    e = mkPoints((200,60), (250,60), (250,170), (200,170))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), mkPoints((250, inf)))
    assert e==r, f"Asser error: {r} is not as expected {e}"

    # Vertical by single waypoint to right
    e = mkPoints((100,60), (50,60), (50,170), (100,170))
    r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), mkPoints((50, inf)))
    assert e==r, f"Asser error: {r} is not as expected {e}"


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
    c = diagram.connections[0]
    #c.waypoints = [Point(x=250, y=75)]

    document['NormalEditBtn'].bind('click', lambda ev: diagram.changeFSM(None))
    document['EditConnectionsBtn'].bind('click', lambda ev: diagram.changeFSM(ConnectionEditor(Relationship)))

test()
