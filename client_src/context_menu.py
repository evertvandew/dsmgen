
from typing import Dict, Callable, Union

from browser import html, console, bind, document

context_menu_name = 'ContextMenu'


def mk_menu_item(text, action, close_func):
    def onSelect(ev):
        ev.stopPropagation()
        ev.preventDefault()
        close_func()
        action(ev)

    item = html.LI(text, data_text=text)
    item.bind('click', onSelect)
    return item

def mk_context_menu(**sections):
    if context_menu_name in document:
        del document[context_menu_name]
    d = html.DIALOG(id=context_menu_name)

    menu = html.UL(Class='contextmenu')
    for section, items in sections.items():
        _ = menu <= html.HR()
        menu_section = html.LI(section)
        if isinstance(items, dict):
            _ = menu_section <= html.UL([mk_menu_item(name, cb, d.close) for name, cb in items.items()])
            _ = menu <= menu_section
        else:
            _ = menu <= mk_menu_item(section, items, d.close)

    _ = d <= menu
    return d

