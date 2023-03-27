

try:
    from browser import document, alert, svg, console
except:
    document = {}
    alert = None
    svg = {}

from typing import Union, Any, List, Self
from dataclasses import dataclass, field
from weakref import ref
import enum


###############################################################################
## Primitive shapes

@dataclass
class Shape:
    x: float
    y: float
    height: float
    width: float
    name: str

    def getPos(self):
        return Point(x=int(self.shape['x']), y=int(self.shape['y']))
    def setPos(self, new):
        self.shape['x'], self.shape['y'] = new.x, new.y
        for s in self.subscribers.values():
            s(self)
    def getSize(self):
        return Point(x=int(self.shape['width']), y=int(self.shape['height']))

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

    def create(self, diagram, parent):
        self.diagram = ref(diagram)

        canvas = diagram.canvas
        r = svg.rect(x=self.x,y=self.y, width=self.width, height=self.height, stroke_width="2",stroke="black",fill="white")
        self.subscribers = {}
        self.shape = r
        canvas <=  r

        r.bind('click', self.onClick)
        r.bind('mousedown', self.onMouseDown)

    def destroy(self):
        pass

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

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

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

ResizeStates = enum.IntEnum('ResizeStates', 'NONE DECORATED MOVING RESIZING')

class Diagram:
    resize_role = 'resize_decorator'
    def __init__(self):
        self.children = []
        self.decorators = {}
        self.dragstart = None
        self.dragged_handle = None
        self.selection = None
        self.initial_pos = None
        self.initial_size = None
        self.resizestate = ResizeStates.NONE

    def bind(self, canvas):
        self.canvas = canvas
        #canvas.bind('click', lambda ev: alert("CLICK2"))
        #canvas.bind('mousedown', self.onMouseDown)
        canvas.bind('click', self.onClick)
        canvas.bind('mouseup', self.onMouseUp)
        canvas.bind('mousemove', self.onMouseMove)
        canvas.bind('mousedown', self.onMouseDown)

    def clickChild(self, widget, ev):
        pass

    def mouseDownChild(self, widget, ev):
        if self.resizestate != ResizeStates.NONE and self.selection != widget:
            self.unselect(self.selection)
        if not self.selection:
            self.select(widget)
        self.resizestate = ResizeStates.MOVING
        self.dragstart = getMousePos(ev)
        self.initial_pos = widget.getPos()
        ev.stopPropagation()
        ev.preventDefault()

    def onClick(self, ev):
        pass

    def onMouseDown(self, ev):
        if self.selection and ev.target == self.selection.shape:
            self.resizestate = ResizeStates.MOVING
        if ev.target == self.canvas:
            if self.resizestate == ResizeStates.DECORATED:
                self.unselect(self.selection)
        self.dragstart = getMousePos(ev)
        if self.selection:
            self.initial_pos = self.selection.getPos()

    def onMouseUp(self, ev):
        if self.resizestate == ResizeStates.RESIZING:
            self.dragEnd(ev)
            self.resizestate = ResizeStates.DECORATED
        if self.resizestate == ResizeStates.MOVING:
            self.resizestate = ResizeStates.DECORATED

    def onMouseMove(self, ev):
        if self.resizestate == ResizeStates.RESIZING:
            self.onDrag(ev)
        if self.resizestate == ResizeStates.MOVING:
            self.selection.setPos(self.initial_pos + getMousePos(ev) - self.dragstart)

    def drop(self, block):
        block.create(self, None)
        #self.children.append(block)

    def onHover(self):
        pass

    def getMenu(self):
        pass

    def onDrop(self):
        pass


    def moveSingleHandle(self, orientation):
        d = self.decorators[orientation]
        x, y, width, height = [int(self.selection.shape[k]) for k in ['x', 'y', 'width', 'height']]
        d['cx'], d['cy'] = locations[orientation](x, y, width, height)

    def moveHandles(self, orientation):
        # Determine which markers to move
        for o in to_update[orientation]:
            self.moveSingleHandle(o)

    def moveAll(self, w):
        if w == self.selection:
            if not self.decorators:
                # We should have been unsubscribed
                self.clearResizeDecorator()
            for o in Orientations:
                self.moveSingleHandle(o)

    def onDrag(self, ev):
        if not self.dragstart:
            return
        dx, dy, sx, sy, mx, my = orientation_details[self.dragged_handle]
        d = self.decorators[self.dragged_handle]
        shape = self.selection.shape
        cood = getMousePos(ev)
        d['cx'], d['cy'] = cood.x if mx else self.dragstart.x, cood.y if my else self.dragstart.y
        delta = Point(x=cood.x - self.dragstart.x, y=cood.y - self.dragstart.y)
        # alert(f"{delta}, {dx}, {dy}, {sx}, {sy}")
        shape['x'] = self.initial_pos.x + dx * delta.x
        shape['y'] = self.initial_pos.y + dy * delta.y
        shape['width'] = self.initial_size.x + sx * delta.x
        shape['height'] = self.initial_size.y + sy * delta.y

        self.moveHandles(self.dragged_handle)

    def dragEnd(self, ev):
        self.dragstart = None
        x, y, width, height = [int(self.selection.shape[k]) for k in ['x', 'y', 'width', 'height']]
        self.initial_pos = self.selection.getPos()
        self.initial_size = self.selection.getSize()
        ev.stopPropagation()
        ev.preventDefault()

    def unselect(self, widget):
        for dec in self.decorators.values():
            dec.remove()
        self.decorators = {}
        if self.selection:
            self.selection.unsubscribe(self.resize_role)
        self.selection = None
        self.resizestate = ResizeStates.NONE

    def select(self, widget):
        if self.resizestate != ResizeStates.NONE:
            return

        self.selection = widget
        shape = widget.shape

        self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2") for k in Orientations}
        x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]

        self.initial_pos = Point(x=x, y=y)
        self.initial_size = Point(x=width, y=height)

        for k, d in self.decorators.items():
            d['cx'], d['cy'] = locations[k](x, y, width, height)

        def bind_decorator(d, orientation):
            def dragStart(ev):
                self.dragged_handle = orientation
                self.dragstart = getMousePos(ev)
                self.resizestate = ResizeStates.RESIZING
                self.initial_pos = widget.getPos()
                self.initial_size = widget.getSize()
                ev.stopPropagation()

            d.bind('mousedown', dragStart)

        for orientation, d in self.decorators.items():
            self.canvas <= d
            bind_decorator(d, orientation)

        widget.subscribe(self.resize_role, self.moveAll)
        self.resizestate = ResizeStates.DECORATED




###############################################################################
## Diagrams and shapes
@dataclass
class Note(Shape):
    description: str

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
    diagram.drop(Block(x=100, y=40, width=200, height=20, name='MyBlock'))

test()
