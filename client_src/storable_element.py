
from enum import Enum, IntEnum, auto
from typing import Self, Tuple, List, Dict, Any, Optional, Type
from dataclasses import dataclass, fields, Field
from copy import deepcopy
from point import Point

class Collection(Enum):
    hierarchy = 'hierarchy'
    block = 'block'
    relation = 'relation'
    message = 'message'
    block_repr = 'block_repr'
    relation_repr = 'relation_repr'
    message_repr = 'message_repr'
    not_storable = ''

    @classmethod
    def representations(cls):
        return [cls.block_repr, cls.relation_repr]

    @classmethod
    def oppose(cls, c):
        """ Find the representation collection for a model collection, and the reverse. """
        return {
            cls.block: cls.block_repr,
            cls.block_repr: cls.block,
            cls.relation: cls.relation_repr,
            cls.relation_repr: cls.relation,
            cls.message: cls.message_repr,
            cls.message_repr: cls.message
        }[c]

class ReprCategory(IntEnum):
    no_repr = auto()
    block = auto()
    port = auto()
    relationship = auto()
    message = auto()


def from_dict(cls, **details) -> Self:
    """ Construct an instance of this class from a dictionary of key:value pairs. """
    # Use only elements accepted by this dataclass.
    keys = [f.name for f in fields(cls)]
    kwargs = {k:v for k, v in details.items() if k in keys}
    return cls(**kwargs)

@dataclass
class StorableElement:
    Id: int = 0
    @classmethod
    def get_collection(cls) -> Collection:
        raise NotImplementedError()
    @classmethod
    def from_dict(cls, data_store: "DataStore", **details) -> Self:
        """ Construct an instance of this class from a dictionary of key:value pairs. """
        return from_dict(cls, **details)
    @classmethod
    def fields(cls) -> Tuple[Field, ...]:
        """ Return the dataclasses.Field instances for each element that needs to be stored in the DB """
        # The default implementation uses dataclasses.fields
        return fields(cls)
    def asdict(self, ignore: List[str]=None) -> Dict[str, Any]:
        ignore = ignore or []   # Use a safe default value for the ignore argument
        keys = [f.name for f in fields(self) if f.name not in ignore]
        result = {k: self.__dict__[k] for k in keys}
        result['__classname__'] = type(self).__name__
        return result

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.no_repr

    @classmethod
    def is_instance_of(cls) -> bool:
        return False

    def copy(self) -> Self:
        # Create a deep copy from the persistent fields for this data structure.
        return from_dict(type(self), **deepcopy(self.asdict()))

    @classmethod
    def get_db_table(cls):
        return cls.__name__

    def get_model_details(self) -> Optional[Type[Self]]:
        return None

    def get_diagram(self) -> Optional[int]:
        return getattr(self, 'diagram', None)

    def get_parent(self) -> Optional[int]:
        return getattr(self, 'parent', None)

    def get_waypoints(self) -> Optional[List[Point]]:
        return getattr(self, 'waypoints', None)

    def get_ports(self) -> Optional[List[Type[Self]]]:
        return getattr(self, 'ports', None)

    def get_children(self) -> Optional[List[Type[Self]]]:
        return getattr(self, 'children', None)

    def get_messages(self) -> Optional[List[Type[Self]]]:
        return getattr(self, 'messages', None)
