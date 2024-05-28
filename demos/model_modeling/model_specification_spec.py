
from typing import Self, Any
from model_definition import (ModelDefinition, required,
                              selection, detail, longstr, XRef, hidden)

# The tooling expects an ModelDifinition object named `md`
md = ModelDefinition()
md.ModelVersion('0.1')

available_shapes = "bar box circle closedcircle cloud component diamond document drum ellipse folder hexagon hourglass label note obliquerect octagon rect ringedclosedcircle square stickman tape triangledown triangleup tunnel"
available_line_endings = "arrow halfarrow pointer triangle diamond longdiamond square arrowopen halfarrowopen pointeropen triangleopen diamondopen longdiamondopen squareopen hat linearror halflinearror one only_one zero_or_one many zero_or_many"
available_port_shapes = "square cup connector circle half_circle triangle_in triangle_out diamond"

###############################################################################
## Logical model
@md.ModelRoot(styling='icon:folder')
class RootModel:
    pass

@md.LogicalModel(styling='icon:folder', parents=[Self, RootModel])
class ModelCollection:
    name: str
    description: longstr

###############################################################################
## Entities for Notes & Constraints, which are used in all other diagrams
@md.Entity(styling = "shape:note;structure:Note;icon:message", parents=[Any])
class Note:
    description: (longstr, required)

@md.Relationship(styling = "end:hat", source=[None], target=[Any])
class Anchor:
    name: str

###############################################################################
## Entities for diagrams

@md.Entity(styling="shape:rect", parents=['SpecificationDiagram'])
class ModelingEntity:
    name: str
    description: (longstr, detail)
    block_shape: selection(available_shapes)
    entity_styling: str

@md.Entity(styling="shape:rect", parents=['SpecificationDiagram'])
class RelationshipEntity:
    name: str
    start_shape: selection(available_line_endings)
    end_shape: selection(available_line_endings)
    entity_styling: str
    
@md.Entity(styling = "shape:rect;structure:Block;icon:square-full", parents=['SpecificationDiagram'])
class PortEntity:
    name: str
    description: (longstr, detail)
    entity_styling: str

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
    block_shape: str
    entity_styling: str

@md.Entity(styling='shape:rect', parents=['SpecificationDiagram'])
class InstanceEntity:
    name: str
    description: (longstr, detail)
    block_shape: str
    entity_styling: str

@md.Entity(styling='shape:folder', parents=['SpecificationDiagram'])
class HierarchyEntity:
    name: str
    description: (longstr, detail)
    entity_styling: str


all_entities = [ModelingEntity, RelationshipEntity, PortEntity, InstanceEntity, CompoundEntity, HierarchyEntity, DiagramEntity]


@md.CompoundEntity(
    parents=[Self, 'SpecificationDiagram'],
    elements=[*all_entities, Attribute, SelectionArgument, SelectionOption, Self],
    styling = "shape:folder;structure:Block;blockcolor:yellow;icon:square-full;icon:image")
class Page:
    name: str

@md.BlockDiagram(*all_entities, Attribute, SelectionArgument, SelectionOption,
              Page, Note, styling="icon:image", parents=[ModelCollection])
class SpecificationDiagram:
    name: str
    description: (longstr, detail)

###############################################################################
## Relationships between entities

@md.Relationship(styling = "endmarker:hat",
                 source=all_entities,
                 target=[RelationshipEntity])
class RelationshipSource:
    pass

@md.Relationship(styling = "startmarker:hat",
                 source=[RelationshipEntity],
                 target=all_entities)
class RelationshipTarget:
    pass

@md.Relationship(styling = "startmarker:hat;endmarker:hat",
                 source=all_entities,
                 target=[RelationshipEntity])
class RelationshipBothEnds:
    pass

@md.Relationship(styling = "endmarker:square",
                 source=all_entities,
                 target=[Attribute, SelectionArgument])
class EntityAttribute:
    pass

@md.Relationship(styling = "endmarker:square", source=[SelectionArgument], target=[SelectionOption])
class SelectionOptionLink:
    pass

@md.Relationship(styling = "endmarker:hat", source=all_entities, target=[DiagramEntity])
class DiagramEntityLink:
    pass

@md.Relationship(styling = "endmarker:diamond", source=[ModelingEntity, CompoundEntity], target=[PortEntity])
class PortEntityLink:
    pass


@md.Relationship(styling = "endmarker:hat;startmarker:square", source=[ModelingEntity, CompoundEntity, PortEntity], target=[InstanceEntity])
class EntityInstantation:
    pass

###############################################################################
##

md.initial_state([
    ModelCollection('Model Collection', '', None),
])
