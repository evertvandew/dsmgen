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
from browser import document, console, html, bind, DOMNode
from browser.widgets.dialog import Dialog
import enum
import diagrams
from dataclasses import fields, MISSING
from typing import Hashable, Dict, Any, List, Optional, Type, Callable
import json

from svg_shapes import HAlign, VAlign
from model_interface import ModelEntity, EditableParameterDetails, PropertyEditable
from shapes import HIDDEN, Stylable
from data_store import DataStore, ExtendibleJsonEncoder, parameter_spec, ReprCategory


line_cls = 'eline'
name_cls = 'ename'


def toggle_caret(ev):
    ev.stopPropagation()
    ev.preventDefault()
    c = ev.target
    holder = c.parent.parent
    #children = holder.select(f'.{line_cls}')
    children = [n for n in holder.childNodes if line_cls in n.classList]
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


def mk_collapsable(heading: str|DOMNode, contents: List[DOMNode], line_id: Optional[int]=None, start_visible=False):
    """ Make contents collapsable. """
    if isinstance(heading, str):
        heading = html.B(heading)
    de = html.DIV()
    dh = html.DIV()
    if start_visible:
        _ = dh <= html.SPAN(Class="caret fa fa-caret-down", style={"width": "1em"})
    else:
        _ = dh <= html.SPAN(Class="caret fa fa-caret-right", style={"width": "1em"})
    _ = dh <= html.SPAN(heading)
    _ = de <= dh
    if line_id:
        d = html.DIV(contents, Class=line_cls, id=line_id)
    else:
        d = html.DIV(contents, Class=line_cls)
    if start_visible:
        d.style['display'] = 'block'
    else:
        d.style['display'] = 'none'
    _ = de <= d

    for c in de.select('.caret'):
        c.bind('click', toggle_caret)

    return de

# Define types that the property editor gives special treatment
class longstr(str): pass
class Color(str): pass

