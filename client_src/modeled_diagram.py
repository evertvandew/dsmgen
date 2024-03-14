
import json
from typing import Dict, Type
from weakref import ref

import data_store
from browser import console, svg
from browser.widgets.dialog import InfoDialog
from diagrams import Diagram, getMousePos, DiagramConfiguration
import shapes
from data_store import DataStore, ReprCategory, StorableElement, Collection, ReprCategory
from modeled_shape import ModeledRelationship, ModelEntity

class ModeledDiagram(Diagram):
    def __init__(self, config: DiagramConfiguration, widgets, datastore: DataStore, diagram_id: int):
        super().__init__(config, widgets)
        self.datastore = datastore               # Interface for getting and storing diagram state
        self.diagram_id = diagram_id

        def addAction(event, source: StorableElement, ds, details):
            """ Perform specific actions when a new record is created """
            ## If a new port is added to the model, check if it is added to any block shown here.
            if type(source).__name__ in datastore.configuration.port_entities:
                # Check if it is owned by any block represented directly.
                reprs = [c for c in self.children if c.model_entity.Id is source.parent]
                for r in reprs:
                    repr_cls = source.get_representation_cls(ReprCategory.port)
                    # Check it is in the ports collection of each model_entity
                    if source not in r.model_entity.ports:
                        r.model_entity.ports.append(source)
                    # Check it is represented in each representation
                    if not source in [p.model_entity for p in r.ports]:
                        p = repr_cls(block=source.Id, parent=r.Id, model_entity=source, diagram=self.diagram_id)
                        self.datastore.add(p)
                        r.ports.append(p)
                        # Redraw the shape
                        r.updateShape(r.shape)

                # Check if it is owned by a diagram block whose diagram is shown here
                if source.parent == self.diagram_id:
                    # Now we need to create a PortLabel
                    repr_cls = source.get_representation_cls(ReprCategory.block)
                    self.addBlock(repr_cls(model_entity=source, block=source.Id, diagram=self.diagram_id))

                # Check if it is owned by a block that is instantiated here.
                reprs = [c for c in self.children if getattr(getattr(c, '_definition', None), 'Id', -1) == source.parent]
                for r in reprs:
                    repr_cls = source.get_representation_cls(ReprCategory.port)
                    # Check it is in the ports collection of each _definition
                    if source not in r._definition.ports:
                        r._definition.append(source)
                    # Check it is represented
                    if not source in [p.model_entity for p in r.ports]:
                        p = repr_cls(block=source.Id, parent=r.Id, model_entity=source, diagram=self.diagram_id)
                        r.ports.append(p)
                        self.datastore.add(p)
                        r.shape.updateShape()

        def deleteAction(event, source: StorableElement, ds, details):
            if type(source).__name__ in datastore.configuration.port_entities:
                # Find any representations of this port
                reprs = [p for c in self.children for p in getattr(c, 'ports', []) if p.model_entity.Id == source.Id]
                for r in reprs:
                    r.shape.remove()
                    self.datastore.delete(r)
                    parent = self.datastore.get(Collection.block_repr, r.parent)
                    parent.ports.remove(r)

        datastore.subscribe('add/*', self, addAction)
        datastore.subscribe('delete/*', self, deleteAction)

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
        representation = ModeledRelationship(model_entity=connection, start=a, finish=b, diagram=self.diagram_id)
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
        allowed_blocks = self.get_allowed_blocks(for_drop=True)
        if cls_name not in allowed_blocks:
            InfoDialog("Not allowed", f"A {cls_name} can not be used in this diagram.", ok="Got it")
            return

        block_cls = allowed_blocks[data['__classname__']]
        repr_cls = block_cls.get_representation_cls(ReprCategory.block)
        default_style = repr_cls.getDefaultStyle()
        drop_details = dict(
            x=loc.x, y=loc.y,
            width=int(default_style.get('width', 64)), height=int(default_style.get('height', 40)),
            diagram=self.diagram_id,
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
        def uf(new_data: str):
            # Store the existing values to see if anything actually changed.
            new_values = json.loads(new_data)
            old_values = widget.asdict()
            widget.model_entity.update(new_values)
            # Inform the datastore of any change
            self.datastore and self.datastore.update(widget.model_entity)

        super().mouseDownChild(widget, ev, uf)

    def mouseDownConnection(self, connection, ev):
        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            data = json.loads(new_data)
            connection.model_entity.update(data)
            # Inform the datastore of any change
            self.datastore and self.datastore.update(connection)
        super().mouseDownConnection(connection, ev, uf)

    def trigger_event(self, widget, event_name, event_detail):
        super().trigger_event(widget, event_name, event_detail)
        self.datastore and self.datastore.trigger_event(event_name, widget, **event_detail)

