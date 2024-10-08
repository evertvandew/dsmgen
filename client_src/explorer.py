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
from browser import html, console, bind, document
from browser.widgets.dialog import Dialog, EntryDialog, InfoDialog

from typing import Type
from data_store import DataStore, ExtendibleJsonEncoder, StorableElement
import json

from property_editor import getDetailsPopup, toggle_caret, name_cls, line_cls
from modeled_shape import ModelEntity, ModelRepresentation
from context_menu import mk_context_menu


class Element: pass

def format_name(name):
    """ Do additional formatting for a name displayed in the explorer """
    return f' — {name}'


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
            _ = dialog.panel <= f"Do you want to move {data.get('name')} to inside {data_element.name}?"

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
            d = Dialog(f'Delete {type(data_element).__name__}', ok_cancel=True)
            @bind(d.ok_button, "click")
            def ok(ev):
                result = api.delete(data_element)
                d.close()
                if result:
                    del document[data_element.Id]
                else:
                    msg = InfoDialog('Failure', f'Could not delete "{data_element.name}"', ok='Close')

        def on_rename(ev):
            d = EntryDialog(f'Rename {type(data_element).__name__}', 'new name:')

            @bind(d, "entry")
            def on_ok(ev):
                data = d.value
                api.update(data_element)
                spans = html_element.select('.ename')
                for span in spans:
                    span.html = format_name(data)
                d.close()

        def on_add(ev, cls: Type[ModelEntity], parent):
            def callback(data):
                new_object = cls(parent=parent, **data)
                api.add_complex(new_object)
            getDetailsPopup(cls, callback)
        def bind_add_action(item):
            return item.__name__, lambda ev: on_add(ev, item, data_element.Id)

        @bind(html_element, 'contextmenu')
        def contextfunc(ev):
            ev.stopPropagation()
            ev.preventDefault()

            create = allowed_children[type(data_element)]

            d = mk_context_menu(
                create=dict(bind_add_action(c) for c in create),
                rename=on_rename,
                remove=on_delete
            )
            _ = html_element <= d
            d.showModal()

    def render_hierarchy(data_list):
        results = []
        for element in data_list:
            # Check if the caret is needed
            de = html.DIV()
            icon = element.get_icon()
            if (children := getattr(element, 'children', None)) is not None:
                _ = de <= html.SPAN(Class="caret fa fa-caret-right", style={"width": "1em"})
            descriptor = html.SPAN(Class="description", draggable="true", data_modelid=str(element.Id),
                                   data_modelcls=type(element).__name__)
            _ = descriptor <= html.SPAN(Class=f"fa fa-{icon}", style={"margin-left":"1em"})
            _ = descriptor <= html.SPAN(format_name(getattr(element, 'name', type(element).__name__)), Class=name_cls)
            _ = de <= descriptor

            d = html.DIV(de, Class=line_cls, id=element.Id)
            d.value = element

            bind_events(element, descriptor)

            if children:
                ch = render_hierarchy(element.children)
                for c in ch:
                    c.style['display'] = 'none'
                _ = d <= ch
            results.append(d)

            for c in de.select('.caret'):
                c.bind('click', toggle_caret)

        return results

    def start(elements):
        _ = holder <= render_hierarchy(elements)

    def onAdd(event, source: StorableElement, ds, details):
        """ Add new elements to the explorer as the user creates them in diagrams or the property editor.
        """
        # Exclude representation records and records without a `parent` field.
        if isinstance(source, ModelRepresentation) or not hasattr(source, 'parent') or not source.get_parent():
            return
        assert source.Id
        # Exclude records that are already in the hierarchy
        if holder.select(f'[data-modelid="{source.Id}"]'):
            return
        # Find the insertion point for the new record
        if source.get_parent():
            model_parent_tag = holder.select_one(f'[data-modelid="{source.get_parent()}"]')
            if not model_parent_tag:
                return
            parent = model_parent_tag.parent.parent
        else:
            parent = holder
        # Add the new element
        _ = parent <= render_hierarchy([source])

    def onUpdate(event, source: StorableElement, ds, details):
        """ Update an element in the hierarchy. This code currently can only change the text for the element. """
        # Exclude representation records and records without a `parent` field.
        if isinstance(source, ModelRepresentation) or not hasattr(source, 'parent'):
            return
        # Get hold of the text
        name_field = holder.select_one(f'[data-modelid="{source.Id}"] .{name_cls}')
        if name_field:
            name_field.clear()
            _ = name_field <= format_name(getattr(source, 'name', type(source).__name__))
            pass


    api.get_hierarchy(start)
    api.subscribe('add/*', None, onAdd)
    api.subscribe('update/*', None, onUpdate)
