
from typing import Any, Self, List, Dict, Optional, Type
from dataclasses import dataclass, field
import json
from browser import svg, console
from diagrams import shapes, Shape, Relationship, CP, Point, Orientations
from data_store import StorableElement, Collection, ReprCategory, from_dict, ExtendibleJsonEncoder, DataStore
from point import load_waypoints
from enum import IntEnum, auto



class DataConvertor:
    """ A dataconvertor converts strings to a specific type, and vice-versa.
        The interface corresponds to the built-in API of most built-in types.
    """
    def __init__(self, str):
        raise RuntimeError()
    def __str__(self) -> str:
        raise RuntimeError()

@dataclass
class EditableParameterDetails:
    """ Description for a parameter that can be edited for an element in a model item. """
    name: str
    type: type   # Key: value pairs used by the property_editor to create input fields.
    current_value: Any
    convertor: DataConvertor


class ModelEntity:
    """ An interface class describing the behaviour of an item represented in a diagram. """
    def get_text(self, index: int) -> str:
        """ Retrieve a specific string associated with the item that is needed in the diagram. """
        return self.name
    def get_nr_texts(self) -> int:
        """ Ask how many texts this item wants to display """
        return 1

    def get_editable_parameters(self) -> List[EditableParameterDetails]:
        return []
    @classmethod
    def supports_ports(cls) -> bool:
        return False

    @classmethod
    def get_representation_cls(cls, context: ReprCategory) -> Optional[Self]:
        """ Create a shape representing this model item.
            context: how this entity is represented: as a block, as a port, as a relation, etc.
        """
        return None

    @classmethod
    def get_allowed_ports(cls) -> List[Self]:
        """ Determine which ports are allowed to be attached to a model entity """
        return []

    def get_instance_parameters(self) -> List[EditableParameterDetails]:
        return []

    def update(self, data: Dict[str, Any]):
        for k, v in data.items():
            setattr(self, k, v)

    @classmethod
    def getDefaultStyle(cls):
        shape_name = cls.default_styling.get('shape', 'rect')
        shape_type = shapes.BasicShape.getDescriptor(shape_name)
        style = cls.default_styling.copy()
        style.update(shape_type.getDefaultStyle())
        return style


###############################################################################
@dataclass
class ModelRepresentation(StorableElement):
    model_entity: ModelEntity = None
    diagram: int = 0                    # Diagram in which this representation is displayed.

    @classmethod
    def repr_category(cls) -> ReprCategory:
        raise NotImplementedError()

    def getShape(self):
        raise NotImplementedError()


@dataclass
class ModeledShape(Shape, ModelRepresentation):
    parent: Optional[int] = None        # For hierarchical shapes (inner block & ports): the owner of this repr.

    default_style = dict(blockcolor='#FFFBD6')
    TextWidget = shapes.Text('text')

    @property
    def text(self):
        return self.model_entity.get_text(0)

    def asdict(self) -> Dict[str, Any]:
        details = StorableElement.asdict(self, ignore=['model_entity', 'ports'])
        details['block'] = self.model_entity.Id
        if 'children' in details:
            del details['children']
        return details

    def getShape(self):
        # This shape consists of two parts: the text and the outline.
        shape_type = self.getShapeDescriptor()
        g = svg.g()
        _ = g <= shape_type.getShape(self)
        _ = g <= self.TextWidget.getShape(self)
        return g

    def updateShape(self, shape):
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(shape.children[0], self)
        self.TextWidget.updateShape(shape.children[1], self)

    def getDefaultStyle(self):
        style = {}
        style.update(self.model_entity.getDefaultStyle())
        style.update(self.TextWidget.getDefaultStyle())
        style.update(self.default_style.copy())
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

@dataclass
class Port(CP, ModelRepresentation):
    # These two items have slightly illogical names. That is because they are stored in the database in
    # the same table as regular blocks, so that connections can be made to them.
    block: int = 0                  # The ID of the model_entity for this port.
    parent: Optional[int] = None    # The block this port belongs to.

    def getShape(self):
        p = self.pos
        shape = svg.rect(x=p.x-5, y=p.y-5, width=10, height=10, stroke_width=1, stroke='black', fill='lightgreen')
        shape.attrs['data-class'] = type(self).__name__
        return shape
    def updateShape(self, shape):
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

    def asdict(self) -> Dict[str, Any]:
        details = StorableElement.asdict(self, ignore=['model_entity', 'id'])
        return details


@dataclass
class ModeledShapeAndPorts(ModeledShape):
    ports: List[Port] = field(default_factory=list)
    children: [Self] = field(default_factory=list)

    def asdict(self) -> Dict[str, Any]:
        details = super().asdict()
        return details

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
        console.log(f'Getting shape for {shape_type} {self}')
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

        # Return the group of objects
        return g

    def updateShape(self, shape):
        # Update the rect
        rect = shape.children[0]
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(rect, self)
        text = shape.children[1]
        self.TextWidget.updateShape(text, self)
        print('SHAPE:', shape)

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

    @staticmethod
    def from_dict(data_store: DataStore, **details) -> Self:
        self = from_dict(ModeledRelationship, **details)
        self.start = data_store.get(Collection.block_repr, details['source_repr_id'])
        self.finish = data_store.get(Collection.block_repr, details['target_repr_id'])
        self.waypoints = load_waypoints(details['routing'])
        return self

    def asdict(self) -> Dict[str, Any]:
        details = StorableElement.asdict(self, ignore=['model_entity', 'start', 'finish', 'waypoints', 'id'])
        details['relationship'] = self.model_entity.Id
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
