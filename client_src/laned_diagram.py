"""
How does a laned diagram differ from a normal block diagram?

* There is only one instance of the type associated with the lane ('vertical_lane' or 'horizontal_lane') in each lane.
* These objects can be freely moved in the direction of the lane, moving them across lanes will insert them where released
  and move the other lanes over.


These differences are handled by giving the LanedDiagram different event handler state classes than the normal Diagram.

"""
from dataclasses import dataclass
from typing import override, List

from browser import svg
from data_store import UndoableDataStore
from modeled_shape import ModeledShape
from diagrams import ResizeStates, DiagramConfiguration, ResizeFSM
from modeled_diagram import ModeledDiagram
from storable_element import ReprCategory

"""
Development strategy:
* First implement adding laned blocks -> clipping them to each lane
* Implement connecting the lanes
* Loading the diagram from the database
* Implement moving the connections up and down.
* Implement moving the lanes left and right.
* Implement resizing the blocks -> and resizing the lanes with it.
* Implement deleting lane objects -- and shifting the others
* Implement deleting connections.

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
        print(f"Adding a block of type {type(block.model_entity).__name__}!", [c.__name__ for c in self.vertical_lane])
        # Create the block as usual
        result = super().addBlock(block)
        if block.category == ReprCategory.laned_block:
            self.lanes.append(block)
        return result

    def place_block(self, block_cls, details):
        """ In diagrams that have clipping, this function updates the location of a newly created block to comply with
            the diagram's rules.
        """
        print("Placing block:", block_cls, details)
        if details['category'] == ReprCategory.laned_block:
            if block_cls in self.vertical_lane:
                details['y'] = 60
                details['x'] = 75 + sum(b.width for b in self.lanes) + lane_margin * len(self.lanes) + details['width'] // 2
                details['lane_length'] = 1000
                print("Adding a vertical laned block", details)
            elif block_cls in self.horizontal_lane:
                print("Adding a horizontal laned block")
                details['x'] = 60
                details['y'] = sum(b.height for b in self.lanes) + lane_margin * len(self.lanes) + details['height'] // 2
                details['lane_length'] = 1000
                print("Adding a horizontal laned block", details)
        print("RE Placing block:", block_cls, details)
