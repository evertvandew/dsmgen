"""
A helper file for the Brython mockup, for inserting the JavaScript events.
"""
import enum

from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class Event:
    target: 'tag' = None
    srcElement: 'tag' = None
    detail: Any = ''
    bubbles: bool = True

    @property
    def type(self):
        return type(self).__name__.lower()

    def __post_init__(self):
        self.cancelBubble: bool = False

    def preventDefault(self):
        # Default actions for each element are not supported by this simulator.
        # If you do want such detailed simulations, just run the actual client and control it through Selenium
        pass
    def stopPropagation(self):
        self.cancelBubble = True

@dataclass
class MouseEvent(Event):
    altKey: bool = False
    buttons: int = 0    # Mask for buttons. bit 1: left, 2: right, 4: wheel/middle, 8: browser back, 16: forward
    offsetX: float = 0.0    # Relative to the event target
    offsetY: float = 0.0    # Relative to the event target
    ctrlKey: bool = False
    detail: str = ''
    metaKey: bool = False
    relatedTarget: 'tag' = None
    shiftKey: bool = False
    key: str = ''

    @property
    def button(self):
        if self.buttons & 1:
            return 0
        if self.buttons & 2:
            return 2
        if self.buttons & 4:
            return 1
        return 0

    @property
    def clientX(self):
        return self.offsetX
    @property
    def clientY(self):
        return self.offsetY
    @property
    def screenX(self):
        return self.offsetX
    @property
    def screenY(self):
        return self.offsetY

class Click(MouseEvent): pass
class ContextMenu(MouseEvent): pass
class DblClick(MouseEvent): pass
class MouseDown(MouseEvent): pass
class MouseEnter(MouseEvent): pass
class MouseLeave(MouseEvent): pass
class MouseMove(MouseEvent): pass
class MouseOut(MouseEvent): pass
class MouseOver(MouseEvent): pass
class MouseUp(MouseEvent): pass
class KeyDown(MouseEvent): pass
class KeyUp(MouseEvent): pass

@dataclass
class DragDataTransfer:
    effectAllowed: str = ''
    dropEffect: str = ''
    data: Dict[str, str] = field(default_factory=dict)

    def setData(self, key: str, value: str):
        self.data[key] = value
    def getData(self, key: str) -> str:
        return self.data[key]

@dataclass
class DragDropEvent(MouseEvent):
    dataTransfer: DragDataTransfer = field(default_factory=DragDataTransfer)

class Drag(DragDropEvent): pass
class DragEnd(DragDropEvent): pass
class DragEnter(DragDropEvent): pass
class DragLeave(DragDropEvent): pass
class DragOver(DragDropEvent): pass
class DragStart(DragDropEvent): pass
class Drop(DragDropEvent): pass
