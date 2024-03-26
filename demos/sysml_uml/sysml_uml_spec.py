
from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              detail, longstr, XRef, hidden, selection)

# The tooling expects an ModelDifinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')

""" TODO: 
* Use Case diagram
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

@md.LogicalModel(styling='icon:folder')
class FunctionalModel:
    name: str
    description: longstr
    parent: XRef('children', Self, RootModel, hidden)

@md.LogicalModel(styling='icon:folder')
class StructuralModel:
    name: str
    description: longstr
    parent: XRef('children', Self, RootModel, hidden)

###############################################################################
## Entities for Notes & Constraints, which are used in all other diagrams
@md.Entity(styling = "shape:note;structure:Note;icon:message")
class Note:
    description: (longstr, required)
    parent: XRef('children', Any, hidden)

@md.Entity(styling = "shape:note;structure:Note;icon:note-sticky")
class Constraint:
    description: (longstr, required)
    parent: XRef('children', Any, hidden)

@md.Relationship(styling = "end:hat")
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


@md.Entity(styling='shape:folder')
class Package:
    parent: XRef('children', Self, StructuralModel, hidden)
    name: str

@md.Entity(styling="shape:rect")
class Class:
    parent: XRef('children', Self, StructuralModel, hidden)
    name: str
    description: (longstr, detail)

@md.BlockInstance(parents=[Any], definitions=[Class])
class ObjectInstance:
    parent: XRef('children', Class, StructuralModel, hidden)
    name: str
    
@md.Entity(styling = "shape:rect;structure:Block;icon:square-full")
class Block:
    parent: XRef('children', Self, StructuralModel, hidden)
    name: str
    description: (longstr, detail)

@md.Entity(styling="shape:stickman")
class Actor:
    name: str
    description: longstr

@md.Port(styling = "shape:square;fill:green;icon:arrows-alt-h")
class FullPort:
    name: str
    parent: XRef('ports', Block, hidden)
    provides: XRef('producers', ProtocolDefinition, hidden)
    requires: XRef('consumers', ProtocolDefinition, hidden)

@md.Port(styling = "shape:square;fill:blue;icon:arrows-alt-h")
class FlowPort:
    name: str
    parent: XRef('ports', Block, hidden)
    inputs: XRef('consumers', ProtocolDefinition, hidden)
    outputs: XRef('producers', ProtocolDefinition, hidden)

@md.Relationship(styling="end:hat;pattern:dashed")
class Dependency:
    stereotype: str
    source: XRef('associations', Block, Actor, hidden)
    target: XRef('associations', Block, Actor, hidden)
    

@md.Relationship(styling = "end:funccall(end)")
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

@md.Relationship(styling = "end:opentriangle")
class BlockGeneralization:
    source: XRef('parent', Block, hidden)
    target: XRef('children', Block, hidden)

@md.Relationship(styling = "end:hat")
class FullPortConnection:
    source: XRef('consumers', FullPort, hidden)
    target: XRef('producers', FullPort, hidden)
    name: str

@md.Relationship(styling = "end:hat")
class FlowPortConnection:
    source: XRef('consumers', FlowPort, hidden)
    target: XRef('producers', FlowPort, hidden)
    name: str

@md.Relationship(styling = "")
class LifeLine:
    source: XRef('a', Actor, ObjectInstance, hidden)
    target: XRef('b', Actor, ObjectInstance, hidden)
    name: str

@md.BlockDiagram(Block, Actor, Note, Constraint, styling='icon:image')
class BlockDefinitionDiagram:
    parent: XRef('children', Block, StructuralModel, hidden)
    name: str

@md.BlockDiagram(ObjectInstance, Actor, Note, Constraint, styling='icon:image')
class CommunicationDiagram:
    parent: XRef('children', Block, FunctionalModel, hidden)
    name: str

###############################################################################
## Entities for requirements
@md.Entity(styling = "shape:ellipse;structure:Block;icon:file-lines")
class Requirement:
    parent: XRef('children', Self, FunctionalModel, hidden)
    name: str
    description: (longstr, detail)
    priority: (selection("NotApplicable Must Should Could Would"), detail)
    category: (str, detail)


###############################################################################
## Use Case diagram
@md.Entity(styling="shape:ellipse")
class UseCase:
    name: str
    description: longstr

@md.Relationship(styling = "end:opentriangle;pattern:dashed")
class Extends:
    source: XRef('extended', UseCase, hidden)
    target: XRef('extending', UseCase, hidden)
    name: str

@md.Relationship()
class Includes:
    source: XRef('including', UseCase, hidden)
    target: XRef('addition', UseCase, hidden)
    name: str

@md.Relationship(styling='end:hat;pattern:dashed')
class InheritUseCase:
    source: XRef('child', UseCase, hidden)
    target: XRef('parent', UseCase, hidden)
    name: str

@md.Relationship(styling='end:hat')
class Association:
    source: XRef('actor', Actor, Class, Package, hidden)
    target: XRef('usecase', UseCase, hidden)
    name: str

###############################################################################
## State diagram
@md.Entity(styling="shape:ellipse")
class State:
    name: str
    description: longstr

@md.Entity(styling="shape:ringedclosedcircle")
class EndState:
    name: str
    description: longstr

@md.Entity(styling="shape:closedcircle")
class StartState:
    name: str
    description: longstr

@md.Relationship(styling='end:arrow')
class Transition:
    source: XRef('from', State, StartState, hidden)
    target: XRef('to', State, EndState, hidden)
    name: str

@md.BlockDiagram(State, Note, Constraint, styling='icon:image')
class UseCaseDiagram:
    parent: XRef('children', FunctionalModel, UseCase, Class, Block, State, Package)
    name: str

###############################################################################
##

md.initial_state([
    FunctionalModel('Functional Model', '', None),
    StructuralModel('Structural Model', '', None)
])
