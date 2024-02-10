
from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              optional, selection, detail, longstr, XRef,
                              hidden, parameter_spec)

# The tooling expects an ModelDifinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')


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
## Entities for Notes & Constraints
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

@md.Entity(styling = "shape:rect;structure:Block;icon:square-full")
class Block:
    parent: XRef('children', Self, StructuralModel, hidden)
    name: str
    description: (longstr, detail)

@md.CompoundEntity(parents=[StructuralModel], elements=[Note, "Block"], styling = "shape:rect;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class SubProgramDefinition:
    name: str
    description: (longstr, detail)
    parameters: (parameter_spec, detail)

@md.Port(styling = "shape:square;fill:green;icon:arrows-alt-h")
class FullPort:
    name: str
    parent: XRef('ports', Block, SubProgramDefinition, hidden)
    provides: XRef('producers', ProtocolDefinition, optional)
    requires: XRef('consumers', ProtocolDefinition, optional)

@md.Port(styling = "shape:square;fill:blue;icon:arrows-alt-h")
class FlowPort:
    name: str
    parent: XRef('ports', Block, SubProgramDefinition, hidden)
    inputs: XRef('consumers', ProtocolDefinition, optional)
    outputs: XRef('producers', ProtocolDefinition, optional)

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

@md.Relationship()
class BlockGeneralization:
    source: XRef('parent', Block, hidden)
    target: XRef('children', Block, hidden)

    styling = "end:opentriangle"

@md.Relationship()
class FullPortConnection:
    source: XRef('consumers', FullPort, hidden)
    target: XRef('producers', FullPort, hidden)
    name: str

    styling = "end:hat"

@md.Relationship()
class FlowPortConnection:
    source: XRef('consumers', FlowPort, hidden)
    target: XRef('producers', FlowPort, hidden)
    name: str

    styling = "end:hat"

@md.BlockInstance(parents=[Any], definitions=[SubProgramDefinition])
class BlockInstance: pass

@md.BlockDiagram(Block, Note, Constraint, BlockInstance, styling='icon:image')
class BlockDefinitionDiagram:
    parent: XRef('children', Block, StructuralModel, hidden)
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


md.initial_state([
    FunctionalModel('Functional Model', '', None),
    StructuralModel('Structural Model', '', None)
])

