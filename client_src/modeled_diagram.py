
import json
from typing import Dict, Type
from weakref import ref
from browser import console, svg
from browser.widgets.dialog import InfoDialog
from diagrams import Diagram, getMousePos, DiagramConfiguration
import shapes
from data_store import DataStore
from modeled_shape import ModeledRelationship, ModelEntity

class ModeledDiagram(Diagram):
    def __init__(self, config: DiagramConfiguration, widgets, datastore: DataStore, diagram_id: int):
        super().__init__(config, widgets)
        self.datastore = datastore               # Interface for getting and storing diagram state
        self.diagram_id = diagram_id

        def representationAction(event, source, ds, details):
            action, clsname, Id = event.split('/')
            item = details['item']
            if item.diagram != diagram_id:
                return
            item.updateShape(item.shape)

        datastore and datastore.subscribe('*/*Representation/*', self, representationAction)

    @classmethod
    def get_allowed_blocks(cls, block_cls_name: str, for_drop=False) -> Dict[str, Type[ModelEntity]]:
        raise NotImplementedError()

    def load_diagram(self):
        self.datastore.get_diagram_data(self.diagram_id, self.mass_update)

    def mass_update(self, data):
        """ Callback for loading an existing diagram """
        # Ensure blocks are drawn before the connections.
        for d in data:
            if isinstance(d, shapes.Shape):
                d.load(self)
        # Now draw the connections
        for d in data:
            if isinstance(d, shapes.Relationship):
                d.load(self)

    def connect_specific(self, a, b, cls):
        """ Use the information stored in the ModellingEntities to create the connection. """
        # First create the model_entity for the connection.
        connection = cls(source=a.model_entity, target=b.model_entity)
        # Create the representation of the connection.
        representation = ModeledRelationship(model_entity=connection, start=a, finish=b)
        # Add the connection to the diagram & database
        self.datastore and self.datastore.add(representation)
        super().addConnection(representation)

    def deleteConnection(self, connection):
        if connection in self.connections:
            self.datastore.delete(connection)
            super().deleteConnection(connection)

    def onDrop(self, ev):
        """ Handler for the 'drop' event.
            This function does some checks the block is valid and allowed to be dropped, then lets the
            `addBlock` function do the rest of the work.
        """
        assert ev.dataTransfer
        json_string = ev.dataTransfer.getData('entity')
        if not json_string:
            console.log('No data was submitted in the drop')
            return
        data = json.loads(json_string)
        loc = getMousePos(ev)

        # Create a representation for this block
        cls_name = data['__classname__']
        allowed_blocks = self.get_allowed_blocks(cls_name, for_drop=True)
        if cls_name not in allowed_blocks:
            InfoDialog("Not allowed", f"A {cls_name} can not be used in this diagram.", ok="Got it")
            return

        block_cls = allowed_blocks[data['__classname__']]
        repr_cls = block_cls.representation_cls()
        default_style = repr_cls.getDefaultStyle()
        drop_details = dict(
            x=loc.x, y=loc.y,
            width=int(default_style.get('width', 64)), height=int(default_style.get('height', 40)),
            diagram=self.diagram_id,
            block=data['Id']
        )
        block = self.datastore.create_representation(block_cls.__name__, data['Id'], drop_details)
        if not block:
            return

        # Add the block to the diagram
        self.addBlock(block)


    def deleteBlock(self, block):
        self.datastore.delete(block)
        super().deleteBlock(block)

    def mouseDownChild(self, widget, ev):
        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            old_values = widget.asdict()
            widget.update(new_data)
            # Inform the datastore of any change
            self.datastore and self.datastore.update(widget)

        super().mouseDownChild(widget, ev, uf)

    def mouseDownConnection(self, connection, ev):
        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            connection.update(new_data)
            # Inform the datastore of any change
            self.datastore and self.datastore.update(connection)
        super().mouseDownConnection(connection, ev, uf)

    def trigger_event(self, widget, event_name, event_detail):
        super().trigger_event(widget, event_name, event_detail)
        self.datastore and self.datastore.trigger_event(event_name, widget, **event_detail)

