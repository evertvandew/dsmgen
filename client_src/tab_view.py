
from typing import Optional, Callable
from browser import document, html, bind

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

            # Click the tab to the right (or left if none exists) the existing tab.
            new_index = current_index if current_index < len(current_tabs) else len(current_tabs)-1
            current_tabs[new_index]


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
