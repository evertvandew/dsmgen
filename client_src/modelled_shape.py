
from typing import Any, Self, List, Dict, Optional, Self
from dataclasses import dataclass, field, asdict
import json
from browser import svg, console
from browser.widgets.dialog import Dialog, InfoDialog
from diagrams import shapes, Shape, Relationship, CP, Point, Orientations, Diagram, getMousePos, DiagramConfiguration
from data_store import DataStore, StorableElement, Collection, ReprCategory, from_dict
from point import load_waypoints



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
    input_details: Dict[str, str]
    current_value: Any
    convertor: DataConvertor


class ModelEntity:
    """ An interface class describing the behaviour of an item represented in a diagram. """
    def get_text(self, index: int):
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

    def representation_cls(self) -> Shape | CP | Relationship:
        """ Create a shape representing this model item. """
        raise NotImplementedError()


###############################################################################
## Diagrams and shapes
class ModelledDiagram(Diagram):
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
        allowed_blocks = self.get_allowed_blocks(for_drop=True)
        if cls_name not in allowed_blocks:
            InfoDialog("Not allowed", f"A {cls_name} can not be used in this diagram.", ok="Got it")
            return

        block_cls = allowed_blocks[data['__classname__']]
        repr_cls = self.config.get_repr_for_drop(block_cls)
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
            old_values = asdict(widget)
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


@dataclass
class ShapeWithText(Shape, StorableElement):
    model_entity: ModelEntity = None
    diagram: int = 0
    parent: Optional[int] = None

    default_style = dict(blockcolor='#FFFBD6')
    TextWidget = shapes.Text('description')

    def asdict(self) -> Dict[str, Any]:
        details = StorableElement.asdict(self)
        details['block'] = self.model_entity.Id
        return details

    def getShape(self):
        # This shape consists of two parts: the text and the outline.
        shape_type = self.getShapeDescriptor()
        g = svg.g()
        g <= shape_type.getShape(self)
        g <= self.TextWidget.getShape(self)
        return g

    def updateShape(self, shape):
        shape_type = self.getShapeDescriptor()
        shape_type.updateShape(shape.children[0], self)
        self.TextWidget.updateShape(shape.children[1], self)

    @classmethod
    def getDefaultStyle(cls):
        style = {}
        shape_type = cls.getShapeDescriptor()
        style.update(shape_type.getDefaultStyle())
        style.update(cls.TextWidget.getDefaultStyle())
        style.update(cls.default_style.copy())
        return style

    def repr_category(cls) -> ReprCategory:
        return ReprCategory.block

    @classmethod
    def is_instance_of(cls) -> bool:
        return False

    @classmethod
    def getShapeDescriptor(cls) -> shapes.BasicShape:
        return shapes.BasicShape.getDescriptor('Note')

    @classmethod
    def get_collection(cls) -> Collection:
        return Collection.block_repr

@dataclass
class Port(CP, StorableElement):
    block: int = 0
    parent: Optional[int] = None
    diagram: int = 0
    model_entity: StorableElement = None

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

@dataclass
class ShapeWithTextAndPorts(ShapeWithText):
    ports: List[Port] = field(default_factory=list)
    children: [Self] = field(default_factory=list)

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
        g <= shape_type.getShape(self)
        # Add the text
        g <= self.TextWidget.getShape(self)
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
                g <= s
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

        # Update the ports
        sorted_ports = {orientation: sorted([p for p in self.ports if p.orientation == orientation], key=lambda x: x.order) \
                       for orientation in Orientations}

        # Delete any ports no longer used
        deleted = [s for s, p in self.port_shape_lookup.items() if p not in self.ports]
        for s in deleted:
            s.remove()
        shape_lookup = {p.id: s for s, p in self.port_shape_lookup.items()}

        for orientation in [Orientations.LEFT, Orientations.RIGHT, Orientations.BOTTOM, Orientations.TOP]:
            ports = sorted_ports[orientation]
            pos_func = self.getPointPosFunc(orientation, ports)
            for i, p in enumerate(ports):
                p.pos = pos_func(i)
                if p.id in shape_lookup:
                    p.updateShape(shape_lookup[p.id])
                else:
                    s = p.getShape()
                    shape <= s
                    self.port_shape_lookup[s] = p

    def getConnectionTarget(self, ev):
        # Determine if one of the ports was clicked on.
        port = self.port_shape_lookup.get(ev.target, None)
        if port is None:
            return self
        return port

    def isConnected(self, target):
        return (target == self) or target in self.ports

    @classmethod
    def getDefaultStyle(cls):
        defaults = super().getDefaultStyle()
        defaults.update(cls.default_style)
        return defaults

    @classmethod
    def is_instance_of(cls):
        return False

    def get_allowed_ports(self):
        return self.model_entity.get_allowed_ports()

@dataclass
class ModeledRelationship(Relationship, StorableElement):
    model_entity: Optional[ModelEntity] = None
    diagram: int = 0

    @staticmethod
    def from_dict(**details) -> Self:
        self = from_dict(ModeledRelationship, **details)
        self.start = details['source_repr_id']  # Needs to be replaced with the actual object later
        self.finish = details['target_repr_id']  # Needs to be replaced with the actual object later
        self.waypoints = load_waypoints(details['routing'])
        return self

    def asdict(self) -> Dict[str, Any]:
        details = StorableElement.asdict(self)
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
