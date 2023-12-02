"""
Visual Modelling client.
"""

<%
"""
    Template for generating the client for the visual modelling environment.
    The tool expects only a definition construct.
    This

    The generated client uses the Brython Python-In-A-Browser technology.
"""

from dataclasses import fields, is_dataclass
import model_definition as mdef

%>

from browser import document, console, html, window, bind, ajax
import json
from explorer import Element, make_explorer, ExplorerDataApi, context_menu_name
from rest_api import ExplorerApi, DiagramApi, ExtendibleJsonEncoder
from dataclasses import dataclass, field, is_dataclass, asdict, fields
from typing import Self, List, Dict, Any, Callable
from collections.abc import Iterable
import typing
import types
from enum import IntEnum
from inspect import getmro
import diagrams
import shapes
from property_editor import dataClassEditor, longstr
from rest_api import IRepresentationSerializer, IClean



# Some mixins to add serialization features
class CleanMonitor(IClean):
    def __init__(self):
        self._dirty = set()
    def mk_dirty_setter(self, k):
        return lambda: self._dirty.add(k)
    def is_dirty(self):
        return bool(self._dirty)
    def set_clean(self):
        self._dirty = set()
    def set_dirty(self, keys):
        self._dirty = set(keys)
    def get_dirty(self):
        return self._dirty
    def clean_keys(self, keys):
        """ Indicate that a particular set of keys has been cleaned. """
        self._dirty = {k for k in self._dirty if k not in keys}

    @classmethod
    def all_annotations(cls):
        for b in getmro(cls):
            if a := getattr(b, '__annotations__', False):
                yield a

    def __setattr__(self, key, value):
        """ Override the method to set attributes, to keep track of internal changes.
        """
        if hasattr(self, '_dirty') and any(key in a for a in self.all_annotations()) and getattr(self, key) != value:
            self._dirty.add(key)
        object.__setattr__(self, key, value)


class EntityReprSerializer(IRepresentationSerializer):
    base_url = f'/data/_BlockRepresentation'

    def new_model_item(self):
        return not self.block

    def extract_representation(self, diagram_id: int):
        """ Return a dictionary that can be sent as json of only the representation details """
        return dict(
            diagram=diagram_id,
            block=self.block,
            x=self.x,
            y=self.y,
            z=self.z,
            width=self.width,
            height=self.height,
            styling=self.styling,
            block_cls=type(self).__name__
        )

    def extract_model(self, original):
        """ Update the underlying model details. """
        # Determine which fields can be updated by the representation.
        keys = {f.name for f in fields(self.logical_class) if hasattr(self, f.name) and f.name != 'Id'}
        for k in keys:
            if (v:=getattr(self, k)) != getattr(original, k):
                setattr(original, k, v)

        # The representation no longer needs to track the values transferred to the model.
        self._dirty -= keys
        return original

    def set_model_id(self, entity):
        self.block = entity.Id
    def get_model_id(self) -> int:
        return self.block

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        ddict = {}
        ddict.update(d['_entity'])
        ddict.update(d)
        field_names = [f.name for f in fields(cls)]
        ddict = {k: v for k, v in ddict.items() if k in field_names}
        entity = cls(**ddict)
        return entity


class RelationshipReprSerializer(IRepresentationSerializer):

    base_url = f'/data/_RelationshipRepresentation'
    logical_class = None

    def new_model_item(self):
        return not self.relationship

    def extract_representation(self, diagram_id: int):
        """ Return a dictionary that can be sent as json of only the representation details """
        return dict(
                diagram = diagram_id,
                relationship = self.relationship,
                source_repr_id = self.start.Id,
                target_repr_id = self.finish.Id,
                routing = json.dumps(self.waypoints, cls=ExtendibleJsonEncoder),
                z = self.z,
                styling = self.styling,
                rel_cls = type(self).__name__
            )
    def extract_model(self, original):
        """ Update the underlying model details. """
        # Determine which fields can be updated by the representation.
        keys = {f.name for f in fields(self.logical_class) if hasattr(self, f.name) and f.name != 'Id'}
        for k in keys:
            if (v:=getattr(self, k)) != getattr(original, k):
                setattr(original, k, v)

        # The representation no longer needs to track the values transferred to the model.
        self._dirty -= keys
        return original

    def set_model_id(self, entity):
        self.relationship = entity.Id
    def get_model_id(self):
        return self.relationship

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        ddict = {}
        ddict.update(d['_entity'])
        ddict.update(d)
        field_names = [f.name for f in fields(cls)]
        ddict = {k: v for k, v in ddict.items() if k in field_names}
        ddict['waypoints'] = json.loads(d['routing'])
        return cls(**ddict)

# Modelling 'Entities:'
% for entity in generator.ordered_items:
@dataclass
class ${entity.__name__}(CleanMonitor):
    Id: shapes.HIDDEN = 0
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${generator.get_html_type(f.type)} = ${generator.get_default(f.type)}
    % endfor
    % if not entity in generator.md.relationship:
    order: shapes.HIDDEN = 0
    children: shapes.HIDDEN = field(default_factory=list)

    def get_icon(self):
        return "${mdef.get_style(entity, 'icon', 'folder')}"
    % endif

    def __post_init__(self):
        # Prepare and arm the dirty monitor functionality
        CleanMonitor.__init__(self)

