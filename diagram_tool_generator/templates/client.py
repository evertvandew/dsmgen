"""
Visual Modelling client.
"""
import svg_shapes

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

from browser import document, console, html, svg, bind, ajax
import json
from explorer import Element, make_explorer, context_menu_name
from dataclasses import dataclass, field, is_dataclass, asdict, fields
from typing import Self, List, Dict, Any, Callable
from collections.abc import Iterable
import typing
import types
from enum import IntEnum
from inspect import getmro
import diagrams
import shapes
from property_editor import dataClassEditor, longstr, OptionalRef
from data_store import DataStore, DataConfiguration, ExtendibleJsonEncoder
from svg_shapes import getMarkerDefinitions


# Modelling 'Entities:'
% for entity in generator.ordered_items:
@dataclass
class ${entity.__name__}:
    Id: shapes.HIDDEN = 0
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${generator.get_html_type(f.type)} = ${generator.get_default(f.type)}
    % endfor
    %if entity in generator.md.port:
    orientation: shapes.BlockOrientations = shapes.BlockOrientations.RIGHT
    %endif
    % if not entity in generator.md.relationship:
    order: shapes.HIDDEN = 0
    children: shapes.HIDDEN = field(default_factory=list)

    def get_icon(self):
        return "${mdef.get_style(entity, 'icon', 'folder')}"
    % endif

% endfor


## Create the representations of the various blocks and relationships
# Representations of the various graphical elements
% for cls in generator.md.entity:
@dataclass
class ${cls.__name__}Representation(diagrams.${mdef.get_style(cls, 'structure', 'Block')}):
    Id: shapes.HIDDEN = 0
    diagram: shapes.HIDDEN = 0
    block: shapes.HIDDEN = 0
    parent: shapes.HIDDEN = 0
    % if cls.__name__ in generator.get_allowed_ports():
    ports: [diagrams.CP] = field(default_factory=list)
    % endif
    % for attr in generator.get_diagram_attributes(cls):
    ${attr.name}: ${generator.get_html_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    shape_type = shapes.BasicShape.getDescriptor("${mdef.get_style(cls, 'shape', 'rect')}")

    logical_class = ${cls.__name__}

    @classmethod
    def repr_category(cls):
        return 'block'

    % if cls.__name__ in generator.get_allowed_ports():
    @classmethod
    def get_allowed_ports(cls):
        return [${", ".join(f'{c}Representation' for c in generator.get_allowed_ports()[cls.__name__])}]
    % endif

% endfor


% for cls in generator.md.port:
@dataclass
class ${cls.__name__}Representation(diagrams.FlowPort):
    Id: shapes.HIDDEN = 0
    diagram: shapes.HIDDEN = 0
    block: shapes.HIDDEN = 0
    parent: shapes.HIDDEN = 0
    % for attr in generator.get_diagram_attributes(cls):
    ${attr.name}: ${generator.get_html_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    shape_type = shapes.BasicShape.getDescriptor("${mdef.get_style(cls, 'shape', 'rect')}")

    logical_class = ${cls.__name__}

    @classmethod
    def repr_category(cls):
        return 'port'

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
class ${cls.__name__}Representation(diagrams.Relationship):
    Id: shapes.HIDDEN = 0
    diagram: shapes.HIDDEN = 0
    relationship: shapes.HIDDEN = 0
    % for attr in fields(cls):
    ${attr.name}: ${get_relationship_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    logical_class = ${cls.__name__}

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

allowed_ports = {
    % for name, clss in generator.get_allowed_ports().items():
    "${name}": [${', '.join(f'{c}Representation' for c in clss)}],
    % endfor
}

diagram_definitions = {
    % for cls in generator.md.diagrams:
    "${cls.__name__}": ${cls.__name__}Representation,
    % endfor
}

explorer_classes = {
    <%  lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.hierarchy] %>
    ${',\n    '.join(lines)}
}

block_entities = {
    <%  lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.entity] %>
    ${',\n    '.join(lines)}
}

relation_classes = {
    <% lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.relationship] %>
    ${',\n    '.join(lines)}
}
port_classes = {
    <% lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.port] %>
    ${',\n    '.join(lines)}
}
block_representations = {
    <% lines = [f'"{c.__name__}Representation": {c.__name__}Representation' for c in generator.md.entity] %>
    ${',\n    '.join(lines)}
}
relation_representations = {
    <% lines = [f'"{c.__name__}Representation": {c.__name__}Representation' for c in generator.md.relationship] %>
    ${',\n    '.join(lines)}
}
port_representations = {
    <% lines = [f'"{c.__name__}Representation": {c.__name__}Representation' for c in generator.md.port] %>
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

def on_diagram_selection(_e_name, _e_source, data_store, details):
    """ An item in a diagram has been selected: create a detail-editor for it. """
    values = details['values']
    update = details['update']
    object = details['object']
    properties_div = document['details']
    for e in properties_div.children:
        e.remove()
    properties_div <= dataClassEditor(object, data_store, update=update)

def on_explorer_click(_event_name, _event_source, data_store, details):
    """ Called when an element was left-clicked. """
    target_dbid = details['target_dbid']
    target_type: str = details['target_type']
    data_element = details['data_element']
    update = details.get('update', False) or data_store.update
    console.log(f"Clicked on element {target_dbid}")
    properties_div = document['details']
    for e in properties_div.children:
        e.remove()
    properties_div <= dataClassEditor(object, data_store, update=update)




def on_explorer_dblclick(_event_name, _event_source, data_store, details):
    """ Called when an element was left-clicked. """
    canvas = details['context']['canvas']
    target_dbid: int = details['target_dbid']
    target_type: str = details['target_type']
    console.log(f"Double-Clicked on element {target_dbid}")

    # If a diagram is double-clicked, open it.
    def oncomplete(response):
        # Clear any existing diagrams
        container = document[canvas]
        container.html = ''
        svg_tag = html.SVG()
        svg_tag <= getMarkerDefinitions()
        svg_tag.classList.add('diagram')
        container <= svg_tag
        ## In future: subscribe to events in the diagram api.
        diagram = diagrams.load_diagram(target_dbid, diagram_definitions[target_type], data_store, svg_tag,
                                        representation_lookup, connections_from)
        data_store.subscribe('shape_selected', svg_tag, on_diagram_selection)

    if target_type in diagram_classes:
        ajax.get(f'/data/diagram_contents/{target_dbid}', oncomplete=oncomplete)



def run(explorer, canvas, details):
    config = DataConfiguration(
        hierarchy_elements=explorer_classes,
        block_entities=block_entities,
        relation_entities=relation_classes,
        port_entities=port_classes,
        block_representations=block_representations,
        relation_representations=relation_representations,
        port_representations=port_representations,
        base_url='/data'
    )

    data_store = DataStore(config)


    blank = document[explorer]

    data_store.subscribe('dblclick', blank, on_explorer_dblclick, context={'canvas': canvas})
    data_store.subscribe('click', blank, on_explorer_click)
    make_explorer(blank, data_store, allowed_children)

    @bind(blank, 'click')
    def close_contextmenu(ev):
        ev.stopPropagation()
        ev.preventDefault()
        if cm := document.get(id=context_menu_name):
            cm.close()
