""" The central repository of all data.

It interfaces with the REST interface of the server.
It has a buffer for all data items that are used in the application.


Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
import sys

from browser import console
import logging
from enum import Enum, IntEnum, auto
import json
from dataclasses import dataclass, is_dataclass, fields, field
from typing import Dict, Callable, List, Any, Iterable, Tuple, Optional, Type, Protocol
from dispatcher import EventDispatcher
from math import inf         # Do not delete: used when evaluating waypoint strings
from contextlib import contextmanager
from storable_element import StorableElement, Collection, ReprCategory
from browser import ajax, alert

class parameter_spec(dict):
    """ A parameter spec is represented in the REST api as a string with this structure:
        "key1: type1, key2: type2".
        When live in the application, the spec is represented as a dict of str:type pairs.
    """
    def __init__(self, values):
        if isinstance(values, dict):
            super().__init__(values)
        elif isinstance(values, str):
            if values.startswith('{'):
                super().__init__(json.loads(values))
            elif ':' in values:
                super().__init__(part.split(':') for part in values.split(','))
            else:
                super().__init__()

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
    all_classes: Dict[str, Type[StorableElement]] = field(default_factory=dict)

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
            return o.value
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
        self.all_classes: Dict[str, Type[StorableElement]] = configuration.all_classes

    @contextmanager
    def transaction(self):
        yield None

    @property
    def ports(self) -> List[StorableElement]:
        """ Return all port elements in the current model """
        return [e for e in self.live_instances[Collection.block].values() if type(e).__name__ in self.configuration.port_entities]
    @property
    def relationships(self) -> List[StorableElement]:
        """ Return all relationship elements in the current model """
        return list(self.live_instances[Collection.relation].values())

    def get_ports(self, o: StorableElement):
        if o.get_collection() == Collection.block:
            return getattr(o, 'ports', [])
        elif o.get_collection() == Collection.block_repr:
            if o.repr_category() == ReprCategory.block:
                return getattr(o, 'ports', [])

    def add(self, record: StorableElement, redo=False) -> StorableElement:
        """ Persist a simple element, without any considerations for dependencies. """
        params = {}
        if redo:
            params = {'redo': True}

        def on_complete(update: JsonResponse):
            if update.status > 299:
                alert("Block could not be created")
            else:
                # Set the ID of the object that was added.
                record.Id = update.json['Id']
                if (cached_record := self.update_cache(record)) is not record:
                    # Check if the cached object is actually used.
                    # It could be a deleted object which ID is reused by the database.
                    if sys.getrefcount(cached_record) >= 2:
                        print("Database ID is reused while old copies still exist!", cached_record)
                        collection = record.get_collection()
                        self.live_instances[collection][record.Id] = record

        data = json.dumps(record, cls=ExtendibleJsonEncoder)
        ajax.post(f'{self.configuration.base_url}/{record.get_db_table()}', blocking=True, data=data,
                  oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"}, params=params)
        return record


    def add_complex(self, record: StorableElement, redo=False) -> StorableElement:
        """ Persist a new element """
        collection = record.get_collection()
        # Representations also have a record with model details that may or may not already exist.
        if model := record.get_model_details():
            # Check if this is a new model item (they can be created inside a diagram)
            if not model.Id:
                # Insert this model item as a child of the diagram (diagrams are also folders in the explorer).
                if not getattr(model, 'parent', True):
                    model.parent = record.get_diagram()
                # Add the model item
                self.add_complex(model, redo)
                self.add_data(record)

            self.add(record, redo)
            # For ports, also update the ports collections in the parent block.
            if record.repr_category() == ReprCategory.port:
                repr_parent = self.live_instances[Collection.block_repr][record.get_parent()]
                if record not in repr_parent.ports:
                    repr_parent.ports.append(record)
                    self.update_cache(repr_parent)
                    self.update_data(repr_parent)
            self.add_data(record)
        else:
            self.add(record, redo)
            if record.Id < 1:
                raise RuntimeError("Could not add record")
            self.add_data(record)
            # For ports, also update the ports collections in the parent block.
            if type(record).__name__ in self.configuration.port_entities:
                parent_block = self.live_instances[Collection.block][record.get_parent()]
                if record not in parent_block.ports:
                    parent_block.ports.append(record)
                    self.update_cache(parent_block)
                    self.update_data(parent_block)
        return record

    def update(self, record: StorableElement):
        collection = record.get_collection()

        def on_complete(update):
            if update.status < 300:
                assert self.update_cache(record) is record

        if model := record.get_model_details():
            # A representation is a merging of two separate entities. Treat them separately.
            org_repr = self.shadow_copy[collection][record.Id]
            org_model = self.shadow_copy[Collection.oppose(collection)][model.Id]
            if model != org_model:
                self.update(model)
            repr = record.asdict()
            changed = any(getattr(org_repr, k) != v for k, v in repr.items() if hasattr(org_repr, k) and k not in ['ports', 'model_entity', '__classname__'])
            if collection == Collection.relation_repr:
                changed = changed or org_repr.waypoints != record.get_waypoints()
            if changed:
                data = json.dumps(repr, cls=ExtendibleJsonEncoder)
                ajax.post(f'{self.configuration.base_url}/{record.get_db_table()}/{record.Id}', blocking=True, data=data,
                          oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
                self.update_data(record)

        else:
            # Handle non-representations
            original = self.shadow_copy[collection][record.Id]
            if record != original:
                data = json.dumps(record, cls=ExtendibleJsonEncoder)
                ajax.post(f'{self.configuration.base_url}/{record.get_db_table()}/{record.Id}', blocking=True,
                          data=data, oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
                self.update_data(record)

    def delete(self, record: StorableElement) -> bool:
        """ Returns true if the deletion is successful. """
        collection = record.get_collection()

        if not record.Id in self.live_instances[collection]:
            return True

        # Find any dependencies and delete these first.
        to_delete = []
        if collection == Collection.block_repr:
            to_delete.extend(c for c in self.live_instances[Collection.block_repr].values() if c.parent == record.Id)
        if collection == Collection.block:
            to_delete.extend(c for c in self.live_instances[Collection.block].values() if c.parent == record.Id)
            to_delete.extend(r for r in self.live_instances[Collection.block_repr].values() if r.model_entity.Id == record.Id)
            # Delete relationships connected to this block
            to_delete.extend(r for r in self.live_instances[Collection.relation].values() if r.source == record.Id)
            to_delete.extend(r for r in self.live_instances[Collection.relation].values() if r.target == record.Id)
            # Don't do the representations of these relations, they will be deleted at another point.
        if collection == Collection.relation:
            to_delete.extend(r for r in self.live_instances[Collection.relation_repr].values() if r.relationship == record.Id)
        for d in to_delete:
            self.delete(d)

        # Now delete the actual entities.
        result = False
        def on_complete(update: JsonResponse):
            nonlocal result
            if update.status < 300:
                del self.shadow_copy[collection][record.Id]
                del self.live_instances[collection][record.Id]
                result = True
        ajax.delete(f'{self.configuration.base_url}/{record.get_db_table()}/{record.Id}', blocking=True, oncomplete=on_complete)
        self.delete_data(record)
        return result

    def get(self, collection: Collection | str, Id: int) -> StorableElement:
        if isinstance(collection, str):
            collection = self.configuration.all_classes[collection].get_collection()
        # Check if the record is in the cache
        if r:=self.live_instances[collection].get(Id, False):
            return r
        # Cache miss. Retrieve the item from the REST API.
        raise NotImplementedError()

    def get_hierarchy(self, cb: Callable):
        def on_data(data: JsonResponse):
            if data.status >= 400:
                # A problem occurred loading the data
                alert("Could not load data")
                return
            records = self.make_objects(data)
            # Determine the actual hierarchy.
            lu = {}
            for r in records:
                r.children = []
                lu[r.Id] = r
            roots = []
            for r in records:
                if r.get_parent():
                    lu[r.get_parent()].get_children().append(r)
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

                representations = []
                # Reconstruct all representations and cache them.
                # Do blocks first, then ports, then represations.
                repr_class = [
                    ReprCategory.block,
                    ReprCategory.laned_block,
                    ReprCategory.block_instance,
                    ReprCategory.laned_instance,
                    ReprCategory.port,
                    ReprCategory.relationship,
                    ReprCategory.laned_connection,
                    ReprCategory.message
                ]
                # Check the order up objects doesn't miss one.
                assert len(repr_class) == len(ReprCategory) - 1

                def filter_reprs(reprs, c: repr_class):
                    for r in reprs:
                        if r['category'] == c:
                            yield r

                # Sort the received entities by their order number.
                response.json.sort(key=lambda e: e.get('order', None) or 1000000)

                # Now handle the different types of representations
                for filter in repr_class:
                    for d in filter_reprs(response.json, filter):
                        entity = self.decode_representation(d)
                        representations.append(entity)

                        if filter == ReprCategory.port:
                            # Ports are not yielded through records, but attached to their owners.
                            block = self.get(Collection.block_repr, entity.parent)
                            block.get_ports().append(entity)
                            block.get_model_details().get_ports().append(entity.model_entity)
                            self.update_cache([block, block.get_model_details()])
                        elif filter == ReprCategory.message:
                            # Like the ports, messages are yielded through representations.
                            relation = self.get(Collection.relation_repr, entity.parent)
                            relation.get_messages().append(entity)
                            self.update_cache(relation)
                        else:
                            # All blocks are yielded to the diagram
                            records.append(entity)

                cb(records)

        ajax.get(f'/data/diagram_contents/{diagram_id}', mode='json', oncomplete=on_data)

    def create_representation(self, block_cls, block_id, drop_details) -> StorableElement:
        result = None
        def on_complete(update: JsonResponse):
            nonlocal result
            if update.status > 299:
                alert("Representation could not be created")
            else:
                drop_details.update(update.json)
                result = self.decode_representation(drop_details)
                if hasattr(result, 'children'):
                    result.ports = [ch for ch in result.children if ch.repr_category() == ReprCategory.port]

        print("Dumping to json", drop_details)
        data = json.dumps(drop_details, cls=ExtendibleJsonEncoder)
        print("POSTING")
        ajax.post(f'{self.configuration.base_url}/{block_cls}/{block_id}/create_representation', blocking=True,
                        data=data, oncomplete=on_complete, mode='json', headers={"Content-Type": "application/json"})
        return result

    def decode_representation(self, data: dict) -> StorableElement:
        """ Create a representation object out of a data dictionary """
        model_cls = self.all_classes[data['_entity']['__classname__']]
        details = data['_entity'].copy()
        model_instance = model_cls.from_dict(self, **details)
        assert model_instance.Id, f"Model instance {type(model_instance).__name__} is not created properly."
        if not self.is_cached(model_instance):
            # A new instance was added: let the rest of the app know.
            # Update the cache first
            model_instance = self.update_cache(model_instance)
            # Dispatch the add event.
            self.add_data(model_instance)
        else:
            # Make sure the shadow copy is in sync with this object, to prevent unnecessary updates.
            model_instance = self.update_cache(model_instance)
        if 'children' in data:
            data['children'] = [self.decode_representation(ch) for ch in data.get('children', [])]
        if 'category' in data and data['category']:
            repr_category = data['category']
        else:
            repr_category = {
                '_RelationshipRepresentation': ReprCategory.relationship,
                '_MessageRepresentation': ReprCategory.message,
                '_BlockInstanceRepresentation': ReprCategory.block_instance,
                '_InstanceRepresentation': ReprCategory.block_instance,
                '_BlockRepresentation': ReprCategory.block,
            }[data['__classname__']]
        representation_cls = model_instance.get_representation_cls(repr_category)
        repr = representation_cls.from_dict(self, model_entity=model_instance, **data)
        self.update_cache(repr)
        return repr

    def make_objects(self, data: JsonResponse) -> List[StorableElement]:
        """ Turn a set of data into objects, ensuring all the types are correct """
        records = []
        for d in data.json:
            cls = self.all_classes[d['__classname__']]
            instance = cls.from_dict(self, **d)
            self.update_cache(instance)
            records.append(instance)
        return records

    def is_cached(self, record: StorableElement) -> bool:
        collection = record.get_collection()
        return record.Id in self.live_instances[collection]

    def update_cache(self, records: List[StorableElement] | StorableElement):
        if isinstance(records, Iterable):
            return [self.update_cache(record) for record in records]
        else:
            record = records
            collection = record.get_collection()
            self.shadow_copy[collection][record.Id] = record.copy()

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

    def get_shadow_copy(self, record: StorableElement) -> Optional[StorableElement]:
        collection = record.get_collection()
        return self.shadow_copy[collection].get(record.Id, None)

    def get_live_instance(self, record: StorableElement) -> Optional[StorableElement]:
        collection = record.get_collection()
        return self.live_instances[collection].get(record.Id, None)

    def split_representation_item(self, collection, record) -> (Dict, StorableElement):
        repr = record.asdict()
        return repr, record.model_entity

    def get_instance_parameters(self, instance_representation: Any) -> Optional[Tuple[List[str], List[type], List[Any]]]:
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




class UndoableAction(Protocol):
    def undo(self, ds: 'UndoableDataStore'):
        raise NotImplementedError

    def redo(self, ds: 'UndoableDataStore'):
        raise NotImplementedError


class AddAction(UndoableAction):
    def __init__(self, item: StorableElement):
        """ Create an undo point for a newly created item """
        # We need to know the ID it got from the database
        assert getattr(item, 'Id')
        self.item = item
    def undo(self, ds):
        ds.undo_add(self.item)
    def redo(self, ds):
        ds.redo_add(self.item)
    def __str__(self):
        return f'Add: {self.item}'

class UpdateAction(UndoableAction):
    def __init__(self, updated: StorableElement, original:StorableElement):
        # With the update function, the internal state of the pre and post situation must be recorded.
        # That means we need to make copies of the internal objects.
        self.updated = updated.copy()
        self.original = original.copy()
    def undo(self, ds):
        ds.undo_update(self.updated, self.original)
    def redo(self, ds):
        ds.redo_update(self.updated, self.original)
    def __str__(self):
        return f'Update: {self.updated}'

class DeleteAction(UndoableAction):
    def __init__(self, item: StorableElement):
        self.item = item

    def undo(self, ds):
        ds.undo_delete(self.item)

    def redo(self, ds):
        ds.redo_delete(self.item)
    def __str__(self):
        return f'Delete: {self.item}'


class CompoundAction(UndoableAction):
    def __init__(self, actions: List[UndoableAction]):
        """ Actions are given in de order in which they were applied, they will by undone in reverse order. """
        self.actions = actions
    def undo(self, ds):
        for action in reversed(self.actions):
            action.undo(ds)

    def redo(self, ds):
        for action in self.actions:
            action.redo(ds)
    def __str__(self):
        return f'Compound: {[str(a) for a in self.actions]}'


class UndoableDataStore(DataStore):
    def __init__(self, configuration: DataConfiguration):
        super().__init__(configuration)
        self.undo_queue: List[UndoableAction] = []
        self.redo_queue: List[UndoableAction] = []
        self.recorded_actions = []
        self.record_level = 0

    def clear_recorder(self):
        self.record_level = 0
        self.recorded_actions = []

    @contextmanager
    def action_recorder(self):
        is_root = self.record_level == 0
        if is_root:
            self.recorded_actions = []
        self.record_level += 1

        yield self.recorded_actions
        if is_root:
            if len(self.recorded_actions) > 1:
                self.undo_queue.append(CompoundAction(self.recorded_actions))
            if len(self.recorded_actions) == 1:
                self.undo_queue.append(self.recorded_actions[0])

            self.record_level = 0
            self.recorded_actions = []
        else:
            self.record_level -= 1

    def add(self, record: StorableElement, redo=False):
        with self.action_recorder() as actions:
            result = super().add(record, redo)

            actions.append(AddAction(result))
        return result

    def add_complex(self, record: StorableElement, redo=False) -> StorableElement:
        with self.action_recorder() as action:
            result = super().add_complex(record, redo)
        return result

    def update(self, record: StorableElement):
        with self.action_recorder() as actions:
            actions.append(UpdateAction(record, self.get_shadow_copy(record)))
            result = super().update(record)
        return result

    def delete(self, record: StorableElement):
        with self.action_recorder() as actions:
            result = super().delete(record)
            actions.append(DeleteAction(record))
        return result

    def create_representation(self, block_cls, block_id, details) -> StorableElement:
        result = super().create_representation(block_cls, block_id, details)
        with self.action_recorder() as actions:
            actions.append(AddAction(result))
            if hasattr(result, 'children'):
                for ch in result.children:
                    actions.append(AddAction(ch))
        return result

    def undo_one_action(self):
        self.record_level = 1       # Capture actions, do NOT create a new undo action.
        if not self.undo_queue:
            return
        action = self.undo_queue.pop(-1)
        try:
            action.undo(self)
        finally:
            self.redo_queue.append(action)
            self.clear_recorder()


    def redo_one_action(self):
        self.record_level = 1       # Capture actions, do NOT create a new undo action.
        if not self.redo_queue:
            return
        action = self.redo_queue.pop(-1)
        try:
            action.redo(self)
        finally:
            self.undo_queue.append(action)
            self.clear_recorder()

    def undo_add(self, item: StorableElement):
        super().delete(item)

    def redo_add(self, item: StorableElement):
        # Normally, an object to be added can not have an id. The redo flag disables this check.
        # That way, any references within the undo_queue remain correct
        super().add(item, redo=True)

    def undo_update(self, updated: StorableElement, original: StorableElement):
        # Retrieve the live object and update it, then call the Update function.
        live_instance = self.get_live_instance(updated)
        for k, v in original.asdict().items():
            if hasattr(live_instance, k):
                try:
                    setattr(live_instance, k, v)
                except AttributeError:
                    pass
        super().update(live_instance)

    def redo_update(self, updated: StorableElement, original: StorableElement):
        # Retrieve the live object and update it, then call the Update function.
        live_instance = self.get_live_instance(updated)
        for k, v in updated.asdict().items():
            if hasattr(live_instance, k):
                try:
                    setattr(live_instance, k, v)
                except AttributeError:
                    pass
        super().update(live_instance)

    def undo_delete(self, item: StorableElement):
        super().add(item, redo=True)

    def redo_delete(self, item: StorableElement):
        super().delete(item)
