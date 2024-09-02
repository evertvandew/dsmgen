"""
How does a laned diagram differ from a normal block diagram?

* There is only one instance of the type associated with the lane ('vertical_lane' or 'horizontal_lane') in each lane.
* These objects can be freely moved in the direction of the lane, moving them across lanes will insert them where released
  and move the other lanes over.


These differences are handled by giving the LanedDiagram different event handler state classes than the normal Diagram.

"""
from dataclasses import dataclass
from typing import override, List

from browser import svg, window, bind
from data_store import UndoableDataStore
from modeled_shape import ModeledShape, ModeledRelationship
from diagrams import ResizeStates, DiagramConfiguration, ResizeFSM
from modeled_diagram import ModeledDiagram
from point import Point
from shapes import Relationship, RoutingStrategy, Orientations, handle_class, getMousePos
from storable_element import ReprCategory

"""
Development strategy:
✔️ First implement adding laned blocks -> clipping them to each lane
✔ Implement connecting the lanes
✔ Loading the diagram from the database
* Implement moving the connections up and down.
* Implement moving the lanes left and right.
* Implement resizing the blocks -> and resizing the lanes with it.
* Implement deleting lane objects -- and shifting the others
* Implement message to self routing
✔ Implement deleting connections.

"""

lane_margin = 20

@dataclass
class LanedShape(ModeledShape):
    lane_length: float = 1000.0

    def getShape(self):
        shape = super().getShape()
        # The shape is a 'g' group, so we can freely add other elements to it.
        # We have a very thin visible line in a sequences diagram, so we need a second, thicker, invisible line for clicking on.
        x = self.x + self.width//2
        y = self.y+self.height
        lane_length = self.lane_length or 1000
        self.lines = [
            svg.line(x1=x, y1=y, x2=x, y2=y + lane_length, stroke='none', opacity=0.0, stroke_width='10'),
            svg.line(x1=x, y1=y, x2=x, y2=y + lane_length, stroke='black', stroke_width='2')
        ]
        _ = [shape <= l for l in self.lines]
        return shape

    def updateShape(self, shape=None):
        super().updateShape(shape)
        x = self.x + self.width//2
        y = self.y+self.height
        for l in self.lines:
            l.attrs['x1'] = int(x)
            l.attrs['x2'] = int(x)
            l.attrs['y1'] = int(y)
            l.attrs['y2'] = int(y + self.lane_length)

class LanedDragFSB(ResizeFSM):
    pass
    # def onMouseUp(self, diagram, ev) -> None:
    #     if self.state == ResizeStates.MOVING:
    #         # If this is a laned object, clip it to the correct lane.
    #     else:
    #         super().onMouseMove(diagram, ev)

class LanedDiagram(ModeledDiagram):
    vertical_lane: List[type] = []
    horizontal_lane: List[type] = []
    def __init__(self, config: DiagramConfiguration, widgets, datastore: UndoableDataStore, diagram_id: int):
        super().__init__(config, widgets, datastore, diagram_id)
        self.lanes = []

    @override
    def get_representation_category(self, block_cls) -> ReprCategory:
        if block_cls in self.vertical_lane or block_cls in self.horizontal_lane:
            return ReprCategory.laned_block
        return ReprCategory.block

    def addBlock(self, block):
        # Create the block as usual
        result = super().addBlock(block)
        if block.category == ReprCategory.laned_block:
            self.lanes.append(block)
        return result

    def place_block(self, block_cls, details):
        """ In diagrams that have clipping, this function updates the location of a newly created block to comply with
            the diagram's rules.
        """
        if details['category'] == ReprCategory.laned_block:
            if block_cls in self.vertical_lane:
                details['y'] = 60
                details['x'] = 75 + sum(b.width for b in self.lanes) + lane_margin * len(self.lanes) + details['width'] // 2
                details['lane_length'] = 1000
            elif block_cls in self.horizontal_lane:
                details['x'] = 60
                details['y'] = sum(b.height for b in self.lanes) + lane_margin * len(self.lanes) + details['height'] // 2
                details['lane_length'] = 1000

    def get_connection_repr(self, a, b):
        if a.category == ReprCategory.laned_block and b.category == ReprCategory.laned_block:
            return ReprCategory.laned_connection
        return ReprCategory.relationship

    def addConnection(self, connection: Relationship) -> None:
        if connection.category == ReprCategory.laned_connection:
            # Determine the offset for this message.
            max_offset = 0
            for c in self.connections:
                if c.category == ReprCategory.laned_connection:
                   if c.waypoints and c.waypoints[0].x > max_offset:
                       max_offset = c.waypoints[0].x
            connection.waypoints = [Point(max_offset + 30, max_offset + 30)]

        result = super().addConnection(connection)
        return result


