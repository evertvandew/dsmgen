"""
Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
import json
from typing import Dict, Type, Any
from weakref import ref

import data_store
from browser import console, svg
from browser.widgets.dialog import InfoDialog
from diagrams import Diagram, getMousePos, DiagramConfiguration
import shapes
from data_store import UndoableDataStore, ReprCategory, StorableElement, Collection, ReprCategory
from modeled_shape import ModeledRelationship, ModelEntity, ModeledShape, Port


class ModeledDiagram(Diagram):
    def __init__(self, config: DiagramConfiguration, widgets, datastore: UndoableDataStore, diagram_id: int):
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
                    #if source not in r.model_entity.ports:
                    #    r.model_entity.ports.append(source)
                    # Check it is represented in each representation
                    if not any(source.Id == p.model_entity.Id for p in r.ports):
                        p = repr_cls(parent=r.Id, model_entity=source, diagram=self.diagram_id)
                        self.datastore.add_complex(p)
                        # Redraw the shape
                        r.updateShape(r.shape)

                # Check if we need to create a PortLabel -- i.e. for a port owned by the diagram, not a block.
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
                        self.datastore.add_complex(p)
                        r.shape.updateShape()

        def deleteAction(event, source: StorableElement, ds, details):
            if type(source).__name__ in datastore.configuration.port_entities:
                # Remove the port from its parent `ports` collection.
                model_parent = self.datastore.get(Collection.block, source.parent)
                if source in model_parent.ports:
                    model_parent.ports.remove(source)
                # Find any representations of this port
                reprs = [p for c in self.children for p in getattr(c, 'ports', []) if p.model_entity.Id == source.Id]
                for r in reprs:
                    r.shape.remove()
                    parent = self.datastore.get(Collection.block_repr, r.parent)
                    # The representation doesn't need deleting: that is done by the data_store.
                    # Only remove them from the ports collection maintained by this class
                    parent.ports.remove(r)
                    self.datastore.update_cache(parent)
                # Find any relationships to this port
                to_delete = []
                for c in self.connections:
                    if c.model_entity.source.Id == source.Id or c.model_entity.target.Id == source.Id:
                        to_delete.append(c.model_entity)
                for e in to_delete:
                    self.datastore.delete(e)
            elif source.get_collection() in Collection.representations():
                if isinstance(source, Port):
                    # Remove the port from the block it belongs to, then redraw the block.
                    block = self.datastore.live_instances[Collection.block_repr][source.parent]
                    if source in block.ports:
                        block.ports.remove(source)
                        block.updateShape(block.shape)
                else:
                    Diagram.deleteBlock(self, source)

        def updateAction(event, source: StorableElement, ds, details):
            if type(source).__name__ in datastore.configuration.block_entities:
                # Find representations of this port
                reprs = [c for c in self.children if c.model_entity.Id == source.Id]
                # Update the shapes
                for r in reprs:
                    r.updateShape(r.shape)
            elif source.get_collection() in Collection.representations():
                # Support for the undo & redo actions.
                if source in self.children:
                    source.updateShape(source.shape)
                    self.rerouteConnections(source)
                else:
                    console.log("SOURCE not in children")



        datastore.subscribe('add/*', self, addAction)
        datastore.subscribe('delete/*', self, deleteAction)
        datastore.subscribe('update/*', self, updateAction)

    def child_update(self, action: shapes.UpdateType, child: StorableElement):
        match action:
            case shapes.UpdateType.add:
                self.datastore.add_complex(child)
            case shapes.UpdateType.update:
                self.datastore.update(child)
            case shapes.UpdateType.delete:
                self.datastore.delete(child)

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

    def get_connection_repr(self, a, b):
        return ReprCategory.relationship

    def connect_specific(self, a, b, cls):
        """ Use the information stored in the ModellingEntities to create the connection. """
        # First create the model_entity for the connection.
        connection = cls(source=a.model_entity, target=b.model_entity)
        # Create the representation of the connection.
        repr_cls = connection.get_representation_cls(self.get_connection_repr(a, b))
        representation = repr_cls(model_entity=connection, start=a, finish=b, diagram=self.diagram_id)
        # Add the connection to the diagram & database
        self.datastore and self.datastore.add_complex(representation)
        self.addConnection(representation)

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
        default_style = block_cls.getDefaultStyle()
        drop_details = dict(
            x=loc.x, y=loc.y,
            width=int(default_style.get('width', 64)), height=int(default_style.get('height', 40)),
            diagram=self.diagram_id,
        )
        category = self.get_representation_category(block_cls)
        # Determine the initial order
        order = len(self.children) + 1
        drop_details.update(category=category, order=order)
        self.place_block(block_cls, drop_details)
        block = self.datastore.create_representation(block_cls.__name__, data['Id'], drop_details)
        if not block:
            return

        # Add the block to the diagram
        self.addBlock(block)

    def createNewBlock(self, template) -> ModeledShape:
        instance = super().createNewBlock(template)
        self.datastore.add_complex(instance)
        return instance

    def place_block(self, block_cls, drop_details):
        pass

    def deleteBlock(self, block):
        self.datastore.delete(block)
        super().deleteBlock(block)

    def connect(self, a, b):
        """ Connect two blocks a and b. If necessary, the right connection type is selected by the User. """
        ta, tb = type(a.model_entity), type(b.model_entity)
        clss = self.config.get_allowed_connections(ta, tb) + self.config.get_allowed_connections(ta, Any)
        if not clss:
            d = InfoDialog('Can not connect', f"A {type(a).__name__} can not be connected to a {type(b).__name__}")
            return
        if len(clss) > 1:
            # Let the user select Connection type
            self.selectConnectionClass(clss, lambda cls: self.connect_specific(a, b, cls))
        else:
            self.connect_specific(a, b, clss[0])

    def mouseDownChild(self, widget: ModeledShape, ev, update_func=None):
        def uf(new_data: str):
            # Store the existing values to see if anything actually changed.
            new_values = json.loads(new_data)
            old_values = widget.asdict()
            widget.model_entity.update(new_values)
            # The styling of the widget can also be updated.
            if 'styling' in new_values:
                widget.updateStyle(**new_values['styling'])
            # Inform the datastore of any change
            self.datastore.update(widget.model_entity)
            if 'styling' in new_values:
                self.datastore.update(widget)

        super().mouseDownChild(widget, ev, uf)

    def mouseDownConnection(self, connection: ModeledRelationship, ev, update_function=None) -> None:
        def uf(new_data):
            # Store the existing values to see if anything actually changed.
            data = json.loads(new_data)
            connection.model_entity.update(data)
            # The styling of the widget can also be updated.
            if 'styling' in data:
                connection.updateStyle(**data['styling'])
            # Inform the datastore of any change
            self.datastore and self.datastore.update(connection)
        super().mouseDownConnection(connection, ev, uf)

    def trigger_event(self, widget, event_name, event_detail):
        super().trigger_event(widget, event_name, event_detail)
        self.datastore and self.datastore.trigger_event(event_name, widget, **event_detail)

    def dblclickChild(self, widget, ev):
        self.datastore.trigger_event('dblclick', self, target_dbid=widget.model_entity.Id,
                                     target_type=type(widget.model_entity).__name__)

    def onKeyDown(self, ev) -> None:
        if ev.key == 'z' and ev.ctrlKey:
            if ev.shiftKey:
                # Redo
                self.datastore.redo_one_action()
            else:
                # Undo
                self.datastore.undo_one_action()
        else:
            super().onKeyDown(ev)
