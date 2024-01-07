"""
Model Definition tools

This file gives the tools to define modelling language. From definitions made with these tools,
graphical modelling environments can be generated.

Syntactically, Python type annotations are used to define the details of the model. Decorators are used
to define how different elements in the model are used in diagrams or in the underlying logical model.

"""

from datetime import datetime, time
from enum import IntEnum, auto
from typing import List, Any, Optional, Dict
from dataclasses import dataclass, field, is_dataclass, fields



class ExplorableElement: pass
class ConnectionElement: pass
class RepresentableElement: pass
class DiagramElement: pass
class PortElement: pass


class LaneDirection(IntEnum):
    Up    =auto(),
    Right =auto(),
    Down  =auto(),
    Left  =auto()


@dataclass
class TypeDefault:
    typename: str
    default: str

@dataclass
class TypeConversion:
    type_name: str
    sqlalchemy: TypeDefault
    server: TypeDefault
    client: TypeDefault

    def get_conversion(self, context):
        c = getattr(self, context)
        return c.typename
    def get_default(self, context):
        c = getattr(self, context)
        return c.typename

@dataclass
class ModelDefinition:
    model_elements: List[Any] = field(default_factory=list)
    initial_records: List[Any] = field(default_factory=list)
    type_conversions: Dict[str, TypeConversion] = field(default_factory=dict)

    @property
    def diagrams(self) -> List[Any]:
        return [e for e in self.model_elements if DiagramElement in e.categories]

    @property
    def hierarchy(self) -> List[Any]:
        return [e for e in self.model_elements if ExplorableElement in e.categories]

    @property
    def representables(self) -> List[Any]:
        return [e for e in self.model_elements if RepresentableElement in e.categories]

    @property
    def relationship(self) -> List[Any]:
        return [e for e in self.model_elements if ConnectionElement in e.categories]
    @property
    def blocks(self) -> List[Any]:
        return [e for e in self.model_elements
                if RepresentableElement in e.categories
                    and ConnectionElement not in e.categories
                    and PortElement not in e.categories]
    @property
    def port(self) -> List[Any]:
        return [e for e in self.model_elements if PortElement in e.categories]

    @property
    def all_model_items(self) -> List[Any]:
        # Some entities are both diagrams and entities. Make sure a list of unique items is returned.
        return self.model_elements

    def is_port(self, cls):
        return PortElement in cls.categories
    def is_relationship(self, cls):
        return ConnectionElement in cls.categories

    def get_conversions(self, cls: Any) -> Optional[TypeConversion]:
        name = cls if isinstance(cls, str) else (cls.__name__ if isinstance(cls, type) else type(cls).__name__)
        if not isinstance(name, str):
            raise False
        return self.type_conversions.get(name, None)

model_definition = ModelDefinition()

def add_type_conversion(cls, sqlalchemy: TypeDefault, server: TypeDefault, client: TypeDefault):
    """ Define how a custom type is represented in the various parts of the system:

    Arguments:
    cls -- The class that is used in the model specification
    sqlalchemy -- the SQLAlchemy type used to represent this data
    server -- how the type is represented in the dataclasses used by the server. Must be JSON serializable.
    client -- how the type is represented in the dataclasses used by the Brython client. Must be JSON serializable.
    """
    conversion = TypeConversion(cls.__name__, sqlalchemy, server, client)
    model_definition.type_conversions[cls.__name__] = conversion


styling_definition = {}


def split_styling(styling):
    """ Split the string used to define styling into a dictionary useful for lookup"""
    if not ':' in styling:
        return {}
    return {k:v for k, v in [l.split(':') for l in styling.split(';')]}

