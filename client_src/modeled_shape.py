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
from typing import Any, Self, List, Dict, Optional, cast, override, Callable
from dataclasses import dataclass, field
from enum import StrEnum
import json
from browser import svg, document, console
from diagrams import Shape, Relationship, CP, Point, Orientations
import shapes
from svg_shapes import MsgShape, HAlign
from context_menu import mk_context_menu
from storable_element import StorableElement, Collection, ReprCategory, from_dict
from data_store import ExtendibleJsonEncoder, DataStore
from point import load_waypoints
from copy import deepcopy, copy
from property_editor import getDetailsPopup
from model_interface import ModelEntity


class RelationAnchor(StrEnum):
    Center = 'C'
    Start = 'S'
    End = 'E'

###############################################################################
@dataclass
class ModelRepresentation(StorableElement):
    Id: int = 0
    model_entity: ModelEntity = None
    diagram: int = 0                    # Diagram in which this representation is displayed.

    @classmethod
    def repr_category(cls) -> ReprCategory:
        raise NotImplementedError()

    def getShape(self):
        raise NotImplementedError()

    def copy(self, ignore=None) -> Self:
        ignore = ignore or ['model_entity', 'id']
        result = type(self)(**{f.name: copy(getattr(self, f.name)) for f in self.fields() if f.name not in ignore})
        result.model_entity = self.model_entity
        return result

    def get_model_details(self) -> Optional[Self]:
        return self.model_entity


def getModeledStyle(modeled_item, key, default=None) -> Optional[str]:
    """ Allow model definitions to override styling """
    if hasattr(modeled_item.model_entity, 'getStyle'):
        if style := modeled_item.model_entity.getStyle(key):
            return style
    if key in modeled_item.styling:
        return modeled_item.styling[key]
    defaults = modeled_item.getDefaultStyle()
    if key in defaults:
        return defaults[key]
    if default is not None:
        return default
    raise RuntimeError(f"Trying to retrieve unknown styling element {key}")


@dataclass
class ModeledShape(Shape, ModelRepresentation):
    default_style = dict(blockcolor='#ffffff')
    TextWidget = shapes.Text('text')
    category: ReprCategory = ReprCategory.block

    @property
    def text(self):
        return self.model_entity.get_text(0)

    @property
    def block(self):
        storable_entity = cast(StorableElement, self.model_entity)
        return storable_entity.Id

    def asdict(self, ignore: List[str]=None) -> Dict[str, Any]:
        ignore = (ignore or []) + ['model_entity', 'ports']
        details = StorableElement.asdict(self, ignore=ignore)
        storable_entity = cast(StorableElement, self.model_entity)
        details['block'] = storable_entity.Id
        if 'children' in details:
            del details['children']
        return details

    def getShape(self):
        # This shape consists of two parts: the text and the outline.
        shape_type = self.getShapeDescriptor()
        g = svg.g()
        _ = g <= shape_type.getShape(self)
        _ = g <= self.TextWidget.getShape(self)
        g.attrs['data-category'] = self.repr_category().value
        g.attrs['data-rid'] = self.Id
        storable_entity = cast(StorableElement, self.model_entity)
        g.attrs['data-mid'] = storable_entity.Id
        return g

    def updateShape(self, shape=None):
        shape = shape or self.shape
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(shape.children[0], self)
        self.TextWidget.updateShape(shape.children[1], self)

    def getDefaultStyle(self):
        style = {}
        style.update(self.TextWidget.getDefaultStyle())
        style.update(self.default_style)
        style.update(self.model_entity.getDefaultStyle())
        return style

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.block

    @classmethod
    def is_instance_of(cls) -> bool:
        return False

    def getShapeDescriptor(self) -> shapes.BasicShape:
        shape_name = self.model_entity.getDefaultStyle().get('shape', 'rect')
        return shapes.BasicShape.getDescriptor(shape_name)

    @classmethod
    def get_collection(cls) -> Collection:
        return Collection.block_repr

    def get_editable_parameters(self):
        return self.model_entity.get_editable_parameters()

    def get_db_table(cls):
        return '_BlockRepresentation'

    @override                                           # From Stylable
    def getStyle(self, key, default=None):
        """ Allow model definitions to override styling """
        return getModeledStyle(self, key, default)