% endfor


## Create the representations of the various blocks and relationships
# Representations of the various graphical elements
% for cls in generator.md.entity + generator.md.port:
@dataclass
class ${cls.__name__}Representation(diagrams.${mdef.get_style(cls, 'structure', 'Block')}, EntityReprSerializer, CleanMonitor):
    Id: shapes.HIDDEN = 0
    diagram: shapes.HIDDEN = 0
    block: shapes.HIDDEN = 0
    % for attr in generator.get_diagram_attributes(cls):
    ${attr.name}: ${generator.get_html_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    shape_type = shapes.BasicShape.getDescriptor("${mdef.get_style(cls, 'shape', 'rect')}")

    logical_class = ${cls.__name__}

    def __post_init__(self):
        # Prepare and arm the dirty monitor functionality
        CleanMonitor.__init__(self)

    @classmethod
    def repr_category(cls):
        return 'block'

% endfor


<%
    def get_relationship_type(field_type):
        if is_dataclass(field_type):
            return field_type.__name__ + 'Representation'
        if isinstance(field_type, mdef.XRef):
            types = [t for t in field_type.types if not (isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation))]
            type_names = ', '.join(get_relationship_type(t) for t in types)
            return f"[{type_names}]"
        result = generator.get_html_type(field_type)
        if result == 'Entity':
            return 'diagrams.Shape'
        return result
%>
% for cls in generator.md.relationship:
@dataclass
class ${cls.__name__}Representation(diagrams.Relationship, RelationshipReprSerializer, CleanMonitor):
    Id: shapes.HIDDEN = 0
    diagram: shapes.HIDDEN = 0
    relationship: shapes.HIDDEN = 0
    % for attr in fields(cls):
    ${attr.name}: ${get_relationship_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    logical_class = ${cls.__name__}

    def __post_init__(self):
        # Prepare and arm the dirty monitor functionality
        CleanMonitor.__init__(self)

    @classmethod
    def repr_category(cls):
        return 'relationship'

% endfor

## Create the diagram definitions
# Definitions for rendering the various diagrams
% for cls in generator.md.diagrams:
<% block_names = [f'"{e.__name__}": {e.__name__}Representation' for e in cls.__annotations__['entities']] %>
class ${cls.__name__}Representation(diagrams.Diagram):
    allowed_blocks = {${", ".join(block_names)}}

% endfor

allowed_children = {
    % for name in generator.all_names.keys():
    ${name}: [${', '.join(generator.children[name])}],
    % endfor
}

diagram_definitions = {
    % for cls in generator.md.diagrams:
    "${cls.__name__}": ${cls.__name__}Representation,
    % endfor
}

explorer_classes = {
    <%  lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.all_model_items] %>
    ${',\n    '.join(lines)}
}

representation_classes = {
    <%  lines = [f'"{c.__name__}Representation": {c.__name__}Representation'
        for c in generator.md.entity + generator.md.port + generator.md.relationship] %>
    ${',\n    '.join(lines)}
}

representation_lookup = {
    <%  lines = [f'"{c.__name__}": {c.__name__}Representation'
        for c in generator.md.entity + generator.md.port + generator.md.relationship] %>
    ${',\n    '.join(lines)}
}

connections_from = {
    ${",\n    ".join(generator.get_connections_from())}
}

def flatten(data):
    if isinstance(data, Iterable):
        for d in data:
            yield from flatten(d)
    else:
        yield data
        if hasattr(data, 'children'):
            yield from flatten(data.children)
diagram_classes = [${', '.join(f'"{c.__name__}"' for c in generator.md.diagrams)}]

def on_explorer_click(target_dbid: int, target_type: str):
    """ Called when an element was left-clicked. """
    console.log(f"Clicked on element {target_dbid}")



def run(explorer, canvas, details):
    eapi = ExplorerApi(allowed_children, explorer_classes)

    def on_diagram_selection(values, update, object):
        properties_div = document['details']
        for e in properties_div.children:
            e.remove()
        properties_div <= dataClassEditor(object, update=update)

    def on_explorer_dblclick(target_dbid: int, target_type: str):
        """ Called when an element was left-clicked. """
        console.log(f"Double-Clicked on element {target_dbid}")

        # If a diagram is double-clicked, open it.
        def oncomplete(response):
            # Clear any existing diagrams
            container = document[canvas]
            container.html = ''
            svg = html.SVG()
            svg.classList.add('diagram')
            container <= svg
            diagram_api = DiagramApi(target_dbid, explorer_classes, representation_classes, eapi)
            ## In future: subscribe to events in the diagram api.
            diagram = diagrams.load_diagram(target_dbid, diagram_definitions[target_type], diagram_api, svg,
                                            representation_lookup, connections_from)
            diagram_api.bind('shape_selected', on_diagram_selection)

        if target_type in diagram_classes:
            ajax.get(f'/data/diagram_contents/{target_dbid}', oncomplete=oncomplete)

    blank = document[explorer]

    eapi.bind('dblclick', on_explorer_dblclick)
    eapi.bind('click', on_explorer_click)
    make_explorer(blank, eapi)

    @bind(blank, 'click')
    def close_contextmenu(ev):
        ev.stopPropagation()
        ev.preventDefault()
        if cm := document.get(id=context_menu_name):
            cm.close()
