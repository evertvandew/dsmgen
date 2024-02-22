
from browser import html, console, bind, document
from browser.widgets.dialog import Dialog, EntryDialog, InfoDialog

from typing import List, Dict, Any, Type
from dataclasses import asdict
from data_store import DataStore, ExtendibleJsonEncoder
import json

from property_editor import dataClassEditorForm, getFormValues
from modeled_shape import ModelEntity

line_cls = 'eline'
name_cls = 'ename'


class Element: pass


context_menu_name = 'ContextMenu'

def toggle_caret(ev):
    ev.stopPropagation()
    ev.preventDefault()
    c = ev.target
    holder = c.parent.parent
    children = holder.select(f'.{line_cls}')
    if 'fa-caret-right' in list(c.classList):
        c.classList.remove('fa-caret-right')
        c.classList.add('fa-caret-down')
        for child in children:
            child.style['display'] = 'block'
    else:
        c.classList.add('fa-caret-right')
        c.classList.remove('fa-caret-down')
        for child in children:
            child.style['display'] = 'none'


def format_name(name):
    """ Do additional formatting for a name displayed in the explorer """
    return f' &mdash; {name}'


def make_explorer(holder, api: DataStore, allowed_children):
    def bind_events(data_element, html_element):
        @bind(html_element, 'click')
        def clickfunc(ev):
            api.trigger_event('click', source=html_element, target_dbid=data_element.Id,
                              target_type=type(data_element).__name__, data_element=data_element)
            ev.stopPropagation()
            ev.preventDefault()

        @bind(html_element, 'dblclick')
        def clickfunc(ev):
            api.trigger_event('dblclick', source=html_element, target_dbid=data_element.Id, target_type=type(data_element).__name__)
            ev.stopPropagation()
            ev.preventDefault()

        @bind(html_element, 'dragstart')
        def ondragstart(ev):
            ev.dataTransfer.setData('entity', json.dumps(data_element, cls=ExtendibleJsonEncoder))
            console.log(f'Entity being dragged: {data_element}')
            console.log(f'JSON: {json.dumps(data_element, cls=ExtendibleJsonEncoder)}')
            ev.dataTransfer.effectAllowed = 'move'
            ev.stopPropagation()

        @bind(html_element, 'dragover')
        def ondragover(ev):
            ev.dataTransfer.dropEffect = 'move'
            ev.preventDefault()

        @bind(html_element, 'drop')
        def onDrop(ev):
            # Check the right data is submitted
            assert ev.dataTransfer
            json_string = ev.dataTransfer.getData('entity')
            if not json_string:
                console.log('No data was submitted in the drop')
                return
            data = json.loads(json_string)
            # Ask the user if this is what he intends to do
            dialog = Dialog("Please Confirm", ok_cancel=True)
            dialog.panel <= f"Do you want to move {data.get('name')} to inside {data_element.name}?"

            @bind(dialog.ok_button, "click")
            def entry(ev):
                dialog.close()
                # Add the object to the new parent
                instance = api.get(data['__classname__'], data['Id'])
                instance.parent=data_element.Id
                api.update(instance)
                # Re-create the hierarchy
                holder.clear()
                api.get_hierarchy(start)

        def on_delete(ev):
            ev.stopPropagation()
            ev.preventDefault()
            document[context_menu_name].close()
            d = Dialog(f'Delete {type(data_element).__name__}', ok_cancel=True)
            d.panel <= f'Delete {type(data_element).__name__} "{data_element.name}"'

            @bind(d.ok_button, "click")
            def ok(ev):
                result = api.delete(data_element)
                d.close()
                if result:
                    del document[data_element.Id]
                    msg = InfoDialog('Success', f'{data_element.name} was deleted', ok='Close')
                else:
                    msg = InfoDialog('Failure', f'Could not delete "{data_element.name}"', ok='Close')

        def on_rename(ev):
            ev.stopPropagation()
            ev.preventDefault()
            document[context_menu_name].close()
            d = EntryDialog(f'Rename {type(data_element).__name__}', 'new name:')

            @bind(d, "entry")
            def on_ok(ev):
                data = d.value
                api.update(data_element)
                spans = html_element.select('.ename')
                for span in spans:
                    span.html = format_name(data)
                d.close()

        def on_add(ev, etype: Type[ModelEntity], parent):
            ev.stopPropagation()
            ev.preventDefault()
            document[context_menu_name].close()
            default_obj = etype()
            d = Dialog(f'Add {etype.__name__}', ok_cancel=True)
            d.panel <= dataClassEditorForm(None, default_obj.get_editable_parameters(), api)

            @bind(d.ok_button, 'click')
            def on_ok(ev):
                data = getFormValues(d.panel, etype)
                new_object = etype(parent=parent, **data)
                api.add(new_object)
                html = render_hierarchy([new_object])
                html_element <= html
                d.close()

        def mk_menu_item(text, action):
            item = html.LI(text)
            item.bind('click', action)
            return item

        def bind_add_action(item):
            return mk_menu_item(item.__name__, lambda ev: on_add(ev, item, data_element.Id))

        @bind(html_element, 'contextmenu')
        def contextfunc(ev):
            create = allowed_children[type(data_element)]
            ev.stopPropagation()
            ev.preventDefault()
            createmenu = html.LI('Create')
            createmenu <= html.UL([bind_add_action(t) for t in create])
            menu = html.UL(Class='contextmenu')
            menu <= createmenu
            menu <= html.HR()
            menu <= mk_menu_item('Rename', on_rename)
            menu <= html.HR()
            menu <= mk_menu_item('Remove', on_delete)
            #d = Dialog("", ok_cancel=True)
            if context_menu_name in document:
                del document[context_menu_name]
            d = html.DIALOG(id=context_menu_name)
            d <= menu
            html_element <= d
            d.showModal()

    def render_hierarchy(data_list):
        results = []
        for element in data_list:
            # Check if the caret is needed
            de = html.DIV()
            icon = element.get_icon()
            if (children := getattr(element, 'children', None)) is not None:
                de <= html.SPAN(Class="caret fa fa-caret-right", style={"width": "1em"})
            descriptor = html.SPAN(Class="description", draggable="true")
            descriptor <= html.SPAN(Class=f"fa fa-{icon}", style={"margin-left":"1em"})
            descriptor <= html.SPAN(format_name(getattr(element, 'name', type(element).__name__)), Class=name_cls)
            de <= descriptor

            d = html.DIV(de, Class=line_cls, id=element.Id)
            d.value = element

            bind_events(element, descriptor)

            if children:
                ch = render_hierarchy(element.children)
                for c in ch:
                    c.style['display'] = 'none'
                d <= ch
            results.append(d)

            for c in de.select('.caret'):
                c.bind('click', toggle_caret)

        return results

    def start(elements):
        holder <= render_hierarchy(elements)

    api.get_hierarchy(start)