@dataclass
class Port(CP, ModelRepresentation):
    # These two items have slightly illogical names. That is because they are stored in the database in
    # the same table as regular blocks, so that connections can be made to them.
    parent: Optional[int] = None    # The block this port belongs to.
    category: ReprCategory = ReprCategory.block

    def __post_init__(self):
        self.shape = None
        self.pos: Point = Point(0, 0)

    @property
    def block(self):
        storable_entity = cast(StorableElement, self.model_entity)
        return storable_entity.Id

    def getShape(self):
        p = self.pos
        shape = svg.rect(x=p.x-5, y=p.y-5, width=10, height=10, stroke_width=1, stroke='black', fill='lightgreen')
        shape.attrs['data-class'] = type(self).__name__
        shape.attrs['data-category'] = int(ReprCategory.port)
        shape.attrs['data-rid'] = self.Id
        storable_entity = cast(StorableElement, self.model_entity)
        shape.attrs['data-mid'] = storable_entity.Id
        return shape
    def updateShape(self, shape=None):
        shape = shape or self.shape
        p = self.pos
        shape['x'], shape['y'], shape['width'], shape['height'] = int(p.x-5), int(p.y-5), 10, 10

    def getPos(self):
        return self.pos
    def getSize(self):
        return Point(1,1)

    def getLogicalClass(self):
        return getattr(self, 'logical_class', None)

    @classmethod
    def get_collection(cls) -> Collection:
        return Collection.block_repr

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.port

    def asdict(self, ignore: List[str]=None) -> Dict[str, Any]:
        ignore = (ignore or []) + ['model_entity', 'id']
        details = StorableElement.asdict(self, ignore=ignore)
        return details

    def get_db_table(cls):
        return '_BlockRepresentation'

