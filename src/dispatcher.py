
from dataclasses import dataclass
from typing import Callable, Any
from fnmatch import fnmatch
from weakref import ref

@dataclass
class EventSubscription:
    path: str
    source: Any
    callback: Callable[[], None]

class EventDispatcher:
    def __init__(self):
        self.subscriptions: EventSubscription = []
    def trigger_event(self, event_name, source, **details):
        for sub in self.subscriptions:
            if fnmatch(event_name, sub.path):
                s = sub.source()
                if s is None:
                    self.unbind(sub.source)
                    continue
                # Do not forward an object its own events.
                if s != ref(source):
                    sub.callback(event_name, **details)
    def bind(self, event_name, source, cb, action=None, Id=None):
        sub = EventSubscription(event_name, ref(source), cb)
        self.subscriptions.append(sub)
    def unbind(self, source):
        if not isinstance(source, ref):
            source = ref(source)
        self.subscriptions = [s for s in self.subscriptions if s.source != source]

    # Some shortcuts for common events
    def create_event(self, action, datatype, item, source):
        path = f'{action}/{datatype}' + (f'/{item.Id}' if getattr(item, 'Id', False) else '')
        self.trigger_event(path, source, item=item)
    def add_data(self, item, source):
        self.create_event('add', type(item).__name__, item, source)
    def update_data(self, item, source):
        self.create_event('update', type(item).__name__, item, source)
    def delete_data(self, item, source):
        self.create_event('delete', type(item).__name__, item, source)

