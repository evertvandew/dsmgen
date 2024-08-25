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
        self.lines = [
            svg.line(x1=x, y1=y, x2=x, y2=y + self.lane_length, stroke='none', opacity=0.0, stroke_width='10'),
            svg.line(x1=x, y1=y, x2=x, y2=y + self.lane_length, stroke='black', stroke_width='2')
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
        # Clip the position of the block if it is a laned block.
        if type(block.model_entity) in self.vertical_lane:
            print("Adding a vertical laned block")
            self.lanes.append(block)
            block.y = 60
            block.x = sum(b.width for b in self.lanes) + lane_margin * len(self.lanes) + block.width//2
            #block.height = self.canvas.offsetHeight
            block.updateShape()
        elif type(block.model_entity) in self.horizontal_lane:
            print("Adding a horizontal laned block")
            self.lanes.append(block)
            block.x = 60
            block.y = sum(b.height for b in self.lanes) + lane_margin * len(self.lanes) + block.height//2
            #block.width = self.canvas.offsetWidth
            block.updateShape()

        return result