class SequenceMessageRouter(RoutingStrategy):
    """ Specialized router for sequence diagrams.
        This router expects a single waypoint, which indicates the offset for this message on the object lifeline.
        The router creates the handle necessary to manipulate this offset.
    """
    name = 'sequence_msg'

    def __init__(self):
        self.drag_start = None
        self.orientation = 'V'
        self.initial_pos = None
        self.widget = None
        self.decorator = None

    def mouseDownHandle(self, ev):
        self.drag_start = getMousePos(ev)
        current = ev.target
        current.dispatchEvent(
            window.CustomEvent.new("handle_drag_start", {"bubbles": True, "detail": {'router': self}}))
        ev.stopPropagation()
        ev.preventDefault()

    def decorate(self, connection, canvas):
        return
        # Show a little stripe next to each line-piece
        self.decorator = []
        self.initial_pos = {}
        self.widget = connection
        self.original_handle_pos = []
        if connection.start.x == connection.finish.x:
            self.orientation = 'V'
            n = Point(0,1)
        else:
            self.orientation = 'H'
            n = Point(1,0)


        c = (connection.start.getPos()+connection.finish.getPos()) / 2
        p1 = c - 20*n
        p2 = c + 20*n

        self.original_handle_pos.append((p1, p2))
        decorator = svg.line(x1=p1.x, y1=p1.y, x2=p2.x, y2=p2.y, stroke_width=6, stroke="#29B6F2",
                             data_orientation=self.orientation, data_index=i, Class=handle_class)
        self.initial_pos = c
        _ = canvas <= decorator
        self.decorator = decorator
        decorator.bind('mousedown', self.mouseDownHandle)
    def clear_decorations(self):
        pass
    def route(self, shape, all_blocks):
        if self.orientation == 'V':
            n = Point(0,1)
            start_x = shape.start.getPos().x + shape.start.getSize().x//2
            start_y = min([shape.start.getPos().y+shape.start.getSize().y, shape.finish.getPos().y+shape.finish.getSize().y])
            delta_x = shape.finish.getPos().x + shape.finish.getSize().x//2 - shape.start.getPos().x - shape.start.getSize().x//2
            delta_y = 0
        else:
            n = Point(1,0)
            start_y = shape.start.getPos().y + shape.start.getSize().y // 2
            start_x = min(
                [shape.start.getPos().x + shape.start.getSize().x, shape.finish.getPos().x + shape.finish.getSize().x])
            delta_y = shape.finish.getPos().y + shape.finish.getSize().y // 2
            delta_x = 0
        start = Point(start_x, start_y) + Point(shape.waypoints[0].x*n.x, shape.waypoints[0].y*n.y)
        delta = Point(delta_x, delta_y)
        shape.path['d'] = f"M {start.x} {start.y} l {delta.x} {delta.y}"
        shape.selector['d'] = f"M {start.x} {start.y} l {delta.x} {delta.y}"
        shape.terminations = (start, start + delta)

    def dragEnd(self, canvas):
        pass


@dataclass
class LanedMessage(ModeledRelationship):
    category: ReprCategory = ReprCategory.laned_connection
    default_style = ModeledRelationship.default_style.copy()
    default_style.update(routing_method = SequenceMessageRouter.name)

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.laned_connection