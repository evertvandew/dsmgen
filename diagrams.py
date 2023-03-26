

try:
    from browser import document, alert, svg
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
    width: float
    height: float

    def onHover(self, ev):
        pass

    def onDrag(self):
        pass

    def onConnect(self):
        pass

    def onEdit(self):
        pass

    def getMenu(self):
        pass

    def onClick(self, ev):
        ev.stopPropagation()
        if not (diagram := self.diagram()):
            return
        diagram.addResizeDecorator(self)


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
        r = svg.rect(x="40",y="100", width="40", height="40", stroke_width="2",stroke="black",fill="white")
        r.bind('click', self.onClick)
        r.bind('mouseenter', self.onMouseEnter)
        self.shape = r

        result = (canvas <=  r)

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


def getMousePos(ev):
    CTM = ev.target.getScreenCTM()
    return Point(x=int((ev.clientX - CTM.e)/CTM.a), y=int((ev.clientY-CTM.f)/CTM.d))

class Diagram:
    def __init__(self):
        self.children = []
        self.decorators = []

    def bind(self, canvas):
        self.canvas = canvas
        #canvas.bind('click', lambda ev: alert("CLICK2"))
        #canvas.bind('mousedown', self.onMouseDown)
        canvas.bind('click', self.onClick)

    def drop(self, block):
        block.create(self, None)
        #self.children.append(block)

    def onHover(self):
        pass

    def getMenu(self):
        pass

    def onDrop(self):
        pass

    def onClick(self, ev):
        pass

    def onMouseDown(self, ev):
        pass


    def addResizeDecorator(self, widget):
        shape = widget.shape

        # Use a lookup table to position each resize handle
        locations = {
            Orientations.TL:    lambda x,y,w,h: (x,     y+h),
            Orientations.TOP:   lambda x,y,w,h: (x+w//2, y+h),
            Orientations.TR:    lambda x,y,w,h: (x+w,   y+h),
            Orientations.RIGHT: lambda x,y,w,h: (x+w,   y+h//2),
            Orientations.BR:    lambda x,y,w,h: (x+w,   y),
            Orientations.BOTTOM:lambda x,y,w,h: (x+w//2, y),
            Orientations.BL:    lambda x,y,w,h: (x,     y),
            Orientations.LEFT:  lambda x,y,w,h: (x,     y+h//2),
        }

        self.decorators = {k: svg.circle(r=5, stroke_width=0, fill="#29B6F2") for k in Orientations}
        x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]

        for k, d in self.decorators.items():
            d['cx'], d['cy'] = locations[k](x, y, width, height)

        to_update = {
            Orientations.TL:    [Orientations.TR, Orientations.BL, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
            Orientations.TOP:   [Orientations.TL, Orientations.TR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP],
            Orientations.TR:    [Orientations.TL, Orientations.BR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
            Orientations.RIGHT: [Orientations.TR, Orientations.BR, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
            Orientations.BR:    [Orientations.BL, Orientations.TR, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
            Orientations.BOTTOM:[Orientations.BL, Orientations.BR, Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM],
            Orientations.BL:    [Orientations.BR, Orientations.TL, Orientations.LEFT, Orientations.RIGHT, Orientations.TOP, Orientations.BOTTOM],
            Orientations.LEFT:  [Orientations.TL, Orientations.BL, Orientations.LEFT, Orientations.TOP, Orientations.BOTTOM],
        }

        def moveSingleHandle(orientation):
            d = self.decorators[orientation]
            x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]
            d['cx'], d['cy'] = locations[orientation](x, y, width, height)


        def moveHandles(orientation):
            # Determine which markers to move
            for o in to_update[orientation]:
                moveSingleHandle(o)

        def bind_decorator(d, orientation):
            dx, dy, sx, sy, mx, my = {
                Orientations.TL: (1, 0, -1, 1, 1, 1),
                Orientations.TOP: (0, 0, 0, 1, 0, 1),
                Orientations.TR: (0, 0, 1, 1, 1, 1),
                Orientations.RIGHT: (0, 0, 1, 0, 1, 0),
                Orientations.BR: (0, 1, 1, -1, 1, 1),
                Orientations.BOTTOM: (0, 1, 0, -1, 0, 1),
                Orientations.BL: (1, 1, -1, -1, 1, 1),
                Orientations.LEFT: (1, 0, -1, 0, 1, 0)
            }[orientation]
            dragstart = None

            def onDrag(ev):
                if not dragstart:
                    return
                cood = getMousePos(ev)
                d['cx'], d['cy'] = cood.x if mx else dragstart.x, cood.y if my else dragstart.y
                delta = Point(x=cood.x-dragstart.x, y=cood.y-dragstart.y)
                #alert(f"{delta}, {dx}, {dy}, {sx}, {sy}")
                shape['x'] = x + dx*delta.x
                shape['y'] = y + dy*delta.y
                shape['width'] = width + sx*delta.x
                shape['height'] = height + sy*delta.y

                moveHandles(orientation)

            def dragStart(ev):
                nonlocal dragstart
                dragstart = getMousePos(ev)
                ev.stopPropagation()

            def dragEnd(ev):
                nonlocal dragstart, x, y, width, height
                dragstart = None
                x, y, width, height = [int(shape[k]) for k in ['x', 'y', 'width', 'height']]

            d.bind('mousedown', dragStart)
            self.canvas.bind('mouseup', dragEnd)
            self.canvas.bind('mousemove', onDrag)

        for orientation, d in self.decorators.items():
            self.canvas <= d
            bind_decorator(d, orientation)



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

@dataclass
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