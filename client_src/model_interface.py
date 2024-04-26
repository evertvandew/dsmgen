

from dataclasses import dataclass
from typing import List, Optional, Self, Dict, Any
from data_store import ReprCategory

class DataConvertor:
    """ A dataconvertor converts strings to a specific type, and vice-versa.
        The interface corresponds to the built-in API of most built-in types.
    """
    def __init__(self, str):
        raise RuntimeError()
    def __str__(self) -> str:
        raise RuntimeError()

@dataclass
class EditableParameterDetails:
    """ Description for a parameter that can be edited for an element in a model item. """
    name: str
    type: type   # Key: value pairs used by the property_editor to create input fields.
    current_value: Any
    convertor: DataConvertor


class ModelEntity:
    """ An interface class describing the behaviour of an item represented in a diagram. """
    default_styling = {}
    def get_text(self, index: int) -> str:
        """ Retrieve a specific string associated with the item that is needed in the diagram. """
        return getattr(self, 'name', '')
    def get_nr_texts(self) -> int:
        """ Ask how many texts this item wants to display """
        return 1

    def get_editable_parameters(self) -> List[EditableParameterDetails]:
        return []
    @classmethod
    def supports_ports(cls) -> bool:
        return False

    @classmethod
    def get_representation_cls(cls, context: ReprCategory) -> Optional[Self]:
        """ Create a shape representing this model item.
            context: how this entity is represented: as a block, as a port, as a relation, etc.
        """
        return None

    @classmethod
    def get_allowed_ports(cls) -> List[Self]:
        """ Determine which ports are allowed to be attached to a model entity """
        return []

    def get_instance_parameters(self) -> List[EditableParameterDetails]:
        return []

    def update(self, data: Dict[str, Any]):
        for k, v in data.items():
            setattr(self, k, v)

    @classmethod
    def getDefaultStyle(cls):
        return cls.default_styling.copy()