def Entity(styling=''):
    """ Definition of a thing rendered as a "shape": blocks, actors, objects, actions, etc, etc, etc """
    def decorate(cls):
        cls.categories = [ExplorableElement, RepresentableElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate

def CompoundEntity(*entities, styling=''):
    """ Definition of a thing rendered as a "shape": blocks, actors, objects, actions, etc, etc, etc,
        but that are also a diagram themselves. In the graphical editor, double-clicking this should
        open an editor for the inned diagram.
    """
    def decorate(cls):
        cls.entities = entities
        cls.categories = [ExplorableElement, RepresentableElement, DiagramElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate

def BlockInstance(styling=''):
    def decorate(cls):
        cls.categories = [ExplorableElement, RepresentableElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate


def Relationship(styling=''):
    """ Definition of a connection between entities. """
    def decorate(cls):
        cls.categories = [ConnectionElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate

def Port(styling=''):
    """ Some entities can have IO "ports", or connection points. """
    def decorate(cls):
        cls.categories = [ExplorableElement, RepresentableElement, PortElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate

def BlockDiagram(*entities, styling=''):
    """ Diagram where entities can be placed anywhere on the grid, and connected freely. """
    def decorate(cls):
        cls.entities = entities
        cls.categories = [ExplorableElement, DiagramElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate


def LanedDiagram(*entities, styling=''):
    """ A diagram with "lanes", e.g. an UML sequence diagram. """
    def decorate(cls):
        cls.entities = entities
        cls.categories = [ExplorableElement, DiagramElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls

    return decorate

def LogicalModel(styling=''):
    """ Part of the underlying logical model. The user can browse the data in the tool following these elements. """
    def decorate(cls):
        cls.categories = [ExplorableElement]
        cls = dataclass(cls)
        model_definition.model_elements.append(cls)
        styling_definition[cls.__name__] = split_styling(styling)
        return cls
    return decorate

def ModelRoot(styling=''):
    """ The root of the underlying logical model. From this element, the user can build
        a model using the tool.
    """
    # TODO: Remove this, the initial elements are a better solution.
    def decorate(cls):
        cls.categories = [ExplorableElement]
        cls = dataclass(cls)
        return cls
    return decorate


###############################################################################
## Bookkeeping helpers
model_version = "0.0"
def ModelVersion(v):
    global model_version
    model_version = v

def get_version():
    return model_version


###############################################################################
## Definitions of additional annotations that can be used in the model, esp. with attributes

class OptionalAnnotation: pass

class required(OptionalAnnotation): pass    # An instance must ALWAYS have this attribute set.
class optional(OptionalAnnotation): pass    # An instance does not need this attribute filled in
class detail(OptionalAnnotation): pass      # This attribute is a detail only shown in a detail editor.
class hidden(OptionalAnnotation): pass      # This attribute is not to be seen or edited by the user.

class selection:
    """ Define an attribute that must be set to one of several options. """
    def __init__(self, options):
        """ Options are set in a single string, separated by spaces. As in the IntEnum function. """
        self.options: List[str] = options.split()

class longstr: pass
add_type_conversion(longstr, TypeDefault('String', '""'), TypeDefault('str', '""'), TypeDefault('str', '""'))

class parameter_spec: pass
add_type_conversion(parameter_spec, TypeDefault('String', '""'), TypeDefault('dict', 'field(default_factory=dict)'), TypeDefault('dict', 'field(default_factory=dict)'))

@dataclass
class parameter_values:
    parameter_definition: str

add_type_conversion(parameter_values, TypeDefault('String', '""'), TypeDefault('dict', 'field(default_factory=dict)'), TypeDefault('dict', 'field(default_factory=dict)'))


class fmt_datetime(datetime):
    def __init__(self, fmt):
        self.fmt = fmt


class XRef:
    def __init__(self, remote_name:str, *types):
        self.remote_name = remote_name
        self.types = types

add_type_conversion(XRef, TypeDefault('Integer', 'None'), TypeDefault('int', 'None'), TypeDefault('int', 'None'))


def initial_state(records):
    model_definition.initial_records = records

def get_style(cls, key, default):
    return styling_definition.get(cls.__name__, {}).get(key, default)
