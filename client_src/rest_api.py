
from browser import ajax, console
import json
from dataclasses import is_dataclass, asdict, fields
from typing import Any, Dict
import enum

class ExtendibleJsonEncoder(json.JSONEncoder):
    """ A JSON encoder that supports dataclasses and implements a protocol for customizing
        the generation process.
    """
    def default(self, o):
        """ We have three tricks to jsonify objects that are not normally supported by JSON.
            * Dataclass instances are serialised as dicts.
            * For objects that define a __json__ method, that method is called for serialisation.
            * For other objects, the str() protocol is used, i.e. the __str__ method is called.
        """
        if hasattr(o, '__json__'):
            return o.__json__()
        if is_dataclass(o):
            result = asdict(o)
            result['__classname__'] = type(o).__name__
            return result
        if isinstance(o, enum.Enum):
            return int(o)
        if isinstance(o, bytes):
            return o.decode('utf8')
        return str(o)


class IClean:
    def is_dirty(self) -> bool:
        raise NotImplementedError
    def set_clean(self):
        raise NotImplementedError()

class IRepresentationSerializer:
    def extract_representation(self, diagram_id: int):
        raise NotImplementedError()
    def extract_model(self, original):
        raise NotImplementedError()
    def set_model_id(self, entity):
        raise NotImplementedError()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        raise NotImplementedError()

    base_url = ''


class RestApi:
    """ A standard REST API that can easily be customized.
        Also allows clients to subscribe to and distribute events.
    """
    def __init__(self):
        self.subscriptions = {}
        self.records = {}
    def get_many_url(self):
        """ Method to retried the URL for getting the collection this API interacts with. """
        raise NotImplementedError
    def get_classes(self) -> Dict[str, Any]:
        """ Get the classes that the API needs to support. Used when de-serializing. """
        raise NotImplementedError
    def get_elements_async(self, cb):
        """ Get the collection from the server. """
        def on_data(data):
            records = []
            for d in data.json:
                cls = self.get_classes()[d['__classname__']]
                ddict = {k :v for k, v in d.items() if k != '__classname__'}
                records.append(cls(**ddict))
            self.records = {r.Id: r for r in records}
            cb(self.records)
        ajax.get(self.get_many_url(), mode="json", oncomplete=on_data)
    def add_element(self, details: Any) -> Any:
        """ Persist a new element """
        data = json.dumps(details, cls=ExtendibleJsonEncoder)
        def on_complete(update):
            details.Id = update.json['Id']
            self.records[details.Id] = details
        ajax.post(f'/data/{type(details).__name__}', blocking=True, data=data, oncomplete=on_complete,
                  mode='json', headers={"Content-Type": "application/json"})
        return details
    def delete_element(self, details: Any) -> bool:
        """ Called when an element is deleted.
            Returns True if the delete was successful, false if not.
        """
        result = False
        def oncomplete(response):
            nonlocal result
            if response.status >= 200 and response.status < 300:
                result = True
        ajax.delete(f'/data/{type(details).__name__}/{details.Id}', blocking=True, oncomplete=oncomplete)
        return result
    def update_element(self, details: Any):
        """ Update an existing element. """
        jstr = json.dumps(details, cls=ExtendibleJsonEncoder)
        ajax.post(f'/data/{type(details).__name__}/{details.Id}', blocking=True, data=jstr,
                  mode='json', headers={"Content-Type": "application/json"})
    def trigger_event(self, event_name, **details):
        for subs in self.subscriptions.get(event_name, []):
            subs(**details)
    def bind(self, event_name, cb):
        subs = self.subscriptions.setdefault(event_name, [])
        subs.append(cb)



class ExplorerApi(RestApi):
    """ A straight-forward API to interact with a database mirroring the entities shown in the explorer. """
    def __init__(self, allowed_children, explorer_classes):
        super().__init__()
        self.allowed_children = allowed_children
        self.explorer_classes = explorer_classes
    def get_many_url(self):
        return '/data/hierarchy'
    def get_classes(self):
        return self.explorer_classes
    def get_allowed_children(self, id: int):
        element = self.records[id]
        cls = type(element)
        return self.allowed_children[cls]
    def get_elements_async(self, cb):
        def on_data(records):
            # Determine the actual hierarchy.
            for r in records.values():
                r.children = []
            roots = []
            for r in records.values():
                if r.parent:
                    records[r.parent].children.append(r)
                else:
                    roots.append(r)
            self.hierarchy = roots
            cb(self.hierarchy)
        RestApi.get_elements_async(self, on_data)
    def add_element(self, details):
        """ Persist a new element created with the right-click menu """
        RestApi.add_element(self, details)
        parent = self.records[details.parent]
        parent.children.append(details)
        return details


