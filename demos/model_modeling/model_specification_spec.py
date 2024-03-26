
from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              selection, detail, longstr, XRef, hidden)

# The tooling expects an ModelDifinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')



###############################################################################
## Logical model
@md.ModelRoot(styling='icon:folder')
class RootModel:
    pass

@md.LogicalModel(styling='icon:folder', parents=[Self, RootModel])
class ModelCollection:
    name: str
    description: longstr
    parent: XRef('children', hidden)

###############################################################################
## Entities for Notes & Constraints, which are used in all other diagrams
@md.Entity(styling = "shape:note;structure:Note;icon:message", parents=[Any])
class Note:
    description: (longstr, required)

@md.Relationship(styling = "end:hat")
class Anchor:
    source: XRef('owner', Note, hidden)
    target: XRef('notes', Any, hidden)
    name: str

###############################################################################
## Entities for diagrams

@md.Entity(styling="shape:rect", parents=['SpecificationDiagram'])
class ModelEntity:
    name: str
    description: (longstr, detail)
    styling: str

@md.Entity(styling="shape:rect", parents=['SpecificationDiagram'])
class RelationshipEntity:
    name: str
    styling: str
    
@md.Entity(styling = "shape:rect;structure:Block;icon:square-full", parents=['SpecificationDiagram'])
class PortEntity:
    name: str
    description: (longstr, detail)
    styling: str

@md.Entity(styling='shape:document')
class Attribute:
    name: str
    type: selection("int str longstr date datetime time")

@md.Entity(styling='shape:tunnel')
class SelectionArgument:
    name: str

@md.Entity(styling='shape:label')
class SelectionOption:
    name: str

@md.Entity(styling='shape:octagon', parents=['SpecificationDiagram'])
class DiagramEntity:
    name: str
    type: selection("blockdiagram")

@md.Entity(styling='shape:rect', parents=['SpecificationDiagram'])
class CompoundEntity:
    name: str
    description: (longstr, detail)
    styling: str

@md.Entity(styling='shape:rect', parents=['SpecificationDiagram'])
class InstanceEntity:
    name: str
    description: (longstr, detail)
    styling: str

@md.Entity(styling='shape:folder', parents=['SpecificationDiagram'])
class HierarchyEntity:
    name: str
    description: (longstr, detail)
    styling: str

@md.CompoundEntity(
    parents=[Self, 'SpecificationDiagram'],
    elements=[ModelEntity, RelationshipEntity, PortEntity, Attribute, SelectionArgument, SelectionOption, Self],
    styling = "shape:folder;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class Page:
    name: str

@md.BlockDiagram(ModelEntity, RelationshipEntity, PortEntity, Attribute, SelectionArgument, SelectionOption,
              Page, styling="icon:image", parents=[ModelCollection])
class SpecificationDiagram:
    name: str
    description: (longstr, detail)

###############################################################################
## Relationships between entities

@md.Relationship(styling = "end:hat")
class RelationshipSource:
    source: XRef('entity', ModelEntity, PortEntity, CompoundEntity, InstanceEntity, hidden)
    target: XRef('relationship', RelationshipEntity, hidden)

@md.Relationship(styling = "end:hat")
class RelationshipTarget:
    source: XRef('entity', RelationshipEntity, hidden)
    target: XRef('relationship', ModelEntity, PortEntity, CompoundEntity, InstanceEntity, hidden)

@md.Relationship(styling = "end:square")
class EntityAttribute:
    source: XRef('entity', ModelEntity, PortEntity, RelationshipEntity, DiagramEntity, HierarchyEntity, CompoundEntity, InstanceEntity, hidden)
    target: XRef('attribute', Attribute, SelectionArgument, hidden)

@md.Relationship(styling = "end:square")
class SelectionOptionLink:
    source: XRef('argument', SelectionArgument, hidden)
    target: XRef('option', SelectionOption, hidden)

@md.Relationship(styling = "end:hat")
class DiagramEntityLink:
    source: XRef('entity', ModelEntity, CompoundEntity, InstanceEntity, hidden)
    target: XRef('diagram', DiagramEntity, hidden)

@md.Relationship(styling = "end:diamond")
class PortEntityLink:
    source: XRef('entity', ModelEntity, CompoundEntity, hidden)
    target: XRef('port', PortEntity, hidden)


@md.Relationship(styling = "end:hat;start:")
class EntityInstantation:
    source: XRef('entity', ModelEntity, CompoundEntity, hidden)
    target: XRef('instance', InstanceEntity, hidden)

###############################################################################
##

md.initial_state([
    ModelCollection('Model Collection', '', None),
])
