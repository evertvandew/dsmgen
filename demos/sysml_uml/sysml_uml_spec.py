
from typing import Self, Any, Optional
from model_definition import (ModelDefinition, required,
                              detail, longstr, XRef, hidden, selection)

# The tooling expects an ModelDefinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')

""" TODO: 
* Sequence diagram
* Collaboration diagram
* Requirement diagram
* Allocation diagram
"""



###############################################################################
## Logical model
@md.ModelRoot(styling='icon:folder')
class RootModel:
    pass

@md.LogicalModel(styling='icon:folder', parents=[Self, RootModel])
class FunctionalModel:
    name: str
    description: longstr

@md.LogicalModel(styling='icon:folder', parents=[Self, RootModel])
class StructuralModel:
    name: str
    description: longstr

###############################################################################
## Entities for Notes & Constraints, which are used in all other diagrams
@md.Entity(styling = "shape:note;structure:Note;icon:message", parents=[Any])
class Note:
    description: (longstr, required)

@md.Entity(styling = "shape:note;structure:Note;icon:note-sticky", parents=[Any])
class Constraint:
    description: (longstr, required)

@md.Relationship(styling = "endmarker:hat")
class Anchor:
    source: XRef('owner', Note, Constraint, hidden)
    target: XRef('notes', Any, hidden)
    name: str

###############################################################################
## Basic entities

@md.LogicalModel
class ProtocolDefinition:
    description: longstr
    definition: longstr


