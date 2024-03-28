from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              parameter_values, detail, longstr, XRef, parameter_spec,
                              hidden)

# The tooling expects an ModelDifinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')


@md.LogicalModel(styling='icon:folder')
class LibraryFolder:
    name: str
    description: longstr
    parent: XRef('children', Self, hidden)

@md.LogicalModel(styling='icon:folder')
class ProgramFolder:
    name: str
    description: longstr
    parent: XRef('children', Self, hidden)


###############################################################################
## Entities for Notes & Constraints
@md.Entity(styling = "shape:note;structure:Note;icon:message")
class Note:
    description: (longstr, required)
    parent: XRef('children', Any, hidden)

@md.Relationship(styling = "endmarker:hat")
class Anchor:
    source: XRef('owner', Note, hidden)
    target: XRef('notes', Any, hidden)
    name: str

###############################################################################
## Definition of blocks in the Library
@md.Entity(styling = "shape:rect;structure:Block;icon:square-full")
class BlockDefinition:
    parent: XRef('children', Self, LibraryFolder, hidden)
    name: str
    implementation: (longstr, detail)
    parameters: (parameter_spec, detail)

@md.CompoundEntity(parents=[LibraryFolder], elements=[Note, "BlockInstance", "SubProgram"], styling = "shape:rect;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class SubProgramDefinition:
    name: str
    description: (longstr, detail)
    parameters: (parameter_spec, detail)

###############################################################################
## Instances of blocks in actual program(s)
@md.BlockInstance(parents=[SubProgramDefinition, 'SubProgram', 'ProgramDefinition'],
               definitions=[BlockDefinition, SubProgramDefinition],
               styling = "shape:rect;structure:Block;icon:square-full")
class BlockInstance:
    parameters: (parameter_values('parent.parameters'), detail)
    name = "<<{self._definition['name']}>>"

@md.CompoundEntity(parents=["ProgramDefinition", SubProgramDefinition, Self],
                elements=[Note, BlockInstance, Self],
                styling="shape:rect;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class SubProgram:
    name: str
    description: (longstr, detail)
    parameters: (longstr, detail)

@md.Port(styling = "shape:square;fill:yellow;icon:arrows-alt-h")
class Input:
    name: str
    parent: XRef('ports', SubProgram, SubProgramDefinition, BlockDefinition, hidden)

@md.Port(styling = "shape:square;fill:yellow;icon:arrows-alt-h")
class Output:
    name: str
    parent: XRef('ports', SubProgram, SubProgramDefinition, BlockDefinition, hidden)


@md.Port(styling = "shape:square;fill:green;icon:arrows-alt-h")
class AsyncInput:
    name: str
    parent: XRef('ports', SubProgram, SubProgramDefinition, BlockDefinition, hidden)

@md.Port(styling = "shape:square;fill:green;icon:arrows-alt-h")
class AsyncOutput:
    name: str
    parent: XRef('ports', SubProgram, SubProgramDefinition, BlockDefinition, hidden)

@md.Relationship(styling='endmarker:arrow')
class SynchronousChannel:
    source: XRef('source', Output)
    target: XRef('target', Input)

@md.Relationship(styling='endmarker:arrowopen')
class AsyncChannel:
    source: XRef('source', AsyncOutput)
    target: XRef('target', AsyncInput)


###############################################################################
## Definition of the actual program
@md.BlockDiagram(Note, BlockInstance, SubProgram, styling='icon:image')
class ProgramDefinition:
    parent: XRef('children', ProgramFolder, hidden)
    name: str
    description: (longstr, detail)



md.initial_state([
    LibraryFolder('Library', 'Pre-defined blocks that can be used in programs.', None),
    ProgramFolder('Programs', 'Here be the programs.', None)
])
