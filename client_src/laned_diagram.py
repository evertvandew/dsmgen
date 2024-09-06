"""
How does a laned diagram differ from a normal block diagram?

* There is only one instance of the type associated with the lane ('vertical_lane' or 'horizontal_lane') in each lane.
* These objects can be freely moved in the direction of the lane, moving them across lanes will insert them where released
  and move the other lanes over.


These differences are handled by giving the LanedDiagram different event handler state classes than the normal Diagram.

"""
from dataclasses import dataclass
from enum import StrEnum
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
✔ Implement moving the connections up and down.
✔ Implement moving the lanes left and right -> shifting the lanes to the right.
✔ Implement resizing the blocks -> and resizing the lanes with it.
✔ Loading the diagram from the database -- especially taking the waypoints into account.
✔ Implement deleting lane objects -- and shifting the others
* Render the name of a message.
✔ Implement message to self routing
✔ Implement deleting connections.

"""


class LaneOrientation(StrEnum):
    Horizontal = 'H'
    Vertical = 'V'



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
    lane_margin = 20
    lane_offset = 90
    cross_offset = 60
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
                details['x'] = 75 + sum(b.width for b in self.lanes) + self.lane_margin * len(self.lanes) + details['width'] // 2
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
        if connection.category == ReprCategory.laned_connection and not connection.waypoints:
            # Determine the offset for this message.
            max_offset = 0
            for c in self.connections:
                if c.category == ReprCategory.laned_connection:
                   if c.waypoints and c.waypoints[0].x > max_offset:
                       max_offset = c.waypoints[0].x
            connection.waypoints = [Point(max_offset + 30, max_offset + 30)]
        result = super().addConnection(connection)
        return result

    def updateLanedBlock(self, _element):
        # Just re-order all blocks and locate them in their proper positions.
        # When in doubt, use brute force.
        keyfunc = (lambda b: b.x) if self.vertical_lane else (lambda b: b.y)
        order: List[LanedShape] = sorted((b for b in self.children if b.category==ReprCategory.laned_block), key=keyfunc)
        position = self.lane_offset
        for i, b in enumerate(order):
            b.order = i+1
            if self.vertical_lane:
                b.x = position
                position += b.width
            else:
                b.y = position
                position += b.height
            position += self.lane_margin
            # Update them all, the data_store will detect any real changes.
            self.datastore.update(b)

    def updateElement(self, element) -> None:
        if isinstance(element, LanedShape):
            self.updateLanedBlock(element)
        super().updateElement(element)


class SequenceMessageRouter(RoutingStrategy):
    """ Specialized router for sequence diagrams.
        This router expects a single waypoint, which indicates the offset for this message on the object lifeline.
        The router creates the handle necessary to manipulate this offset.
    """
    name = 'sequence_msg'
    self_msg_step = 30

    def __init__(self):
        self.drag_start = None
        self.orientation: LaneOrientation = LaneOrientation.Vertical
        self.initial_pos = None
        self.widget = None
        self.decorator = None

    def mouseDownHandle(self, ev):
        self.drag_start = getMousePos(ev)
        self.initial_pos = self.widget.waypoints[0]
        current = ev.target
        self.original_handle_pos = Point(float(current['x1']), float(current['y1']))
        current.dispatchEvent(
            window.CustomEvent.new("handle_drag_start", {"bubbles": True, "detail": {'router': self}}))
        ev.stopPropagation()
        ev.preventDefault()

    def sequenceMessagePoints(self, shape):
        # Check for message to self
        if shape.start == shape.finish:
            if self.orientation == LaneOrientation.Vertical:
                n = Point(0, 1)
                start_x = shape.start.getPos().x + shape.start.getSize().x // 2
                start_y = shape.start.getPos().y+shape.start.getSize().y
                delta_x = self.self_msg_step
                delta_y = self.self_msg_step
            else:
                n = Point(1, 0)
                start_y = shape.start.getPos().y + shape.start.getSize().y // 2
                start_x = shape.start.getPos().x+shape.start.getSize().x
                delta_y = self.self_msg_step
                delta_x = self.self_msg_step

        else:
            if self.orientation == LaneOrientation.Vertical:
                n = Point(0,1)
                start_x = shape.start.getPos().x + shape.start.getSize().x//2
                start_y = max([shape.start.getPos().y+shape.start.getSize().y, shape.finish.getPos().y+shape.finish.getSize().y])
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
        return start, delta, n

    def decorate(self, connection, canvas):
        # Show a little stripe next to each line-piece
        self.decorator = None
        self.initial_pos = {}
        self.widget = connection
        self.original_handle_pos = None
        start, delta, n = self.sequenceMessagePoints(connection)

        c = -10*n + start + delta / 2
        p1 = c - 10*n.transpose()
        p2 = c + 10*n.transpose()

        self.original_handle_pos = p1
        decorator = svg.line(x1=p1.x, y1=p1.y, x2=p2.x, y2=p2.y, stroke_width=6, stroke="#29B6F2",
                             data_orientation=self.orientation, data_index=0, Class=handle_class)
        self.initial_pos = c
        _ = canvas <= decorator
        self.decorator = decorator
        decorator.bind('mousedown', self.mouseDownHandle)
    def clear_decorations(self):
        if self.decorator:
            self.decorator.remove()
            self.decorator = None

    def dragHandle(self, pos):
        delta = pos - self.drag_start
        new_pos = self.initial_pos + delta
        h = self.decorator
        if self.orientation == LaneOrientation.Vertical:
            new_pos = Point(new_pos.y, new_pos.y)
            h['y1'] = int(self.original_handle_pos.y + delta.y)
            h['y2'] = int(self.original_handle_pos.y + delta.y)
        else:
            new_pos = Point(new_pos.x, new_pos.x)
            h['x1'] = int(self.original_handle_pos.x + delta.x)
            h['x2'] = int(self.original_handle_pos.x + delta.x)
        self.widget.waypoints[0] = new_pos

    def dragEnd(self, canvas):
        pass

    def route(self, shape, all_blocks):
        start, delta, n = self.sequenceMessagePoints(shape)
        if shape.start == shape.finish:
            if self.orientation == LaneOrientation.Vertical:
                shape.path['d'] = f"M {start.x} {start.y} h {delta.x} v {delta.y} h -{delta.x}"
                shape.selector['d'] = f"M {start.x} {start.y} h {delta.x} v {delta.y} h -{delta.x}"
                shape.terminations = (start, start + Point(0, delta.y))
            else:
                shape.path['d'] = f"M {start.x} {start.y} v {-delta.y} h {delta.x} v {delta.y}"
                shape.selector['d'] = f"M {start.x} {start.y} v {-delta.y} h {delta.x} v {delta.y}"
                shape.terminations = (start, start + Point(delta.x, 0))
        else:
            shape.path['d'] = f"M {start.x} {start.y} l {delta.x} {delta.y}"
            shape.selector['d'] = f"M {start.x} {start.y} l {delta.x} {delta.y}"
            shape.terminations = (start, start + delta)

    def deleteWaypoint(self):
        # Ignore: sequence messages have no user-editable waypoints that can be added or deleted.
        pass

@dataclass
class LanedMessage(ModeledRelationship):
    category: ReprCategory = ReprCategory.laned_connection
    default_style = ModeledRelationship.default_style.copy()
    default_style.update(routing_method = SequenceMessageRouter.name)

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.laned_connection