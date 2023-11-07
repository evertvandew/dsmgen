
from typing import Self, List, Dict
from model_definition import (Entity, Relationship, Port, BlockDiagram, LogicalModel, ModelRoot, required,
                              optional, selection, detail, longstr, XRef, ModelVersion, initial_state,
                              hidden, style)

ModelVersion('0.1')


###############################################################################
## Logical model
@ModelRoot
class RootModel:
    pass

@LogicalModel
class FunctionalModel:
    name: str
    description: longstr
    parent: XRef('children', Self, RootModel, hidden)

@LogicalModel
class StructuralModel:
    name: str
    description: longstr
    parent: XRef('children', Self, RootModel, hidden)

###############################################################################
## Entities for Notes & Constraints
@Entity(styling = "shape:note")
class Note:
    description: (longstr, required)

@Entity(styling = "shape:note")
class Constraint:
    description: (longstr, required)

@Relationship(styling = "end:hat")
class Anchor:
    source: XRef('owner', Note, Constraint, hidden)
    target: XRef('notes', Entity, hidden)
    name: str

###############################################################################
## Entities for structural diagrams
@LogicalModel
class ProtocolDefinition:
    description: longstr
    definition: longstr

@Entity(styling = "shape:rect")
class Block:
    parent: XRef('children', Self, StructuralModel, hidden)
    name: str
    description: (longstr, detail)

@Port(styling = "shape:square;fill:green")
class FullPort:
    name: str
    parent: XRef('ports', Block, hidden)
    provides: XRef('producers', ProtocolDefinition, optional)
    requires: XRef('consumers', ProtocolDefinition, optional)

@Port(styling = "shape:square;fill:blue")
class FlowPort:
    name: str
    parent: XRef('ports', Block, hidden)
    inputs: XRef('consumers', ProtocolDefinition, optional)
    outputs: XRef('producers', ProtocolDefinition, optional)

@Relationship(styling = "end:funccall(end)")
class BlockReference:
    stereotype: selection("None Association Aggregation Composition")
    source: XRef('associations', Block, hidden)
    target: XRef('associations', Block, hidden)
    source_multiplicity: selection("0-1 1 + *")
    target_multiplicity: selection("0-1 1 + *")
    association: XRef('associations', Block, hidden)

    def end(self):
        return {
            'None': 'none',
            'Association': 'closedarrow',
            'Aggregation': 'opendiamond',
            'Composition': 'closeddiamond'
        }[self.stereotype]

@Relationship()
class BlockGeneralization:
    source: XRef('parent', Block, hidden)
    target: XRef('children', Block, hidden)

    styling = "end:opentriangle"

@Relationship()
class FullPortConnection:
    source: XRef('consumers', FullPort, hidden)
    target: XRef('producers', FullPort, hidden)
    name: str

    styling = "end:hat"

@Relationship()
class FlowPortConnection:
    source: XRef('consumers', FlowPort, hidden)
    target: XRef('producers', FlowPort, hidden)
    name: str

    styling = "end:hat"

@BlockDiagram
class BlockDefinitionDiagram:
    entities: [Block, Note, Constraint]
    parent: XRef('children', Block, StructuralModel, hidden)
    name: str


###############################################################################
## Entities for requirements
@Entity()
class Requirement:
    parent: XRef('children', Self, FunctionalModel, hidden)
    name: str
    description: (longstr, detail)
    priority: (selection("NotApplicable Must Should Could Would"), detail)
    category: (str, detail)


initial_state([
    FunctionalModel('Functional Model', '', None),
    StructuralModel('Structural Model', '', None)
])


style(Note, icon='message')
style(Constraint, icon='note-sticky')
style(Requirement, icon='file-lines')
style(Block, icon='square-full')
style(BlockDefinitionDiagram, icon='image')
style(FlowPort, icon='arrows-alt-h')
style(FullPort, icon='arrows-alt-h')
style(FunctionalModel, icon='folder')
style(StructuralModel, icon='folder')
