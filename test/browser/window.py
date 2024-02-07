
from .events import Event


class CustomEvent(Event):
    @property
    def type(self):
        return self.custom_type
    @type.setter
    def type(self, value):
        self.custom_type = value
    @staticmethod
    def new(name, details) -> Event:
        ev = CustomEvent(**details)
        ev.type = name
        return ev