@md.CompoundEntity(parents=[Self, StructuralModel, FunctionalModel], elements=[Note, Self],
                   styling="shape:rect;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class Package:
    name: str


@md.Entity(styling="shape:rect", parents=[Self, StructuralModel])
class Class:
    name: str
    description: (longstr, detail)


@md.BlockInstance(parents=[Any], definitions=[Class])
class ObjectInstance:
    name: str


@md.Entity(styling="shape:rect;structure:Block;icon:square-full", parents=[Self, StructuralModel])
class Block:
    name: str
    description: (longstr, detail)


@md.Entity(styling="shape:stickman")
class Actor:
    name: str
    description: longstr


###############################################################################
## Entities for requirements
@md.Entity(styling = "shape:ellipse;structure:Block;icon:file-lines", parents=[Self, FunctionalModel])
class Requirement:
    name: str
    description: (longstr, detail)
    priority: (selection("NotApplicable Must Should Could Would"), detail)
    category: (str, detail)


###############################################################################
## Use Case diagram
@md.Entity(styling="shape:ellipse;", parents=[FunctionalModel])
class UseCase:
    name: str
    description: longstr

@md.Relationship(styling = "endmarker:triangleopen;pattern:dashed;routing_method:center2center")
class Extends:
    source: XRef('extended', UseCase, hidden)
    target: XRef('extending', UseCase, hidden)
    name: str

@md.Relationship(styling="routing_method:center2center")
class Includes:
    source: XRef('including', UseCase, hidden)
    target: XRef('addition', UseCase, hidden)
    name: str

@md.Relationship(styling='endmarker:hat;pattern:dashed;routing_method:center2center')
class InheritUseCase:
    source: XRef('child', UseCase, hidden)
    target: XRef('parent', UseCase, hidden)
    name: str

@md.Relationship(styling='endmarker:hat;routing_method:center2center')
class Association:
    source: XRef('actor', Actor, Class, Package, hidden)
    target: XRef('usecase', UseCase, hidden)
    name: str

@md.BlockDiagram(Actor, UseCase, Note, styling='icon:image', parents=[FunctionalModel, Package])
class UseCaseDiagram:
    name: str


###############################################################################
## State diagram
@md.Entity(styling="shape:ellipse", parents=[Class, Self, Block, UseCase])
class State:
    name: str
    description: longstr

@md.Entity(styling="shape:ringedclosedcircle", parents=[Class, Block, Self, UseCase])
class EndState:
    name: str
    description: longstr

@md.Entity(styling="shape:closedcircle", parents=[Class, Block, Self, UseCase])
class StartState:
    name: str
    description: longstr

@md.Relationship(styling='endmarker:arrow;routing_method:center2center')
class Transition:
    source: XRef('from', State, StartState, hidden)
    target: XRef('to', State, EndState, hidden)
    name: str

@md.BlockDiagram(State, StartState, EndState, Note, Constraint, styling='icon:image', parents=[FunctionalModel, Class, Block, Self, UseCase, Package])
class StateDiagram:
    name: str


###############################################################################
## Entities for structural diagrams

@md.Port(styling = "shape:square;fill:green;icon:arrows-alt-h", parents=[Block])
class FullPort:
    name: str
    provides: XRef('producers', ProtocolDefinition, hidden)
    requires: XRef('consumers', ProtocolDefinition, hidden)

@md.Port(styling = "shape:square;fill:blue;icon:arrows-alt-h", parents=[Block])
class FlowPort:
    name: str
    inputs: XRef('consumers', ProtocolDefinition, hidden)
    outputs: XRef('producers', ProtocolDefinition, hidden)

@md.Relationship(styling='endmarker:hat')
class Dependency:
    stereotype: selection("None Association Aggregation Composition")
    source: XRef('associations', Class, Block, hidden)
    target: XRef('associations', Class, Block, hidden)
    source_multiplicity: selection("0-1 1 + *")
    target_multiplicity: selection("0-1 1 + *")

    def getStyle(self, key, default) -> Optional[str]:
        if key == 'startmarker':
            return {
                1: 'none', 2: 'arrow', 3: 'diamondopen', 4: 'diamond'
            }.get(self.stereotype, 'none')


@md.Relationship(styling = "endmarker:triangleopen;routing_method:center2center")
class ClassGeneralization:
    source: XRef('parent', Class, Block, hidden)
    target: XRef('children', Class, Block, hidden)

@md.Relationship(styling = "endmarker:hat")
class FullPortConnection:
    source: XRef('consumers', FullPort, hidden)
    target: XRef('producers', FullPort, hidden)
    name: str

@md.Relationship(styling = "endmarker:hat")
class FlowPortConnection:
    source: XRef('consumers', FlowPort, hidden)
    target: XRef('producers', FlowPort, hidden)
    name: str

@md.BlockDiagram(Block, Actor, Note, Constraint, styling='icon:image', parents=[Block, StructuralModel])
class BlockDefinitionDiagram:
    name: str

@md.BlockDiagram(Class, Actor, Note, Constraint, styling='icon:image', parents=[Block, Class, StructuralModel])
class ClassDiagram:
    name: str

###############################################################################
## Behavioural Diagrams
@md.Relationship(styling="endmarker:none", source=[Actor, ObjectInstance, Block], target=[Actor, ObjectInstance, Block])
class CommunicationLink: pass


@md.BlockDiagram(ObjectInstance, Actor, Note, Constraint, styling='icon:image', parents=[Block, Class, FunctionalModel, ClassDiagram])
class CommunicationDiagram:
    name: str

@md.Message(targets=[CommunicationLink, ObjectInstance], parents=[Class, Block, CommunicationDiagram])
class ClassMessage:
    name: str
    kind: selection('function event message create destroy')
    arguments: str
    description: longstr

@md.Relationship(styling = "")
class LifeLine:
    source: XRef('a', Actor, ObjectInstance, hidden)
    target: XRef('b', Actor, ObjectInstance, hidden)
    name: str

@md.Relationship(styling='')
class SequencedMessage:
    source: XRef('a', Actor, ObjectInstance, hidden)
    target: XRef('b', Actor, ObjectInstance, hidden)
    name: str
    kind: selection('function event message return create destroy')


@md.LanedDiagram(ObjectInstance, Actor, Note, Constraint, vertical_lane=[ObjectInstance, Actor],
                 interconnect=SequencedMessage, self_message=True, parents=[FunctionalModel, ClassDiagram, UseCaseDiagram])
class SequenceDiagram:
    name: str


###############################################################################
##

md.initial_state([
    FunctionalModel('Functional Model', '', None),
    StructuralModel('Structural Model', '', None)
])