@dataclass
class ModeledShapeAndPorts(ModeledShape):
    ports: List[Port] = field(default_factory=list)
    children: [Self] = field(default_factory=list)

    def asdict(self, ignore: List[str]=None) -> Dict[str, Any]:
        details = super().asdict(ignore)
        return details

    def copy(self, ignore=None) -> Self:
        ignore = (ignore or []) + ['ports', 'children', 'model_entity', 'id']
        result = super().copy(ignore=ignore)
        result.ports = self.ports
        result.children = self.children
        return result

    @classmethod
    def getShapeDescriptor(cls):
        return shapes.BasicShape.getDescriptor("rect")

    def getPointPosFunc(self, orientation, ports):
        match orientation:
            case Orientations.LEFT:
                return lambda i: Point(x=self.x, y=self.y + self.height / len(ports) / 2 * (2 * i + 1))
            case Orientations.RIGHT:
                return lambda i: Point(x=self.x + self.width,
                                                y=self.y + self.height / len(ports) / 2 * (2 * i + 1))
            case Orientations.TOP:
                return lambda i: Point(x=self.x + self.width / len(ports) / 2 * (2 * i + 1), y=self.y)
            case Orientations.BOTTOM:
                return lambda i: Point(x=self.x + self.width / len(ports) / 2 * (2 * i + 1), y=self.y + self.height)

    def getShape(self):
        g = svg.g()
        # Add the core rectangle
        shape_type = self.getShapeDescriptor()
        _ = g <= shape_type.getShape(self)
        # Add the text
        _ = g <= self.TextWidget.getShape(self)
        # Add the ports
        port_shape_lookup = {}      # A lookup for when the port is clicked.
        sorted_ports = {orientation: sorted([p for p in self.ports if p.orientation == orientation], key=lambda x: x.order) \
                       for orientation in Orientations}
        for orientation in [Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM, Orientations.TOP]:
            ports = sorted_ports[orientation]
            pos_func = self.getPointPosFunc(orientation, ports)

            for i, p in enumerate(ports):
                p.pos = pos_func(i)
                s = p.getShape()
                _ = g <= s
                p.shape = s
                port_shape_lookup[s] = p
        self.port_shape_lookup = port_shape_lookup

        g.attrs['data-category'] = int(ReprCategory.block)
        g.attrs['data-rid'] = self.Id
        storable_entity = cast(StorableElement, self.model_entity)
        g.attrs['data-mid'] = storable_entity.Id

        # Return the group of objects
        return g

    def updateShape(self, shape=None):
        shape = shape or self.shape
        # Update the rect
        rect = shape.children[0]
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(rect, self)
        text = shape.children[1]
        self.TextWidget.updateShape(text, self)

        # Update the ports
        sorted_ports = {orientation: sorted([p for p in self.ports if p.orientation == orientation], key=lambda x: x.order) \
                       for orientation in Orientations}

        # Delete any ports no longer used
        deleted = [s for s, p in self.port_shape_lookup.items() if p not in self.ports]
        for s in deleted:
            s.remove()
        shape_lookup = {p.Id: s for s, p in self.port_shape_lookup.items()}

        for orientation in [Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM, Orientations.TOP]:
            ports = sorted_ports[orientation]
            pos_func = self.getPointPosFunc(orientation, ports)
            for i, p in enumerate(ports):
                p.pos = pos_func(i)
                if p.Id in shape_lookup:
                    p.updateShape(shape_lookup[p.Id])
                else:
                    # Get the shape for the port
                    s = p.getShape()
                    p.shape = s
                    _ = shape <= s
                    self.port_shape_lookup[s] = p

    def getConnectionTarget(self, ev):
        # Determine if one of the ports was clicked on.
        port = self.port_shape_lookup.get(ev.target, None)
        if port is None:
            return self
        return port

    def isConnected(self, target):
        return (target == self) or target in self.ports

    def getDefaultStyle(self):
        defaults = super().getDefaultStyle()
        defaults.update(self.default_style)
        return defaults

    @classmethod
    def is_instance_of(cls):
        return False

    def get_allowed_ports(self):
        return self.model_entity.get_allowed_ports()


