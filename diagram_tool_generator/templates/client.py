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

import model_definition as mdef
from model_definition import fields, is_dataclass

%>

from browser import document, console, html, svg, bind, ajax
import json
from explorer import Element, make_explorer, context_menu_name
from dataclasses import dataclass, field, is_dataclass, asdict, fields
from typing import Self, List, Dict, Any, Callable, Type
from collections.abc import Iterable
import typing
import types
from enum import IntEnum
from inspect import getmro
from modeled_diagram import ModeledDiagram
import modeled_shape as ms
import diagrams
import shapes
from property_editor import dataClassEditor, longstr, OptionalRef, parameter_spec, parameter_values, stylingEditorForm
from data_store import DataStore, DataConfiguration, ExtendibleJsonEncoder, Collection, StorableElement
from svg_shapes import getMarkerDefinitions
from tab_view import TabView


def resolve(name: str) -> Type[ms.ModelEntity]:
    r, *parts = name.split('.')
    var = globals()[r]
    for p in parts:
        var = getattr(var, p)
    return var

# Modelling 'Entities:'
% for entity in generator.ordered_items:
@dataclass
class ${entity.__name__}(ms.ModelEntity, StorableElement):
    % for f in fields(entity):
    ## All elements must have a default value so they can be created from scratch
    ${f.name}: ${generator.get_html_type(f.type)} = ${generator.get_default(f.type)}
    % endfor
    %if generator.md.is_port(entity):
    orientation: shapes.BlockOrientations = shapes.BlockOrientations.RIGHT
    %endif
    % if not generator.md.is_relationship(entity):
    order: shapes.HIDDEN = 0
    children: shapes.HIDDEN = field(default_factory=list)
    % if generator.md.is_instance_of(entity):
    parameters: parameter_values = field(default_factory=dict)
    % endif
    % if generator.get_allowed_ports().get(entity.__name__, []):
    ports: List[ms.ModelEntity] = field(default_factory=list)
    %endif

    def get_icon(self):
        return "${generator.md.get_style(entity, 'icon', 'folder')}"
    % endif

    % if generator.md.is_diagram(entity):
    class Diagram(ModeledDiagram):
        allowed_drops_blocks = {${", ".join(generator.get_allowed_drops(entity))}}
        allowed_create_blocks = {${", ".join(generator.get_allowed_creates(entity))}}
        @classmethod
        def get_allowed_blocks(cls, for_drop=False) -> Dict[str, Type[ms.ModelEntity]]:
            # The allowed blocks are given as a Dict[str, str]. Here we replace the str references to classes
            # by actual classes.
            if for_drop:
                return {k: resolve(v) for k, v in cls.allowed_drops_blocks.items()}
            else:
                return {k: resolve(v) for k, v in cls.allowed_create_blocks.items()}
    % endif

    @classmethod
    def is_instance_of(cls):
        % if generator.md.is_instance_of(entity):
        return True

    def get_definition(self) -> int:
        return self.definition
        %else:
        return False
        %endif

    @classmethod
    def get_allowed_ports(cls) -> List[str]:
        return [${', '.join(generator.get_allowed_ports().get(entity.__name__, []))}]

    @classmethod
    def get_collection(cls) -> Collection:
    %if generator.md.is_relationship(entity):
        return Collection.relation
    %elif generator.md.is_representable(entity):
        return Collection.block
    %elif generator.md.is_explorable(entity):
        return Collection.hierarchy
    %else:
        return Collection.not_storable
    %endif

    %if generator.md.is_representable(entity):
    @classmethod
    def representation_cls(cls) -> ms.ModeledShape | ms.ModeledShapeAndPorts | ms.Port | ms.ModeledRelationship:
    %if generator.md.is_relationship(entity):
        return ms.ModeledRelationship
    %elif generator.md.is_port(entity):
        return ms.Port
    %elif generator.get_allowed_ports().get(entity.__name__, []) or generator.md.is_instance_of(entity):
        return ms.ModeledShapeAndPorts
    %else:
        return ms.ModeledShape
    %endif

    %endif

    def get_editable_parameters(self) -> List[ms.EditableParameterDetails]:
        return [
        %for f in [f for f in fields(entity) if f.name not in ['parent', 'Id', 'ports', 'children']]:
            ms.EditableParameterDetails("${f.name}", ${generator.get_html_type(f.type)}, self.${f.name}, ${generator.get_html_type(f.type)}),
        %endfor
        ]

    %if generator.md.is_relationship(entity):
    def asdict(self) -> Dict[str, Any]:
        """ Relationships need to serialize only the ID's of the target and source,
            not the source or target themselves.
        """
        details = StorableElement.asdict(self)
        details['source_id'] = self.source.Id if self.source else None
        details['target_id'] = self.target.Id if self.target else None
        del details['source']
        del details['target']
        return details
    %endif

