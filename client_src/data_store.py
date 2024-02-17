""" The central repository of all data.

It interfaces with the REST interface of the server.
It has a buffer for all data items that are used in the application.
"""
from enum import Enum, IntEnum, auto
import json
from copy import deepcopy
from dataclasses import dataclass, is_dataclass, asdict, fields, field, Field
from typing import Dict, Callable, List, Any, Iterable, Tuple, Optional, Self
from dispatcher import EventDispatcher
from math import inf         # Used when evaluating waypoint strings
from contextlib import contextmanager

from browser import ajax, console

class Collection(Enum):
    hierarchy = 'hierarchy'
    block = 'block'
    relation = 'relation'
    block_repr = 'block_repr'
    relation_repr = 'relation_repr'
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
        }[c]

class ReprCategory(IntEnum):
    no_repr = auto()
    block = auto()
    port = auto()
    relationship = auto()


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
    def get_collection(cls):
        raise NotImplementedError()
    @classmethod
    def from_dict(cls, **details) -> Self:
        """ Construct an instance of this class from a dictionary of key:value pairs. """
        return from_dict(cls, **details)
    @classmethod
    def fields(cls) -> Tuple[Field, ...]:
        """ Return the dataclasses.Field instances for each element that needs to be stored in the DB """
        # The default implementation uses dataclasses.fields
        return fields(cls)
    def asdict(self) -> Dict[str, Any]:
        result = {k.name: self.__dict__[k.name] for k in fields(self)}
        result['__classname__'] = type(self).__name__
        return result

    @classmethod
    def repr_category(cls) -> ReprCategory:
        return ReprCategory.no_repr

    @classmethod
    def is_instance_of(cls) -> bool:
        return False


class parameter_spec(str):
    """ A parameter spec is represented in the REST api as a string with this structure:
        "key1: type1, key2: type2".
        When live in the application, the spec is represented as a dict of str:type pairs.
    """
    pass

class parameter_values(str):
    """ A set of parameter values is represented in the REST api as a string with this structure:
        "Key1: value1, key2: value2".
        When live in the application, it is a simple key:value dictionary.
    """
    pass

@dataclass
class DataConfiguration:
    hierarchy_elements: Dict[str, StorableElement]
    block_entities: Dict[str, StorableElement]
    relation_entities: Dict[str, StorableElement]
    port_entities: Dict[str, StorableElement]
    base_url: str
    all_classes: Dict[str, StorableElement] = field(default_factory=dict)

    def __post_init__(self):
        result = {}
        result.update(self.hierarchy_elements)
        result.update(self.relation_entities)
        self.all_classes = result


class ExtendibleJsonEncoder(json.JSONEncoder):
    """ A JSON encoder that supports dataclasses and implements a protocol for customizing
        the generation process.
    """
    def default(self, o):
        """ We have three tricks to jsonify objects that are not normally supported by JSON.
            * For objects with an `asdict` function, that is called, and the dict serialized.
            * Dataclass instances are serialised as dicts.
            * For objects that define a `__json__` method, that method is called for serialisation.
            * For other objects, the str() protocol is used, i.e. the __str__ method is called.
        """
        if hasattr(o, 'asdict'):
            return o.asdict()
        elif hasattr(o, '__json__'):
            return o.__json__()
        elif is_dataclass(o):
            result = {k.name: o.__dict__[k.name] for k in fields(o)}
            result['__classname__'] = type(o).__name__
            return result
        elif isinstance(o, Enum):
            return int(o)
        elif isinstance(o, bytes):
            return o.decode('utf8')
        return str(o)

@dataclass
class JsonResponse:
    """ Brython doesn't document the exact type of the Response object, so we make one here
        to help the IDE flag wrong usage.
    """
    status: int
    text: str
    json: Any


def dc_from_dict(cls, ddict):
    keys = [f.name for f in fields(cls)]
    arguments = {k: v for k, v in ddict.items() if k in keys}
    return cls(**arguments)

