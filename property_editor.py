from browser import document, console, html, bind
from browser.widgets.dialog import Dialog, EntryDialog, InfoDialog
import enum
import diagrams
from dataclasses import fields, MISSING
from typing import Hashable
import json

diagrams.createDiagram("canvas", "properties");

type2HtmlInput = {
        float: {'type': 'number', 'step': 'any'},
        str: {'type': 'text'},
        int: {'type': 'number', 'step': 1},
        diagrams.HIDDEN: {'type': 'hidden'}
    }

def isEditable(field):
    return issubclass(field.type, enum.IntEnum) or isinstance(field.type, Hashable) and field.type in type2HtmlInput

def isPortCollection(field):
    if not isinstance(field.type, list):
        return False
    return all(issubclass(t, diagrams.CP) for t in field.type)

def getInputForField(o, field):
    if issubclass(field.type, enum.IntEnum):
        input = html.SELECT(id=f"edit_{field.name}", name=field.name)
        value = getattr(o, field.name) if o else ''
        for option in field.type:
            if value == option:
                input <= html.OPTION(option.name, value=option.value, selected=1)
            else:
                input <= html.OPTION(option.name, value=option.value)
        return input
    if field.type in type2HtmlInput:
        input = html.INPUT(id=f"edit_{field.name}", name=field.name, value=getattr(o, field.name) if o else '', **type2HtmlInput[field.type])
        input.className = 'form-control'
        return input


def createFromValue(t):
    if issubclass(t, enum.IntEnum):
        return lambda x: t(int(x))
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




def createPortEditor(o, field):
    div = html.DIV()
    table = html.TABLE()
    table.className = 'porttable'
    div <= html.H3(field.name) + '\n' + table

    def bindRowToEditor(row, item, delete):
        row.bind('click', lambda ev: editDialog(item))
        delete.bind('click', lambda ev: (confirmDeleteDialog(item, row), ev.stopPropagation()))

    def fillTable():
        table.clear()
        sorted_ports = sorted(getattr(o, field.name), key = lambda p: 100*p.orientation.value + p.order)
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
            d.close()


    def editDialog(current=None):
        is_add = current is None
        d = Dialog("Test", ok_cancel=True)

        style = dict(textAlign="center", paddingBottom="1em")

        # Determine which possible fields are available
        # We make a single dict of all editable options.
        all_editables = {}
        port_selector = html.SELECT()
        for i, port_class in enumerate(field.type):
            port_selector <= html.OPTION(port_class.__name__, value=i)
            all_editables.update({f.name: f for f in fields(port_class) if isEditable(f)})

        d.panel <= html.LABEL("Port type:") + port_selector + html.BR()

        if is_add:
            # Create some sensible defaults
            current = createDefault(port_class)

        for k, edit_type in all_editables.items():
            d.panel <= html.LABEL(k) + getInputForField(current, edit_type) + html.BR()

        converters = {k: createFromValue(t.type) for k, t in all_editables.items()}

        # Event handler for "Ok" button
        @bind(d.ok_button, "click")
        def ok(ev):
            """InfoDialog with text depending on user entry, at the same position as the
            original box."""
            port_type = field.type[int(port_selector.value)]
            if not is_add:
                port_index = getattr(o, field.name).index(current)

            values = {k: converters[k](d.panel.select_one(f'#edit_{k}').value) for k in all_editables}
            for k, v in values.items():
                setattr(current, k, v)

            if is_add:
                getattr(o, field.name).append(current)
            else:
                getattr(o, field.name)[port_index] = current

            d.close()
            fillTable()

    def onAdd(ev):
        editDialog()

    fillTable()
    addb = html.BUTTON("+", type="button")
    addb.bind("click", onAdd)
    div <= addb
    return div

# Add the logic to edit parameters
# When a block is selected, the canvas throws an event with the details
def dataClassEditor(objecttype, defaults=None, update=None):
    # Use the annotations to create the properties editor
    form = html.FORM()

    o = objecttype

    editable_fields = [f for f in fields(objecttype) if f.name not in ['x', 'y', 'height', 'width'] and isEditable(f)]

    for field in editable_fields:
        label = html.LABEL(field.name)
        label.className ="col-sm-3 col-form-label"
        form <= label
        form <= getInputForField(o, field)
        form <= html.BR()

    port_fields = [f for f in fields(o) if isPortCollection(f)]
    for field in port_fields:
        form <= createPortEditor(o, field)

    # Add a SAVE button
    def onSave(_):
        # Because this is a Closure, we can use the captured variables
        # Get the new values for the editable fields
        update_data = {}
        for field in editable_fields:
            # Use the standard constructor for the type to do the conversion
            update_data[field.name] = field.type(document[f'edit_{field.name}'].value)
        if callable(update):
            update(json.dumps(update_data))

    b = html.BUTTON("Save", type="button")
    b.className = "btn btn-primary"
    b.bind("click", onSave)
    return form, b