% endfor


@dataclass
class PortLabel(ms.ModeledShape):
    Id: shapes.HIDDEN = 0
    block: shapes.HIDDEN = None
    parent: shapes.HIDDEN = None
    diagram: shapes.HIDDEN = None
    name: str = ''

    logical_class = None

    @classmethod
    def repr_category(cls):
        return 'block'

    @classmethod
    def getShapeDescriptor(cls):
        return shapes.BasicShape.getDescriptor("label")

    @classmethod
    def is_instance_of(cls):
        return False


allowed_children = {
    % for name in generator.all_names.keys():
    ${name}: [${', '.join(generator.children[name])}],
    % endfor
}

allowed_ports = {
    % for name, clss in generator.get_allowed_ports().items():
    "${name}": [${', '.join(f'{c}' for c in clss)}],
    % endfor
}

diagram_definitions = {
    % for cls in generator.md.diagrams:
    "${cls.__name__}": ${cls.__name__}.Diagram,
    % if generator.md.is_representable(cls):
    "${cls.__name__}": ${cls.__name__}.Diagram,
    % endif
    % endfor
}

explorer_classes = {
    <%  lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.hierarchy] %>
    ${',\n    '.join(lines)}
}

block_entities = {
    <%  lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.blocks] %>
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
instance_classes = {
    <% lines = [f'"{c.__name__}": {c.__name__}' for c in generator.md.instance_of] %>
    ${',\n    '.join(lines)}
}

connections_from = {
    ${",\n    ".join(generator.get_connections_from())}
}

opposite_ports = ${generator.get_opposite_ports()}


class DiagramConfig(diagrams.DiagramConfiguration):
    def get_repr_for_create(self, cls) -> type:
        repr = super().get_repr_for_create(cls)
        console.log(f"Got repr {repr.__name__}, {issubclass(repr, diagrams.CP)}")
        if issubclass(repr, diagrams.CP):
            # The user tries to create a new port. Inside a diagram, that is represented by a Label,
            # not by the normal representation for this CP.
            return PortLabel
        return repr


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
    repr: ms.ModeledShape = details['object']
    model: ms.ModelEntity = repr.model_entity

    properties_div = document['details']
    for e in properties_div.children:
        e.remove()
    _ = properties_div <= dataClassEditor(model, data_store, update=update)
    _ = properties_div <= stylingEditorForm(repr)


def on_explorer_click(_event_name, _event_source, data_store, details):
    """ Called when an element was left-clicked. """
    def datastore_update(update: Dict):
        for k, v in json.loads(update).items():
            setattr(data_element, k, v)
        data_store.update(data_element)

    target_dbid = details['target_dbid']
    target_type: str = details['target_type']
    data_element = details['data_element']
    update = details.get('update', False) or datastore_update
    console.log(f"Clicked on element {target_dbid}")
    properties_div = document['details']
    for e in properties_div.children:
        e.remove()
    properties_div <= dataClassEditor(data_element, data_store, update=update)



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
    diagram_tabview = TabView('canvas')

    def on_explorer_dblclick(_event_name, event_source, data_store, details):
        """ Called when an element was left-clicked. """
        canvas = details['context']['canvas']
        target_dbid: int = details['target_dbid']
        target_type: str = details['target_type']
        console.log(f"Double-Clicked on element {target_dbid}")

        # If a diagram is double-clicked, open it.
        def oncomplete(response):
            # Clear any existing diagrams
            svg_tag = html.SVG()
            svg_tag <= getMarkerDefinitions()
            svg_tag.classList.add('diagram')
            # container <= svg_tag
            ## In future: subscribe to events in the diagram api.
            config = DiagramConfig({}, connections_from)
            diagram = diagrams.load_diagram(target_dbid, diagram_definitions[target_type], config, data_store, svg_tag)
            diagram_details = data_store.get(target_type, target_dbid)
            console.log(f'DETAILS: {details}')
            diagram_tabview.add_page(diagram_details.name, svg_tag, diagram.close)
            data_store.subscribe('shape_selected', svg_tag, on_diagram_selection)

        if target_type in diagram_classes:
            ajax.get(f'/data/diagram_contents/{target_dbid}', oncomplete=oncomplete)


    data_store.subscribe('dblclick', blank, on_explorer_dblclick, context={'canvas': canvas})
    data_store.subscribe('click', blank, on_explorer_click)
    make_explorer(blank, data_store, allowed_children)

    @bind(blank, 'click')
    def close_contextmenu(ev):
        ev.stopPropagation()
        ev.preventDefault()
        if cm := document.get(id=context_menu_name):
            cm.close()

