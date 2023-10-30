"""
Model Definition tools

This file gives the tools to define modelling language. From definitions made with these tools,
graphical modelling environments can be generated.

Syntactically, Python type annotations are used to define the details of the model. Decorators are used
to define how different elements in the model are used in diagrams or in the underlying logical model.

"""


from typing import List
from enum import IntEnum, auto


class LaneDirection(IntEnum):
    Up    =auto(),
    Right =auto(),
    Down  =auto(),
    Left  =auto()


model_definition = {
    'ModelRoot': None
    # All other entities in the model definition are added dynamically by the decorators.
}

styling_definition = {}


def Entity(styling=''):
    """ Definition of a thing rendered as a "shape": blocks, actors, objects, actions, etc, etc, etc """
    def decorate(cls):
        model_definition['Entity'].append(cls)
        styling_definition[cls] = styling

def Relationship(styling=''):
    """ Definition of a connection between entities. """
    def decorate(cls):
        model_definition['Relationship'].append(cls)
        styling_definition[cls] = styling

def Port(styling=''):
    """ Some entities can have IO "ports", or connection points. """
    def decorate(cls):
        model_definition['Port'].append(cls)
        styling_definition[cls] = styling

def BlockDiagram():
    """ Diagram where entities can be placed anywhere on the grid, and connected freely. """
    def decorate(cls):
        model_definition['BlockDiagram'].append(cls)

def LanedDiagram(lane_direction: LaneDirection):
    """ A diagram with "lanes", e.g. an UML sequence diagram. """
    def decorate(cls):
        model_definition['LanedDiagram'].append(cls)

def LogicalModel():
    """ Part of the underlying logical model. The user can browse the data in the tool following these elements. """
    def decorate(cls):
        model_definition['LogicalModel'].append(cls)

def ModelRoot():
    """ The root of the underlying logical model. From this element, the user can build
        a model using the tool.
    """
    def decorate(cls):
        assert model_definition['ModelRoot'] is None
        model_definition['ModelRoot'] = cls


###############################################################################
## Definitions of additional annotations that can be used in the model, esp. with attributes

class required: pass    # An instance must ALWAYS have this attribute set.
class optional: pass    # An instance does not need this attribute filled in
class detail: pass      # This attribute is a detail only shown in a detail editor.

class selection:
    """ Define an attribute that must be set to one of several options. """
    def __init__(self, options):
        """ Options are set in a single string, separated by spaces. As in the IntEnum function. """
        self.options: List[str] = options.split()
