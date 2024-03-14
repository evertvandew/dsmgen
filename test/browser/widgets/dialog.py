
from typing import Iterable
from browser import document
from browser.html import DIALOG, DIV, BUTTON

class Dialog(DIV):
    def __init__(self, title, *, top=None, left=None, default_css=True, ok_cancel=False):
        super().__init__(Class='brython-dialog-main')
        self.panel = DIV(Class='brython-dialog-panel')
        self <= self.panel
        if ok_cancel is True:
            self.ok_button = BUTTON(text='OK', Class='brython-dialog-button')
            self <= self.ok_button
            self <= BUTTON(text='Cancel', Class='brython-dialog-button')
        elif isinstance(ok_cancel, Iterable) and len(ok_cancel) == 2:
            self.ok_button = BUTTON(text=ok_cancel[0], Class='brython-dialog-button')
            self <= self.ok_button
            self <= BUTTON(text=ok_cancel[1], Class='brython-dialog-button')
        # Ensure the dialog is in the DOM
        document <= self

    def tagname(self):
        return DIV.__name__

    def close(self):
        self.remove()

class EntryDialog(Dialog):
    def __init__(self, title, message=None, *, top=None, left=None, default_css=True, ok=True):
        super().__init__(title)

class InfoDialog(Dialog):
    def __init__(self, title, message, *, top=None, left=None, default_css=True, remove_after=None, ok=False):
        super().__init__(title)
