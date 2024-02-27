from browser import document, console, html, bind
from browser.widgets.dialog import Dialog, EntryDialog, InfoDialog
import enum
import diagrams
from dataclasses import fields, MISSING, dataclass, Field
from typing import Hashable, Dict, Any, List, Optional
import json
from svg_shapes import HAlign, VAlign
from shapes import HIDDEN
from data_store import DataStore, ExtendibleJsonEncoder, parameter_spec, parameter_values
from modeled_shape import ModeledShape, ModelEntity, EditableParameterDetails

#diagrams.createDiagram("canvas");


class longstr(str): pass

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
        return lambda v: t(int(v if v else 0))
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

def isStylable(objecttype):
    return hasattr(objecttype, 'getStyleKeys')

def getInputForValue(name: str, field_type: type, value: Any):
    if isinstance(field_type, type) and issubclass(field_type, enum.IntEnum):
        input = html.SELECT(id=f"edit_{name}", name=name)
        for option in field_type:
            if value == option:
                input <= html.OPTION(option.name, value=option.value, selected=1)
            else:
                input <= html.OPTION(option.name, value=option.value)
        return input
    if field_type == longstr:
        value = value_formatter[field_type](getattr(o, name) if o else '')
        input = html.TEXTAREA(id=f"edit_{name}", name=name)
        input <= value
        input.className = 'form-control'
        return input
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

def getInputForField(o: dataclass, field: Field):
    """ Determine the right edit widget to use for a specific field description.
        The field is an instance of
    """
    return getInputForValue(field.name, field.type, getattr(o, field.name, None) if o else '')


def getInputForStyle(o: Any, key, value):
    """ Determine an appropriate edit widget for a specific style item. """
    if 'color' in key:
        return html.INPUT(id=f"styling_{key}", name=key, value=value, type='color')
    if 'align' in key:
        t = {'halign': HAlign, 'valign': VAlign}[key]
        input = html.SELECT(id=f"styling_{key}", name=key)
        value = int(value)
        for option in t:
            if value == option:
                input <= html.OPTION(option.name, value=option.value, selected=1)
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


def createPortEditor(o, field, port_types, data_store: DataStore):
    div = html.DIV()
    table = html.TABLE()
    table.className = 'porttable'
    div <= html.H3(field.name) + '\n' + table

    def bindRowToEditor(row, item, delete):
        row.bind('click', lambda ev: editDialog(item))
        delete.bind('click', lambda ev: (confirmDeleteDialog(item, row), ev.stopPropagation()))

    def fillTable():
        table.clear()
        sorted_ports = sorted(getattr(o, field.name), key = lambda p: 100*int(p.orientation) + p.order)
        for item in sorted_ports:
            row = html.TR()
            for f in fields(item):
                row <= html.TD(str(getattr(item, f.name)))
            # Add a delete button for each port
            delete = html.BUTTON('X', style="background-color:red; color:white", type='button')
            row <= delete
            table <= row
            bindRowToEditor(row, item, delete)

    def confirmDeleteDialog(item, row):
        d = Dialog("Test", ok_cancel=('Yes', 'No'))
        d.panel <=  "Delete this port?"

        @bind(d.ok_button, "click")
        def yes(ev):
            """ Delete the item """
            getattr(o, field.name).remove(item)
            row.remove()
            data_store.update_data(o, div)
            d.close()


    def editDialog(current):
        d = Dialog("Test", ok_cancel=True)

        style = dict(textAlign="center", paddingBottom="1em")

        # Determine which possible fields are available
        # We make a single dict of all editable options.
        all_editables = {f.name: f for f in fields(current) if isEditable(f)}

        for k, edit_type in all_editables.items():
            d.panel <= html.LABEL(k) + getInputForField(current, edit_type) + html.BR()

        converters = {k: createFromValue(t.type) for k, t in all_editables.items()}

        # Event handler for "Ok" button
        @bind(d.ok_button, "click")
        def ok(ev):
            """InfoDialog with text depending on user entry, at the same position as the
            original box."""
            port_index = getattr(o, field.name).index(current)
            values = {k: converters[k](d.panel.select_one(f'#edit_{k}').value) for k in all_editables}
            for k, v in values.items():
                setattr(current, k, v)

            getattr(o, field.name)[port_index] = current
            data_store.update_data(o, div)

            d.close()
            fillTable()

    def onAdd(ev):
        """ If there is a choice, select the type of port. """
        if len(port_types) == 1:
            # Just add the new port to the block and be done with it.
            # Use the default values for each of the attributes of the port.
            getattr(o, field.name).append(port_types[0]())
            return

        # We need to select what type of port we want to add.
        d = Dialog("Test", ok_cancel=True)

        style = dict(textAlign="center", paddingBottom="1em")

        # Determine which possible fields are available
        # We make a single dict of all editable options.
        port_selector = html.SELECT()
        for i, port_class in enumerate(port_types):
            port_selector <= html.OPTION(port_class.__name__, value=i)

        d.panel <= html.LABEL("Port type:") + port_selector

        # Event handler for "Ok" button
        @bind(d.ok_button, "click")
        def ok(ev):
            # Determine what type the user selected
            index = int(port_selector.value)
            # Add a new instance to the block filled with detail values
            getattr(o, field.name).append(port_types[index]())
            data_store.update_data(o, div)
            d.close()
            fillTable()


    fillTable()
    addb = html.BUTTON("+", type="button")
    addb.bind("click", onAdd)
    _ = div <= addb
    return div


