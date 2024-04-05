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
from typing import Optional, Callable
from browser import document, html, bind, window

header_cls = "tabview-header"
body_cls = "tabview-body"


class Closeable:
    def close(self):
        raise NotImplementedError()

class TabView:
    def __init__(self, parent):
        self.container = document[parent]
        c = self.container
        self.header = html.DIV(Class=header_cls)
        self.body = html.DIV(Class=body_cls)
        c <= self.header
        c <= self.body
        self.current_page: Optional[Closeable] = None
        self.current_diagram: Optional[Closeable] = None

    def add_page(self, title, page, diagram: Closeable = None):
        new_header = html.SPAN(title, Class='tab')
        btn = html.SPAN(Class='fa fa-times', style='background-color:red;color:white')
        new_header <= btn
        self.header <= new_header
        self.body <= page

        @bind(btn, 'click')
        def onClose(evt):
            nonlocal new_header, page
            evt.preventDefault()
            evt.stopPropagation()
            page.remove()
            if diagram != None:
                diagram.close()
            current_tabs = self.header.select('.tab')
            current_index = current_tabs.index(new_header)
            new_header.remove()
            current_tabs = self.header.select('.tab')
            # If no other tabs exist, we are done.
            if not current_tabs:
                return

            # Click the tab to the left of the existing tab to activate it.
            new_index = min([current_index-1, 0])
            evt = window.MouseEvent.new("click")
            current_tabs[new_index].dispatchEvent(evt)

        @bind(new_header, 'click')
        def onActivate(evt: Optional):
            nonlocal new_header, page
            if self.current_page:
                self.current_page.style.display = 'none'
            self.current_page = page
            self.current_page.style.display = 'block'
            for t in self.header.select('.tab-active'):
                t.classList.remove('tab-active')
            new_header.classList.add('tab-active')
            self.current_diagram = diagram

        # Display the page and hide the others.
        onActivate(None)
