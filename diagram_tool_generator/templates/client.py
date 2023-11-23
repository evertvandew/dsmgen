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
from rest_api import RestApi, ExplorerApi, DiagramApi
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Self, List, Dict, Any
from collections.abc import Iterable
import typing
import types
from enum import IntEnum
import diagrams
import shapes
from property_editor import dataClassEditor, longstr

# Modelling 'Entities:'
% for entity in generator.ordered_items:
@dataclass
class ${entity.__name__}:
    Id: diagrams.HIDDEN = 0
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${generator.get_html_type(f.type)} = ${generator.get_default(f.type)}
    % endfor
    % if not entity in generator.md.relationship:
    order: diagrams.HIDDEN = 0
    children: diagrams.HIDDEN = field(default_factory=list)

    def get_icon(self):
        return "${mdef.get_style(entity, 'icon', 'folder')}"
    % endif

% endfor


## Create the representations of the various blocks and relationships
# Representations of the various graphical elements
% for cls in generator.md.entity + generator.md.port:
@dataclass
class ${cls.__name__}Representation(diagrams.${mdef.get_style(cls, 'structure', 'Block')}):
    Id: diagrams.HIDDEN = 0
    diagram: diagrams.HIDDEN = 0
    block: diagrams.HIDDEN = 0
    % for attr in generator.get_diagram_attributes(cls):
    ${attr.name}: ${generator.get_html_type(attr.type)} = ${generator.get_default(attr.type)}
    % endfor

    shape_type = shapes.BasicShape.getDescriptor("${mdef.get_style(cls, 'shape', 'rect')}")

    logical_class = ${cls.__name__}

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
class ${cls.__name__}Representation(diagrams.Relationship):
    Id: diagrams.HIDDEN = 0
    diagram: diagrams.HIDDEN = 0
    relationship: diagrams.HIDDEN = 0
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