def dataClassEditorForm(o: ModelEntity, editable_fields: List[EditableParameterDetails], data_store: DataStore):
    """ Return a form for editing the values in a data object, without buttons. """
    # Use the annotations to create the properties editor
    form = html.FORM()

    for field in editable_fields:
        label = html.LABEL(field.name)
        label.className ="col-sm-3 col-form-label"
        _ = form <= label
        _ = form <= getInputForField(o, field)
        _ = form <= html.BR()

    port_types = o.get_allowed_ports() if o else []
    if port_types:
        f = [f for f in fields(o) if f.name == 'ports'][0]
        _ = form <= createPortEditor(o, f, port_types, data_store)
    return form

def stylingEditorForm(o: ModeledShape):
    # Add an editor for style elements
    form = html.FORM()
    if isStylable(o):
        _ = form <= html.H3("Styling")
        style_keys = o.getStyleKeys()
        for key in style_keys:
            label = html.LABEL(key)
            label.className = "col-sm-3 col-form-label"
            _ = form <= label
            _ = form <= getInputForStyle(o, key, o.getStyle(key, ''))
            _ = form <= html.BR()
    return form

def getFormValues(form, o: Optional[ModelEntity], editable_fields: List[EditableParameterDetails]):
    """ Returns a dictionary with the current values in the form edits. """
    console.log(f"Form: {form}")
    update_data = {}
    for field in editable_fields:
        # Use the standard constructor for the type to do the conversion
        constructor = type2Constructor(field.type)
        update_data[field.name] = constructor(form.select_one(f'#edit_{field.name}').value)

    if isStylable(o):
        defaults = o.getDefaultStyle()
        new_style = {key: createFromValue(type(default))(document[f'styling_{key}'].value) for key, default in defaults.items()}
        update_data['styling'] = new_style

    return update_data


# Add the logic to edit parameters
# When a block is selected, the canvas throws an event with the details
def dataClassEditor(o: Optional[ModelEntity], parameters: List[EditableParameterDetails], data_store: DataStore, update=None):
    """ Create a detail-editor, with a save button for the user to click..
        o: Optional object with the current values of the fields.
        parameters: List of descriptors of all the fields.
        data_store: REST api client that persists the object being edited / created.
    """
    form = dataClassEditorForm(o, parameters, data_store)
    # Add a SAVE button
    def onSave(_):
        # Because this is a Closure, we can use the captured variables
        # Get the new values for the editable fields
        update_data = getFormValues(form, o, parameters)
        if callable(update):
            update(json.dumps(update_data, cls=ExtendibleJsonEncoder))

    b = html.BUTTON("Save", type="button")
    b.className = "btn btn-primary"
    b.bind("click", onSave)
    return form, b
