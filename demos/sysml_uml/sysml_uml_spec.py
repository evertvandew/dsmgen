
from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              detail, longstr, XRef, hidden, selection)

# The tooling expects an ModelDifinition object named `md`
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
## Entities for structural diagrams
@md.LogicalModel
class ProtocolDefinition:
    description: longstr
    definition: longstr


@md.CompoundEntity(parents=[StructuralModel, FunctionalModel], elements=[Note, Self], styling = "shape:rect;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
@md.Entity(styling='shape:folder', parents=[Self, StructuralModel])
class Package:
    name: str

@md.Entity(styling="shape:rect", parents=[Self, StructuralModel])
class Class:
    name: str
    description: (longstr, detail)

@md.BlockInstance(parents=[Any], definitions=[Class])
class ObjectInstance:
    name: str
    
@md.Entity(styling = "shape:rect;structure:Block;icon:square-full", parents=[Self, StructuralModel])
class Block:
    name: str
    description: (longstr, detail)

@md.Entity(styling="shape:stickman")
class Actor:
    name: str
    description: longstr

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

@md.Relationship(styling="endmarker:hat;pattern:dashed")
class Dependency:
    stereotype: str
    source: XRef('associations', Block, Actor, hidden)
    target: XRef('associations', Block, Actor, hidden)
    

@md.Relationship(styling = "endmarker:funccall(end)")
class BlockReference:
    stereotype: selection("None Association Aggregation Composition")
    source: XRef('associations', Block, hidden)
    target: XRef('associations', Block, hidden)
    source_multiplicity: selection("0-1 1 + *")
    target_multiplicity: selection("0-1 1 + *")

    def end(self):
        return {
            'None': 'none',
            'Association': 'closedarrow',
            'Aggregation': 'opendiamond',
            'Composition': 'closeddiamond'
        }[self.stereotype]

@md.Relationship(styling = "endmarker:opentriangle")
class BlockGeneralization:
    source: XRef('parent', Block, hidden)
    target: XRef('children', Block, hidden)

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

@md.Relationship(styling = "")
class LifeLine:
    source: XRef('a', Actor, ObjectInstance, hidden)
    target: XRef('b', Actor, ObjectInstance, hidden)
    name: str

@md.BlockDiagram(Block, Actor, Note, Constraint, styling='icon:image', parents=[Block, StructuralModel])
class BlockDefinitionDiagram:
    name: str

@md.BlockDiagram(ObjectInstance, Actor, Note, Constraint, styling='icon:image', parents=[Block, FunctionalModel])
class CommunicationDiagram:
    name: str

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
@md.Entity(styling="shape:ellipse", parents=[FunctionalModel])
class UseCase:
    name: str
    description: longstr

@md.Relationship(styling = "endmarker:opentriangle;pattern:dashed")
class Extends:
    source: XRef('extended', UseCase, hidden)
    target: XRef('extending', UseCase, hidden)
    name: str

@md.Relationship()
class Includes:
    source: XRef('including', UseCase, hidden)
    target: XRef('addition', UseCase, hidden)
    name: str

@md.Relationship(styling='endmarker:hat;pattern:dashed')
class InheritUseCase:
    source: XRef('child', UseCase, hidden)
    target: XRef('parent', UseCase, hidden)
    name: str

@md.Relationship(styling='endmarker:hat')
class Association:
    source: XRef('actor', Actor, Class, Package, hidden)
    target: XRef('usecase', UseCase, hidden)
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

@md.Relationship(styling='endmarker:arrow')
class Transition:
    source: XRef('from', State, StartState, hidden)
    target: XRef('to', State, EndState, hidden)
    name: str

@md.BlockDiagram(State, Note, Constraint, styling='icon:image', parents=[FunctionalModel, Class, Block, Self, UseCase, Package])
class UseCaseDiagram:
    name: str

###############################################################################
##

md.initial_state([
    FunctionalModel('Functional Model', '', None),
    StructuralModel('Structural Model', '', None)
])
