
from dataclasses import dataclass
from typing import Callable, Any, Dict, Optional
from fnmatch import fnmatch
from weakref import ref

@dataclass
class EventSubscription:
    path: str
    source: Any
    context: Optional[Dict]
    callback: Callable[[str, Any, "EventDispatcher", Dict], None]

class EventDispatcher:
    def __init__(self):
        self.subscriptions: EventSubscription = []
    def trigger_event(self, event_name, source, **details):
        for sub in self.subscriptions:
            if fnmatch(event_name, sub.path):
                details['source'] = sub.source
                details['data_store'] = self
                details['context'] = sub.context
                sub.callback(event_name, source, self, details)
    def subscribe(self, event_name, source, cb, context=None):
        # Do not accept bound functions, as these prevent objects from being garbage collected.
        assert getattr(cb, 'im_self', None) is None, "Member functions are not supported"
        #sub = EventSubscription(event_name, ref(source), context, cb)
        sub = EventSubscription(event_name, source, context, cb)
        self.subscriptions.append(sub)
    def unsubscribe(self, source):
        self.subscriptions = [s for s in self.subscriptions if s.source != source]

    # Some shortcuts for common events
    def create_event(self, action, datatype, item, source, Id=None):
        path = f'{action}/{datatype}' + (f'/{item.Id}' if Id else '')
        self.trigger_event(path, source, item=item)
    def add_data(self, item, source):
        self.create_event('add', type(item).__name__, item, source)
    def update_data(self, item, source):
        self.create_event('update', type(item).__name__, item, source, getattr(item, 'Id', False))
    def delete_data(self, item, source):
        self.create_event('delete', type(item).__name__, item, source, getattr(item, 'Id', False))
