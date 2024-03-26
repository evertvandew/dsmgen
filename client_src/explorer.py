
from browser import html, console, bind, document
from browser.widgets.dialog import Dialog, EntryDialog, InfoDialog

from typing import Type
from data_store import DataStore, ExtendibleJsonEncoder, StorableElement
import json

from property_editor import dataClassEditorForm, getFormValues
from modeled_shape import ModelEntity, ModelRepresentation

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
            ev.stopPropagation()
            ev.preventDefault()
            document[context_menu_name].close()
            d = Dialog(f'Delete {type(data_element).__name__}', ok_cancel=True)
            _ = d.panel <= f'Delete {type(data_element).__name__} "{data_element.name}"'

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
            parameters = default_obj.get_editable_parameters()
            _ = d.panel <= dataClassEditorForm(None, parameters, api)

            @bind(d.ok_button, 'click')
            def on_ok(ev):
                data = getFormValues(d.panel, etype, parameters)
                new_object = etype(parent=parent, **data)
                api.add(new_object)
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
            _ =createmenu <= html.UL([bind_add_action(t) for t in create])
            menu = html.UL(Class='contextmenu')
            _ = menu <= createmenu
            _ = menu <= html.HR()
            _ = menu <= mk_menu_item('Rename', on_rename)
            _ = menu <= html.HR()
            _ = menu <= mk_menu_item('Remove', on_delete)
            #d = Dialog("", ok_cancel=True)
            if context_menu_name in document:
                del document[context_menu_name]
            d = html.DIALOG(id=context_menu_name)
            _ = d <= menu
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
        if isinstance(source, ModelRepresentation) or not hasattr(source, 'parent'):
            return
        assert source.Id
        # Exclude records that are already in the hierarchy
        if holder.select(f'[data-modelid="{source.Id}"]'):
            return
        # Find the insertion point for the new record
        if source.parent:
            parent = holder.select_one(f'[data-modelid="{source.parent}"]').parent.parent
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