class DiagramApi(RestApi):
    """ Specialized API for supporting diagrams.
        One complication in diagrams is that diagrams draw representations of classes stored in the model.
        The database will differentiate between the representations and the underlying classes.
        For the representation, only graphical details are stored (position, size etc).
        Other details are stored in the model class (name, description, settings, etc).
        This API needs to determine when to create or update the underlying model class, and when to update
        the representation.
    """
    def __init__(self, diagram_id, explorer_classes, representation_classes, explorer_api):
        super().__init__()
        self.diagram_id = diagram_id
        self.explorer_classes = explorer_classes
        self.representation_classes = representation_classes
        self.explorer_api: ExplorerApi = explorer_api
        self.blocks = {}
        self.relations = {}
    def get_elements_async(self, cb):
        """ Retrieve a list of elements.

            The elements of the diagram are returned as a list of (Representation, underlying entity) pairs.
            For the diagram, these are combined in one.
        """
        def on_data(response):
            if response.status >=200 and response.status < 300:
                records = []
                entity_lu = {}
                # First handle all the entities in the diagram
                for d in [r for r in response.json if 'block_cls' in r]:
                    self.blocks[d['_entity']['Id']] = d['_entity']
                    cls = self.representation_classes[d['block_cls']]
                    entity = cls.from_dict(d)
                    records.append(entity)
                    entity_lu[entity.Id] = entity

                # Then handle the relationships
                for d in [r for r in response.json if 'rel_cls' in r]:
                    # Some underlying data needs to be reconstructed
                    self.relations[d['_entity']['Id']] = d['_entity']
                    cls = self.representation_classes[d['rel_cls']]
                    d['start'] = entity_lu[d['source_repr_id']]
                    d['finish'] = entity_lu[d['target_repr_id']]
                    entity = cls.from_dict(d)
                    records.append(entity)

                cb(records)
        ajax.get(f'/data/diagram_contents/{self.diagram_id}', mode='json', oncomplete=on_data)
    def add_element(self, details: IRepresentationSerializer):
        """ Persist a new element created with the right-click menu.
            In the database there is a distinction between the logical model, and the graphic representation
            of these models. The "details" class that is given as parameter combines these two aspects,
            this function needs to split them.
        """
        if not isinstance(details, IRepresentationSerializer):
            return
        # Determine which class holds the model information, instead of the graphical information.
        # Connections store different information than blocks or messages, so these are treated differently here.
        if details.new_model_item():
            # The block itself is new, create it first as a child of this diagram.
            model_element = details.extract_model(details.logical_class())
            model_element.parent=self.diagram_id
            result = RestApi.add_element(self, model_element)
            details.set_model_id(result)

        representation = details.extract_representation(self.diagram_id)
        url = details.base_url

        def on_complete(update):
            if update.status > 299:
                console.alert("Block could not be created")
            else:
                # Set the ID of the object that was added.
                details.Id = update.json['Id']

        data = json.dumps(representation, cls=ExtendibleJsonEncoder)
        ajax.post(url, blocking=True, data=data, oncomplete=on_complete,
                  mode='json', headers={"Content-Type": "application/json"})
        return details

    def delete_element(self, details: IRepresentationSerializer) -> bool:
        """ Called when an element is deleted.
            Returns True if the delete was successful, false if not.
        """
        result = False

        def oncomplete(response):
            nonlocal result
            if response.status >= 200 and response.status < 300:
                result = True

        ajax.delete(f'{details.base_url}/{details.Id}', blocking=True, oncomplete=oncomplete)
        return result
    def update_element(self, details: IRepresentationSerializer):
        """ Update the representation of an object. """
        if details.repr_category() == 'block':
            model_item = details.extract_model(self.blocks[details.block])
        else:

            model_item = details.extract_model(self.relations[details.relationship])
        if model_item.is_dirty():
            self.explorer_api.update_element(model_item)
            model_item.set_clean()

        if details.is_dirty():
            def on_complete(update):
                if update.status > 299:
                    console.alert("Block could not be updated")
                else:
                    details.set_clean()
            data = json.dumps(details.extract_representation(self.diagram_id))
            url = details.base_url+f'/{details.Id}'
            ajax.post(url, blocking=True, data=data, oncomplete=on_complete,
                mode='json', headers={"Content-Type": "application/json"})
