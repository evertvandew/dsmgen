"""
This file makes a model of the building blocks of a model specification.

Using it, the model specification can be built and maintained with the tool itself.
"""


from typing import Self, Any
from model_definition import (Entity, Relationship, Port, BlockDiagram, LogicalModel, ModelRoot, required,
                              optional, selection, detail, longstr, XRef, ModelVersion, initial_state,
                              hidden)

ModelVersion('0.1')



@LogicalModel()
class ModelBlock:
    pass