class DataStore(EventDispatcher):
    def __init__(self, configuration: DataConfiguration):
        super().__init__()
        self.configuration = configuration
        self.shadow_copy: Dict[Collection, Dict[int: StorableElement]] = {k: {} for k in Collection}
        self.live_instances: Dict[Collection, Dict[int: StorableElement]] = {k: {} for k in Collection}
        self.all_classes = configuration.all_classes
        self.repr_collection_urls = {
            Collection.relation_repr: '_RelationshipRepresentation',
            Collection.block_repr: '_BlockRepresentation',
        }

    # Override the dispatching methods to persist the changes
    def add_data(self, item, source):
        if type(item).__name__ in self.all_classes:
            self.add(item)
        super().add_data(item, source)
    def update_data(self, item, source):
        super().update_data(item, source)
        if type(item).__name__ in self.all_classes:
            self.update(item)
    def delete_data(self, item, source):
        super().delete_data(item, source)
        if type(item).__name__ in self.all_classes:
            self.delete(item)

    @contextmanager
    def transaction(self):
        yield None

    def add(self, record: Any) -> Any:
        """ Persist a new element """
        collection = record.get_collection()
        if collection in Collection.representations():
            # Representations are to be broken up into two objects:
            # Pure representation details, and the underlying model item
            assert record.diagram
            repr, model = self.split_representation_item(collection, record)
            # Check if this is a new model item (they can be created inside a diagram)
            if not model.Id:
                # Insert this model item as a child of the diagram (diagrams are also folders in the explorer).
                model.parent = record.diagram
                # Add the model item
                self.add(model)
                # Take out the new Id of the model item
                if collection == Collection.block_repr:
                    record.block = model.Id
                    repr['block'] = model.Id
                else:
                    record.relationship = model.Id
                    repr['relationship'] = model.Id
            collection_url = self.repr_collection_urls[collection]

            def on_complete(update: JsonResponse):
                if update.status > 299:
                    console.alert("Block could not be created")
                else:
                    # Set the ID of the object that was added.
                    record.Id = update.json['Id']
                    assert self.update_cache(record) is record

            data = json.dumps(repr, cls=ExtendibleJsonEncoder)
            ajax.post(f'{self.configuration.base_url}/{collection_url}', blocking=True, data=data,
                      oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
            return record
        else:
            data = json.dumps(record, cls=ExtendibleJsonEncoder)
            def on_complete(update):
                record.Id = update.json['Id']
                assert self.update_cache(record) is record
            ajax.post(f'/data/{type(record).__name__}', blocking=True, data=data, oncomplete=on_complete,
                      mode='json', headers={"Content-Type": "application/json"})
            return record

    def update(self, record):
        collection = record.get_collection()

        def on_complete(update):
            if update.status < 300:
                assert self.update_cache(record) is record

        if collection in Collection.representations():
            # A representation is a merging of two separate entities. Treat them separately.
            repr, model = self.split_representation_item(collection, record)
            org_repr = self.shadow_copy[collection][record.Id]
            org_model = self.shadow_copy[Collection.oppose(collection)][model.Id]
            if model != org_model:
                self.update(model)
            changed = any(getattr(org_repr, k) != v for k, v in repr.items() if hasattr(org_repr, k) and k != 'ports')
            if collection == Collection.relation_repr:
                changed = changed or org_repr.waypoints != record.waypoints
            if changed:
                url = self.repr_collection_urls[collection]
                data = json.dumps(repr, cls=ExtendibleJsonEncoder)
                ajax.post(f'{self.configuration.base_url}/{url}/{record.Id}', blocking=True, data=data,
                          oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
            # Handle any ports
            if collection == Collection.block_repr and hasattr(record, 'ports'):
                orig_ports = org_repr.ports
                new_ports = record.ports
                if orig_ports != new_ports:
                    lu_orig = {p.Id: p for p in orig_ports}
                    lu_new = {p.Id: p for p in new_ports}
                    deleted = set(lu_orig) - set(lu_new)
                    added = set(lu_new) - set(lu_orig)
                    updated = [i for i in (set(lu_new) & set(lu_orig)) if lu_orig[i] != lu_new[i]]

                    for i in deleted:
                        p = lu_orig[i]
                        self.delete(p)
                        # For Port representations are always directly linked to models.
                        self.delete(self.shadow_copy[Collection.block][p.block])
                    for i in added:
                        p = lu_new[i]
                        # Set fields refering to the context of the port
                        p.parent = record.Id
                        p.diagram = record.diagram
                        # Store the new port
                        self.add(p)
                    for i in updated:
                        self.update(lu_new[i])
                    assert self.update_cache(record) == record
        else:
            original = self.shadow_copy[collection][record.Id]
            if record != original:
                data = json.dumps(record, cls=ExtendibleJsonEncoder)
                ajax.post(f'{self.configuration.base_url}/{type(record).__name__}/{record.Id}', blocking=True,
                          data=data, oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})



    def delete(self, record):
        collection = record.get_collection()
        def on_complete(update: JsonResponse):
            if update.status < 300:
                del self.shadow_copy[collection][record.Id]
                del self.live_instances[collection][record.Id]
        url = type(record).__name__ if collection not in Collection.representations() else \
            self.repr_collection_urls[collection]
        ajax.delete(f'{self.configuration.base_url}/{url}/{record.Id}', blocking=True, oncomplete=on_complete)

    def get(self, collection: Collection | str, Id: int):
        if isinstance(collection, str):
            collection = self.configuration.all_classes[collection].get_collection()
        # Check if the record is in the cache
        if r:=self.live_instances[collection].get(Id, False):
            return r
        # Cache miss. Retrieve the item from the REST API.
        raise NotImplementedError()

    def get_hierarchy(self, cb: Callable):
        def on_data(data: JsonResponse):
            records = self.make_objects(data)
            records = self.update_cache(records)
            # Determine the actual hierarchy.
            lu = {}
            for r in records:
                r.children = []
                lu[r.Id] = r
            roots = []
            for r in records:
                if r.parent:
                    lu[r.parent].children.append(r)
                else:
                    roots.append(r)
            cb(roots)
        ajax.get('/data/hierarchy', mode="json", oncomplete=on_data)

    def get_diagram_data(self, diagram_id, cb: Callable):
        """ Retrieve a list of elements.

            The elements of the diagram are returned as a list of (Representation, underlying entity) pairs.
            For the diagram, these are combined in one.
        """

        def on_data(response: JsonResponse):
            if response.status >= 200 and response.status < 300:
                records = []
                # Reconstruct the entities the diagram refers to and cache them
                for e in response.json:
                    model_details = e['_entity']
                    model_cls = self.all_classes[model_details['__classname__']]
                    model_item = dc_from_dict(model_cls, model_details)
                    self.update_cache(model_item)
                    if model_cls.is_instance_of():
                        # For Instance representations, handle the definition.
                        definition_details = e['_definition']
                        definition_cls = self.all_classes[definition_details['__classname__']]
                        definition_item = dc_from_dict(definition_cls, definition_details)
                        self.update_cache(definition_item)

                representations = []
                # Reconstruct all representations and cache them.
                for d in response.json:
                    entity = self.decode_representation(d)
                    representations.append(entity)

                # All blocks are yielded to the diagram
                records.extend(r for r in representations if r.repr_category() == ReprCategory.block)
                # A lookup of connection points is make for connecting them.
                # Ports and Blocks are stored in the same table, so Id's are unique.
                # The cache is not used for lookup, as those hold COPIES of the connection points for
                # detecting changes.
                cp_lu = {r.Id: r for r in records}

                # Ports are not yielded directly to the diagram, they are added to the block that owns them.
                for p in [r for r in representations if r.repr_category() == ReprCategory.port]:
                    block = cp_lu[p.parent]
                    block.ports.append(p)
                    cp_lu[p.Id] = p

                # Then handle the relationships
                for d in [r for r in representations if r.repr_category() == ReprCategory.relationship]:
                    # Some underlying data needs to be reconstructed
                    # The connection expects actual blocks as start and finish, not their ID.
                    # First check they actually exist.
                    if d.start not in cp_lu or d.finish not in cp_lu:
                        console.log(f"Could not find the blocks for connection {d}")
                        # Delete the faulty connection.
                        self.delete(d)
                        continue
                    d.start = cp_lu[d.start]
                    d.finish = cp_lu[d.finish]
                    records.append(d)

                for r in records:
                    self.update_cache(r)
                cb(records)

        ajax.get(f'/data/diagram_contents/{diagram_id}', mode='json', oncomplete=on_data)

    def create_representation(self, block_cls, block_id, drop_details):
        result = None
        def on_complete(update: JsonResponse):
            nonlocal result
            if update.status > 299:
                console.alert("Representation could not be created")
            else:
                result = self.decode_representation(update.json)
                result.ports = [ch for ch in result.children if ch.repr_category() == ReprCategory.port]

        data = json.dumps(drop_details)
        ajax.post(f'{self.configuration.base_url}/{block_cls}/{block_id}/create_representation', blocking=True,
                        data=data, oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
        return result

    def decode_representation(self, data: dict):
        """ Create a representation object out of a data dictionary """
        model_cls = self.all_classes[data['_entity']['__classname__']]
        details = data['_entity'].copy()
        model_instance = self.update_cache(model_cls.from_dict(**details))

        representation_cls = model_instance.representation_cls()
        return representation_cls.from_dict(model_entity=model_instance, **data)

    def make_objects(self, data: JsonResponse) -> List[StorableElement]:
        """ Turn a set of data into objects, ensuring all the types are correct """
        records = []
        for d in data.json:
            cls = self.all_classes[d['__classname__']]
            records.append(cls.from_dict(**d))
        return records

    def update_cache(self, records: List[StorableElement] | StorableElement):
        if isinstance(records, Iterable):
            return [self.update_cache(record) for record in records]
        else:
            record = records
            cls_name = type(record).__name__
            collection = record.get_collection()
            self.shadow_copy[collection][record.Id] = deepcopy(record)

            # Check if we already have an instance of this record. If so, reuse it.
            collection_records = self.live_instances[collection]
            if record.Id in collection_records:
                if collection_records[record.Id] is record:
                    # The objects are the same instance: no work necessary
                    return record
                # Update the existing record
                live_instance = collection_records[record.Id]
                for f in record.fields():
                    setattr(live_instance, f.name, getattr(record, f.name))
                return live_instance

            self.live_instances[collection][record.Id] = record
            return record

    def split_representation_item(self, collection, record) -> (Dict, StorableElement):
        repr = record.asdict()
        del repr['model_entity']
        return repr, record.model_entity

    def get_instance_parameters(self, instance_representation: Any) -> Optional[Tuple[str, type, Any]]:
        """ Inspect the definition object being instantiated by the argument, to determine the parameters it needs.
            Returns either None (if the object isn't an Instance),
            or a tuple of argument names, argument types and current argument values.
        """
        if instance_representation is None or not instance_representation.is_instance_of():
            return None
        definition = self.get(Collection.block, instance_representation.get_definition())
        param_fields = [f for f in fields(definition) if f.type == parameter_spec]
        names = []
        types = []
        values = []
        for p in param_fields:
            spec = getattr(definition, p.name)
            if isinstance(spec, str):
                type_lu = {'int': int, 'str': str, 'float': float}
                spec = {k.strip():type_lu[v.strip()] for k,v in [part.split(':') for part in spec.split(',')]}
            for k, t in spec.items():
                names.append(k)
                types.append(t)
                values.append(getattr(instance_representation, k, ''))
        return names, types, values
