"""
Model Definition tools

This file gives the tools to define modelling language. From definitions made with these tools,
graphical modelling environments can be generated.

Syntactically, Python type annotations are used to define the details of the model. Decorators are used
to define how different elements in the model are used in diagrams or in the underlying logical model.

"""

from datetime import datetime, time
from enum import IntEnum, auto
from typing import List, Any
from dataclasses import dataclass, field


class LaneDirection(IntEnum):
    Up    =auto(),
    Right =auto(),
    Down  =auto(),
    Left  =auto()


@dataclass
class ModelDefinition:
    entity: List[Any] = field(default_factory=list)
    relationship: List[Any] = field(default_factory=list)
    port: List[Any] = field(default_factory=list)
    block_diagram: List[Any] = field(default_factory=list)
    laned_diagram: List[Any] = field(default_factory=list)
    logical_model: List[Any] = field(default_factory=list)
    initial_records: List[Any] = None
    model_root: Any = None

    @property
    def diagrams(self) -> List[Any]:
        return self.block_diagram + self.laned_diagram

    @property
    def models(self) -> List[Any]:
        return self.logical_model + [self.model_root]

    @property
    def all_model_items(self) -> List[Any]:
        return self.diagrams + self.models + self.entity + self.relationship + self.port

model_definition = ModelDefinition()

styling_definition = {}


def Entity(styling=''):
    """ Definition of a thing rendered as a "shape": blocks, actors, objects, actions, etc, etc, etc """
    def decorate(cls):
        cls = dataclass(cls)
        model_definition.entity.append(cls)
        styling_definition[cls] = styling
        return cls
    return decorate

def Relationship(styling=''):
    """ Definition of a connection between entities. """
    def decorate(cls):
        cls = dataclass(cls)
        model_definition.relationship.append(cls)
        styling_definition[cls] = styling
        return cls
    return decorate

def Port(styling=''):
    """ Some entities can have IO "ports", or connection points. """
    def decorate(cls):
        cls = dataclass(cls)
        model_definition.port.append(cls)
        styling_definition[cls] = styling
        return cls
    return decorate

def BlockDiagram(cls):
    """ Diagram where entities can be placed anywhere on the grid, and connected freely. """
    cls = dataclass(cls)
    model_definition.block_diagram.append(cls)
    return cls


def LanedDiagram(lane_direction: LaneDirection):
    """ A diagram with "lanes", e.g. an UML sequence diagram. """
    def decorate(cls):
        cls = dataclass(cls)
        model_definition.laned_diagram.append(cls)
        return cls

    return decorate

def LogicalModel(cls):
    """ Part of the underlying logical model. The user can browse the data in the tool following these elements. """
    cls = dataclass(cls)
    model_definition.logical_model.append(cls)
    return cls


def ModelRoot(cls):
    """ The root of the underlying logical model. From this element, the user can build
        a model using the tool.
    """
    cls = dataclass(cls)
    assert model_definition.model_root is None
    model_definition.model_root = cls
    return cls


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

class selection:
    """ Define an attribute that must be set to one of several options. """
    def __init__(self, options):
        """ Options are set in a single string, separated by spaces. As in the IntEnum function. """
        self.options: List[str] = options.split()

class longstr(str): pass

class fmt_datetime(datetime):
    def __init__(self, fmt):
        self.fmt = fmt


class XRef:
    def __init__(self, remote_name:str, *types):
        self.remote_name = remote_name
        self.types = types


def initial_state(records):
    model_definition.initial_records = records
