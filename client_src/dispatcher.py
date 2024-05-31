"""
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
from dataclasses import dataclass
from typing import Callable, Any, Dict, Optional, List
from fnmatch import fnmatch
from browser import console

@dataclass
class EventSubscription:
    """ Stores the details for a subscription: the filter that is applied, the callback to call and any context for
        calling the function.
    """
    path: str
    target: Any
    callback: Callable[[str, Any, "EventDispatcher", Dict], None]
    context: Optional[Dict]


class EventDispatcher:
    def __init__(self):
        self.subscriptions: List[EventSubscription] = []
    def trigger_event(self, event_name, source, **details):
        for sub in self.subscriptions:
            if fnmatch(event_name, sub.path):
                details['target'] = sub.target
                details['data_store'] = self
                details['context'] = sub.context
                sub.callback(event_name, source, self, details)

    def subscribe(self, event_name: str, source: Optional[Any], cb: Callable, context: Optional[Any]=None) -> None:
        """
        Subscribe to one or more events. A callback is called whenever am event it triggered that matches the filter.
        Event names are built up like this: <action>/<datatype>[/<id>]
        The action is one of add, update and delete.
        The datatype is the classname of the event source.
        The id is optional, it is not set for the add event but set for the others.

        :param event_name: A path describing the exact event. Wildcards are allowed.
        :param source: Optional Object that is monitored
        :param cb: Called when an event is triggered that matches the filter. This can not be a bound function or
               a closure. Use the optional context instead. The context is stored with a weakref, so it doesn't
               prevent listeners from being cleaned up.
        :param context: Optional context supplied with the callback
        """
        # Do not accept bound functions, as these prevent objects from being garbage collected.
        assert getattr(cb, 'im_self', None) is None, "Member functions are not supported"
        sub = EventSubscription(event_name, source, cb, context)
        self.subscriptions.append(sub)

    def unsubscribe(self, target):
        self.subscriptions = [s for s in self.subscriptions if s.target != target]

    # Some shortcuts for common events
    def create_event(self, action, datatype, source, Id=None):
        path = f'{action}/{datatype}' + (f'/{source.Id}' if Id else '')
        self.trigger_event(path, source)
    def add_data(self, item):
        self.create_event('add', type(item).__name__, item)
    def update_data(self, item):
        console.log(f"CREATING UPDATE EVENT {item}")
        self.create_event('update', type(item).__name__, item, getattr(item, 'Id', False))
    def delete_data(self, item):
        self.create_event('delete', type(item).__name__, item, getattr(item, 'Id', False))