@dataclass
class ModeledRelationship(Relationship, ModelRepresentation):
    start: ModeledShape = None
    finish: ModeledShape = None
    category: ReprCategory = ReprCategory.relationship

    def __post_init__(self):
        super().__post_init__()
        self.text_widgets = None

    @property
    def relationship(self):
        storable_entity = cast(StorableElement, self.model_entity)
        return storable_entity.Id

    def create(self, owner, all_blocks):
        # Add the text boxes to the diagram
        # The text shape objects are cached, check if they need to be created.
        def mk_getter(index: int) -> Callable[[], str]:
            return lambda: self.model_entity.get_text(index)
        if self.model_entity:
            self.text_widgets = {}
            for anchor, text_nr in self.model_entity.get_anchor_descriptor().items():
                tw = shapes.TextBox(text_getter = mk_getter(text_nr))
                tw.default_style['halign'] = {
                    RelationAnchor.Center: HAlign.CENTER,
                    RelationAnchor.Start: HAlign.LEFT,
                    RelationAnchor.End: HAlign.RIGHT
                }[anchor]
                self.text_widgets[anchor] = tw
                tw.width = 64
                tw.height = 24
                tw.create(owner)

        super().create(owner, all_blocks)

    def getDefaultStyle(self):
        style = {}
        # TODO: Add support for texts with the connection # style.update(self.TextWidget.getDefaultStyle())
        style.update(self.default_style)
        style.update(self.model_entity.getDefaultStyle())
        return style

    def onContextMenu(self, ev):
        ev.stopPropagation()
        ev.preventDefault()
        storable_entity = cast(StorableElement, self.model_entity)
        msgs = storable_entity.get_messages()
        def bind_add_msg_action(cls):
            def do_add(ev):
                def callback(data):
                    new_object = cls(parent=self.diagram, association=storable_entity.Id, **data)
                    new_shape = Message(model_entity=new_object, parent=self.Id, diagram=self.diagram)
                    self.add_message(new_shape)

                getDetailsPopup(cls, callback)
            return cls.__name__, do_add

        d = mk_context_menu(
            create=dict(bind_add_msg_action(c) for c in msgs),
        )
        _ = document <= d
        d.showModal()

    def add_message(self, new_shape):
        super().add_message(new_shape)
        self.owner.child_update(shapes.UpdateType.add, new_shape)
        new_shape.create(self.owner)

    def copy(self, ignore:Optional[List[str]]=None) -> Self:
        ignore = (ignore or []) + ['start', 'finish', 'model_entity', 'id']
        result = super().copy(ignore=ignore)
        result.start = self.start
        result.finish = self.finish
        # The waypoints need to be deep-copied
        result.waypoints = deepcopy(self.waypoints)
        return result

    @classmethod
    def from_dict(cls, data_store: DataStore, **details) -> Self:
        self = from_dict(cls, **details)
        self.start = data_store.get(Collection.block_repr, details['source_repr_id'])
        self.finish = data_store.get(Collection.block_repr, details['target_repr_id'])
        self.waypoints = load_waypoints(details['routing'])
        self.category = cls.category
        return self

    def asdict(self, ignore:Optional[List[str]]=None) -> Dict[str, Any]:
        ignore = (ignore or []) + ['model_entity', 'start', 'finish', 'waypoints', 'id']
        storable_entity = cast(StorableElement, self.model_entity)
        details = StorableElement.asdict(self, ignore=ignore)
        details['relationship'] = storable_entity.Id
        details['source_repr_id'] = self.start.Id
        details['target_repr_id'] = self.finish.Id
        details['routing'] = json.dumps(self.waypoints, cls=ExtendibleJsonEncoder)
        return details

    @classmethod
    def get_collection(cls) -> Collection:
        return Collection.relation_repr

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.relationship

    def route(self, all_blocks):
        super().route(all_blocks)
        self.path.attrs['data-category'] = int(ReprCategory.relationship)
        self.path.attrs['data-rid'] = self.Id
        storable_entity = cast(StorableElement, self.model_entity)
        self.path.attrs['data-mid'] = storable_entity.Id

    def reroute(self, all_blocks):
        super().reroute(all_blocks)
        # Update the positions of the various texts according to their anchors.
        anchor_positions = {
            RelationAnchor.Start: self.terminations[0],
            RelationAnchor.Center: self.terminations[2],
            RelationAnchor.End: self.terminations[1]
        }
        for anchor, widget in self.text_widgets.items():
            widget.setPos(anchor_positions[anchor])
            widget.updateShape()

    def get_db_table(cls):
        return '_RelationshipRepresentation'

    @override                                           # From Stylable
    def getStyle(self, key, default=None):
        """ Allow model definitions to override styling """
        return getModeledStyle(self, key, default)

@dataclass
class Message(ModeledShape):
    message: int = None
    orientation: float = 0
    direction: shapes.MsgDirection = shapes.MsgDirection.source_2_target

    def isResizable(self) -> bool:
        return False

    @staticmethod
    def from_dict(data_store: DataStore, **details) -> ModeledShape:
        self = from_dict(Message, **details)
        self.category = ReprCategory.message
        return self

    def asdict(self, ignore:Optional[List[str]]=None) -> Dict[str, Any]:
        ignore = (ignore or []) + ['model_entity', 'id', 'width', 'height']
        storable_entity = cast(StorableElement, self.model_entity)
        details = StorableElement.asdict(self, ignore=ignore)
        details['message'] = storable_entity.Id
        return details

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.message

    @classmethod
    def get_collection(cls) -> Collection:
        return Collection.message_repr

    def get_db_table(cls):
        return '_MessageRepresentation'

    def getShapeDescriptor(self):
        return MsgShape

    def updateShape(self, shape=None):
        shape = shape or self.shape
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(shape.children[0], self)
        self.TextWidget.updateShape(shape.children[1], self)