class OptionalRef:
    def __init__(self, t):
        self.type = t
    def __execute__(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            if value in ['None', 'null']:
                return None
        return self.t(value)


type2HtmlInput = {
        float: {'type': 'number', 'step': 'any'},
        str: {'type': 'text'},
        int: {'type': 'number', 'step': 1},
        Dict[str, str]: {'type': 'text'},
        HIDDEN: {'type': 'hidden'},
        parameter_spec: {'type': 'text'}
    }

type2default = {
    float: 0.0,
    str: '',
    int: 0,
    Dict[str, str]: '',
    longstr: '',
    HIDDEN: ''
}


parameter_types = {
    'int': int,
    'float': float,
    'str': str
}


def type2Constructor(t: type):
    """ Find the right constructor for a specific type. The constructor is used to convert the value inside the
        edit field of the property editor, into an instance of this type.
    """
    if t == Dict[str, str]:
        return lambda v: dict([[k.strip() for k in item.split(':')]  for item in v.split(';')])
    elif t == HIDDEN:
        return str
    elif isinstance(t, enum.EnumType):
        return lambda v: t(int(v if v else list(t)[0]))
    elif t == longstr:
        return str
    elif t == int:
        return lambda v: int(v) if v else 0
    return t


# Define a lookup table to convert values to a type the property editor can handle.
value_formatter = {
    float: float,
    str: str,
    int: int,
    longstr: str,
    Dict[str, str]: lambda v: '; '.join(f'{k}:{i}' for k, i in v.items()) if v else '',
    HIDDEN: str,
    parameter_spec: str
}

def isEditable(field):
    """ Return true if a user is allowed to directly edit this value. """
    if field.type is HIDDEN:
        return False
    return ((isinstance(field.type, type) and issubclass(field.type, enum.IntEnum)) or field.type==longstr
            or (isinstance(field.type, Hashable) and field.type in type2HtmlInput) or field.type==parameter_spec)

def isPortCollection(field):
    """ Return true if the field a collection of ports. """
    if not isinstance(field.type, list):
        return False
    return any(isinstance(t, type) and issubclass(t, diagrams.CP) for t in field.type)

def getInputForValue(name: str, field_type: type, value: Any):
    if isinstance(field_type, type) and issubclass(field_type, enum.IntEnum):
        input = html.SELECT(id=f"edit_{name}", name=name)
        for option in field_type:
            if value == option:
                input <= html.OPTION(option.name, value=option.value, selected=1)
                input.value = option.value
            else:
                input <= html.OPTION(option.name, value=option.value)
        return input
    if field_type == longstr:
        v = value_formatter[field_type](value if value else '')
        input = html.TEXTAREA(id=f"edit_{name}", name=name)
        input <= v
        input.className = 'form-control'
        return input
    if field_type == Color:
        return html.INPUT(id=f"edit_{name}", name=name, value=value, type='color')
    if field_type in type2HtmlInput:
        stored_value = value if value is not None else type2default[field_type]
        if stored_value is None or value == '':
            value = ''
        else:
            value = value_formatter[field_type](stored_value)
        input = html.INPUT(id=f"edit_{name}", name=name, value=value, **type2HtmlInput[field_type])
        input.className = 'form-control'
        return input
    console.log(f"Could not determine input for {field_type}")

def getInputForField(field: EditableParameterDetails):
    """ Determine the right edit widget to use for a specific field description.
        The field is an instance of
    """
    return getInputForValue(field.name, field.type, field.current_value)


def getInputForStyle(o: Any, key, value):
    """ Determine an appropriate edit widget for a specific style item. """
    if 'color' in key:
        return html.INPUT(id=f"styling_{key}", name=key, value=value, type='color')
    if 'align' in key:
        t = {'halign': HAlign, 'valign': VAlign}[key]
        input = html.SELECT(id=f"styling_{key}", name=key)
        value = value.value
        for option in t:
            if value == option:
                input <= html.OPTION(option.name, value=option.value, selected=1)
                input.value = option.value
            else:
                input <= html.OPTION(option.name, value=option.value)
        return input
    return html.INPUT(id=f"styling_{key}", name=key, value=value, type='text')


def str2int(x):
    """ Convert a string to an integer. The empty string is mapped to 0. """
    if x:
        return int(x)
    return 0

def createFromValue(t):
    if isinstance(t, type) and issubclass(t, enum.IntEnum):
        return lambda x: t(str2int(x))
    if isinstance(t, type) and issubclass(t, int):
        return str2int
    if str(t) == 'typing.Dict[str, str]':
        return lambda s: {k.strip(): v.strip() for k,v in [l.split(':') for l in s.split(';')]} if s else {}
    return t


def createDefault(dcls):
    """ Create a default value for a dataclass. This also works for dataclasses that have no defaults for fields. """
    default = {}
    for f in fields(dcls):
        if callable(f.default_factory):
            default[f.name] = f.default_factory()
        elif f.default != MISSING:
            default[f.name] = f.default
        elif issubclass(f.type, enum.Enum):
            default[f.name] = list(f.type)[0]
        elif f.type in [int, float]:
            default[f.name] = 0
        else:
            default[f.name] = ''

    return dcls(**default)


def createPortEditor(o: ModelEntity, field, port_types, data_store: DataStore):
    div = html.DIV()
    table = html.TABLE()
    table.className = 'porttable'
    _ = div <= mk_collapsable(field.name, table)

    def bindRowToEditor(row: DOMNode, item: ModelEntity, delete: DOMNode):
        row.bind('click', lambda ev: editDialog(item))
        delete.bind('click', lambda ev: (confirmDeleteDialog(item, row), ev.stopPropagation()))

    def fillTable():
        table.clear()
        sorted_ports: List[ModelEntity] = sorted(data_store.get_ports(o), key = lambda p: 100*int(p.orientation) + p.order)
        for i, item in enumerate(sorted_ports):
            row = html.TR(Class='port_row', data_mid=item.Id)
            for f in item.get_editable_parameters():
                _ = row <= html.TD(str(f.current_value))
            # Add a delete button for each port
            delete = html.BUTTON('X', style="background-color:red; color:white", type='button',
                                 id=f'delete_port_{i}')
            _ = row <= delete
            _ = table <= row
            bindRowToEditor(row, item, delete)

    def confirmDeleteDialog(item, row):
        d = Dialog("Test", ok_cancel=('Yes', 'No'))
        _ = d.panel <=  "Delete this port?"

        @bind(d.ok_button, "click")
        def yes(ev):
            """ Delete the item """
            row.remove()
            data_store.delete(item)
            d.close()


    def editDialog(current: ModelEntity):
        d = Dialog("Test", ok_cancel=True)

        style = dict(textAlign="center", paddingBottom="1em")

        # Determine which possible fields are available
        # We make a single dict of all editable options.
        all_editables = current.get_editable_parameters()

        for f in all_editables:
            _ = d.panel <= html.LABEL(f.name) + getInputForField(f) + html.BR()

        converters = {f.name: createFromValue(f.type) for f in all_editables}

        # Event handler for "Ok" button
        @bind(d.ok_button, "click")
        def ok(ev):
            """InfoDialog with text depending on user entry, at the same position as the
            original box."""
            port_index = data_store.get_ports(o).index(current)
            values = {f.name: converters[f.name](d.panel.select_one(f'#edit_{f.name}').value) for f in all_editables}
            for k, v in values.items():
                setattr(current, k, v)

            data_store.get_ports(o)[port_index] = current
            data_store.update_data(o)

            d.close()
            fillTable()

    def onAdd(ev):
        """ If there is a choice, select the type of port. """
        if len(port_types) == 1:
            # Just add the new port to database, its logic will cause it to be added to relevant collections.
            # Use the default values for each of the attributes of the port.
            data_store.add_complex(port_types[0](parent=o.Id))
            fillTable()
            return

        # We need to select what type of port we want to add.
        d = Dialog("Test", ok_cancel=True)

        style = dict(textAlign="center", paddingBottom="1em")

        # Determine which possible fields are available
        # We make a single dict of all editable options.
        port_selector = html.SELECT(id="port_selector")
        for i, port_class in enumerate(port_types):
            _ = port_selector <= html.OPTION(port_class.__name__, value=i)

        _ = d.panel <= html.LABEL("Port type:") + port_selector

        # Event handler for "Ok" button
        @bind(d.ok_button, "click")
        def ok(ev):
            # Determine what type the user selected
            index = int(port_selector.value)
            # Obtain the ID of the model entity this port is being added to.
            data_store.add_complex(port_types[index](parent=o.Id))
            d.close()
            fillTable()


    fillTable()
    addb = html.BUTTON("+", type="button", id="add_port")
    addb.bind("click", onAdd)
    _ = div <= addb
    return div


def dataClassEditorForm(o: PropertyEditable, editable_fields: List[EditableParameterDetails], data_store: DataStore=None):
    """ Return a form for editing the values in a data object, without buttons. """
    # Use the annotations to create the properties editor
    form = html.FORM()

    for field in editable_fields:
        iff = getInputForField(field)
        if iff:
            de = html.DIV()
            de.className = "mb-3 row"
            label = html.LABEL(field.name)
            label.className = "col-sm-3 col-form-label"
            _ = de <= label
            iff.className = "form-control"
            dc = html.DIV()
            dc.className = 'col-sm-9'
            _ = dc <= iff
            _ = de <= dc
            _ = form <= de

    port_types = o.getModelEntity().get_allowed_ports() if o else []
    if port_types and data_store and ((not o.isStylable()) or o.category != ReprCategory.block_instance):
        f = [f for f in fields(o) if f.name == 'ports'][0]
        _ = form <= createPortEditor(o.getModelEntity(), f, port_types, data_store)
    return form

def stylingEditorForm(o: PropertyEditable):
    # Add an editor for style elements

    parameters = o.get_styling_parameters()
    if not parameters:
        return

    form = html.FORM()
    for field in parameters:
        label = html.LABEL(field.name)
        label.className = "col-sm-3 col-form-label"
        _ = form <= label
        _ = form <= getInputForField(field)
        _ = form <= html.BR()
    return mk_collapsable('Styling', form)

def getFormValues(form, o: Optional[ModelEntity], editable_fields: List[EditableParameterDetails]):
    """ Returns a dictionary with the current values in the form edits. """
    update_data = {}
    for field in editable_fields:
        # Use the standard constructor for the type to do the conversion
        constructor = type2Constructor(field.type)
        update_data[field.name] = constructor(form.select_one(f'#edit_{field.name}').value)

    if o.isStylable():
        defaults = o.getDefaultStyle()
        fields = {key: document.select( f'#edit_{key}') for key in defaults.keys()}
        fields = {k: v[0].value for k, v in fields.items() if v}
        new_style = {key: createFromValue(type(default))(fields.get(key, default))
                     for key, default in defaults.items()}
        update_data['styling'] = new_style

    return update_data


# Add the logic to edit parameters
# When a block is selected, the canvas throws an event with the details
def dataClassEditor(o: PropertyEditable, data_store: DataStore, update=None):
    """ Create a detail-editor, with a save button for the user to click..
        o: object with the current values of the fields.
        parameters: List of descriptors of all the fields.
        data_store: REST api client that persists the object being edited / created.
        update: A function to be called when the user clicks on "save".
    """
    parameters = o.get_editable_parameters()
    editor = html.DIV()
    _ = editor <= mk_collapsable(f'{type(o).__name__}: {getattr(o, "name", "")}',
                                 dataClassEditorForm(o, parameters, data_store), start_visible=True)
    if o.isStylable():
        _ = editor <= stylingEditorForm(o)
    # Add a SAVE button
    def onSave(_):
        # Because this is a Closure, we can use the captured variables
        # Get the new values for the editable fields
        update_data = getFormValues(editor, o, parameters)
        if callable(update):
            update(json.dumps(update_data, cls=ExtendibleJsonEncoder))

    b = html.BUTTON("Save", type="button", id='save_properties')
    b.className = "btn btn-primary"
    b.bind("click", onSave)
    _ = editor <= b
    return editor


def getDetailsPopup(cls: Type[PropertyEditable], cb: Callable):
    default_obj = cls()
    d = Dialog(f'Add {cls.__name__}', ok_cancel=True)
    parameters = default_obj.get_editable_parameters()
    _ = d.panel <= dataClassEditorForm(default_obj, parameters)

    @bind(d.ok_button, 'click')
    def on_ok(ev):
        cb(getFormValues(d.panel, cls, parameters))
        d.close()
