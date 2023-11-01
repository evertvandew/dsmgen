
from typing import Self, List, Dict
from model_definition import (Entity, Relationship, Port, BlockDiagram, LogicalModel, ModelRoot, required,
                              optional, selection, detail)

###############################################################################
## Logical model
@ModelRoot
class RootModel:
    pass

@LogicalModel
class FunctionalModel:
    parent: (Self, RootModel)

@LogicalModel
class StructuralModel:
    parent: (Self, RootModel)

###############################################################################
## Entities for Notes & Constraints
@Entity(styling = "shape:note")
class Note:
    description: (str, required)

@Entity(styling = "shape:note")
class Constraint:
    description: (str, required)

@Relationship(styling = "end:hat")
class Anchor:
    source: (Note, Constraint)
    target: Entity
    name: str

###############################################################################
## Entities for structural diagrams
@Port(styling = "shape:square;fill:green")
class FullPort:
    name: str
    provides: [Entity, str]
    requires: [Entity, str]

@Port(styling = "shape:square;fill:blue")
class FlowPort:
    name: str
    inputs: [Entity, str]
    outputs: [Entity, str]

@Entity(styling = "shape:rect")
class Block:
    parent: (Self, StructuralModel)
    name: str
    description: (str, detail)
    ports: [FullPort, FlowPort]

@Relationship(styling = "end:funccall(end)")
class BlockReference:
    stereotype: selection("None Association Aggregation Composition")
    source: Block
    target: Block
    source_multiplicity: selection("0-1 1 + *")
    target_multiplicity: selection("0-1 1 + *")
    association: Block

    def end(self):
        return {
            'None': 'none',
            'Association': 'closedarrow',
            'Aggregation': 'opendiamond',
            'Composition': 'closeddiamond'
        }[self.stereotype]

@Relationship()
class BlockGeneralization:
    source: Block
    target: Block

    styling = "end:opentriangle"

@Relationship()
class FullPortConnection:
    source: FullPort
    target: FullPort
    name: str

    styling = "end:hat"

@Relationship()
class FlowPortConnection:
    source: FlowPort
    target: FlowPort
    name: str

    styling = "end:hat"

@BlockDiagram
class BlockDefinitionDiagram:
    entities: [Block, Note, Constraint]
    parent: (Block, StructuralModel)


###############################################################################
## Entities for requirements
@Entity()
class Requirement:
    parent: (Self, FunctionalModel)
    name: str
    description: (str, detail)
    priority: (selection("NotApplicable Must Should Could Would"), detail)
    category: (str, detail)
