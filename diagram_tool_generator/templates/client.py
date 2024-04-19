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

import model_definition as mdef
from model_definition import fields, is_dataclass, parameter_spec

%>

from browser import document, console, html, svg, bind, ajax
import json
from explorer import Element, make_explorer, context_menu_name
from dataclasses import dataclass, field, is_dataclass, asdict, fields
from typing import Self, List, Dict, Any, Callable, Type, Optional, Union, Tuple
from collections.abc import Iterable
import types
from enum import IntEnum
from inspect import getmro
from modeled_diagram import ModeledDiagram
import modeled_shape as ms
import diagrams
import shapes
from property_editor import dataClassEditor, longstr, OptionalRef, parameter_spec, parameter_values, stylingEditorForm, parameter_types
from storable_element import Collection, StorableElement, from_dict
from data_store import DataStore, DataConfiguration, ExtendibleJsonEncoder
from svg_shapes import getMarkerDefinitions
from tab_view import TabView
from point import load_waypoints
from copy import deepcopy, copy


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
    <%
        # Make name:type pairs of all fields to add to this class.
        # Start with the user-defined fields.
        internal_fields = {f.name: (f.type, generator.get_default(f.type)) for f in fields(entity)}
        persistent_fields = {f.name: f.type for f in fields(entity)}

        # Add the ID.
        persistent_fields['Id'] = int

        # Add fields according to the type of entity
        if generator.md.is_port(entity):
            internal_fields['orientation'] = ('shapes.BlockOrientations', 'shapes.BlockOrientations.RIGHT')
            persistent_fields['orientation'] = 'shapes.BlockOrientations'

        if generator.get_allowed_ports().get(entity.__name__, []) or generator.md.is_instance_of(entity):
            internal_fields['ports'] = ('List[ms.ModelEntity]', 'field(default_factory=list)')

        if generator.md.is_instance_of(entity):
            internal_fields['parameters'] = ('parameter_values', 'field(default_factory=dict)')
            persistent_fields['parameters'] = 'parameter_values'


        if not generator.md.is_relationship(entity):
            internal_fields['order'] = ('int', '0')
            persistent_fields['order'] = 'int'

            internal_fields['children'] = ('shapes.HIDDEN', 'field(default_factory=list)')

        if generator.md.is_message(entity):
            internal_fields['association'] = ('shapes.HIDDEN', 'None')
            persistent_fields['association'] = 'int'

        text_fields = [f.name for f in fields(entity)
                       if generator.field_is_type(f.type, str) or generator.field_is_type(f.type, mdef.longstr)]

        base_shape_name = generator.styling.get('shape', 'rect')

%>
    % for key, (type_, default) in internal_fields.items():
    ## All elements must have a default value so they can be created from scratch
    ${key}: ${generator.get_html_type(type_)} = ${default}
    % endfor

    % if generator.md.is_relationship(entity):
    default_styling = shapes.Relationship.getDefaultStyle().copy()
    % else:
    default_styling = shapes.BasicShape.getDescriptor("${base_shape_name}").getDefaultStyle().copy()
    % endif
    default_styling.update(${repr(generator.styling[entity.__name__])})


    def __eq__(self, other) -> bool:
        if type(self) != type(other):
            return False
        return (
            ${' and\n            '.join(f'self.{name} == other.{name}' for name in persistent_fields.keys())}
        )

    def copy(self) -> Self:
        return type(self)(
            ${',\n            '.join(f'{k}= copy(getattr(self, "{k}"))' for k in persistent_fields.keys())}
        )

    def get_icon(self):
        return "${generator.md.get_style(entity, 'icon', 'folder')}"

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
    %elif generator.md.is_message(entity):
        return Collection.message
    %elif generator.md.is_representable(entity):
        return Collection.block
    %elif generator.md.is_explorable(entity):
        return Collection.hierarchy
    %else:
        return Collection.not_storable
    %endif

    %if generator.md.is_representable(entity):
    @classmethod
    def get_representation_cls(cls, category: ms.ReprCategory) -> Optional[Union[ms.ModeledShape, ms.ModeledShapeAndPorts, ms.Port, ms.ModeledRelationship, ms.Message]]:
    %if generator.md.is_relationship(entity):
        if category == ms.ReprCategory.relationship:
            return ms.ModeledRelationship
    %elif generator.md.is_port(entity):
        if category == ms.ReprCategory.block:
            return PortLabel
        elif category == ms.ReprCategory.port:
            return ms.Port
    %elif generator.get_allowed_ports().get(entity.__name__, []) or generator.md.is_instance_of(entity):
        if category == ms.ReprCategory.block:
            return ms.ModeledShapeAndPorts
    %elif generator.md.is_message(entity):
        if category == ms.ReprCategory.message:
            return ms.Message
    %else:
        if category == ms.ReprCategory.block:
            return ms.ModeledShape
    %endif

    %endif

    def get_nr_texts(self) -> int:
        return ${len(text_fields)}

    def get_text(self, index: int) -> str:
        % for i, f in enumerate(text_fields):
        if index == ${i}:
            return self.${f}
        % endfor
        return ''

    def get_parameter_spec_fields(self) -> List[str]:
        return "${generator.get_spec_fields(entity)}"

    def get_parameter_specs(self) -> Dict[str, type]:
        field_specs = getattr(self, self.get_parameter_spec_fields())
        if isinstance(field_specs, str):
            fs = field_specs.strip('{}')
            field_specs = dict(name_type.split(':') for name_type in fs.split(',')) if fs else {}
        keys_types = {k.strip(): parameter_types[t.strip()] for k, t in field_specs.items()}
        return keys_types

    def get_editable_parameters(self) -> List[ms.EditableParameterDetails]:
        regular_parameters = [
        %for name, type_ in {k:v for k, v in persistent_fields.items() if k not in ['parent', 'Id', 'ports', 'children', 'source', 'target', 'definition', 'association']}.items():
            ms.EditableParameterDetails("${name}", ${generator.get_html_type(type_)}, self.${name}, ${generator.get_html_type(type_)}),
        %endfor
        ]
        %if generator.md.is_instance_of(entity):
        if not self.definition:
            return regular_parameters
        parameter_specs = self.definition.get_parameter_spec_fields()
        if not parameter_specs:
            return regular_parameters
        keys_types = self.definition.get_parameter_specs()
        if keys_types:
            regular_parameters += [
                ms.EditableParameterDetails(key, type_, self.parameters.get(key, ''), type_)
                for key, type_ in keys_types.items()
            ]
        # Filter out the parameter collection field
        regular_parameters = [p for p in regular_parameters if p.name not in parameter_specs]
        %endif
        return regular_parameters

    def asdict(self) -> Dict[str, Any]:
        """ Relationships need to serialize only the ID's of the target and source,
            not the source or target themselves.
        """
        details = {
            '__classname__': "${entity.__name__}",
            ${",\n            ".join((f'"{k}": self.{k}') for k in persistent_fields.keys())}
        }
    % if generator.md.is_relationship(entity):
        details['source'] = self.source.Id if self.source else None
        details['target'] = self.target.Id if self.target else None
    %endif
    % if generator.md.is_instance_of(entity):
        details['definition'] = self.definition.Id
    % endif
        return details

    @staticmethod
    def get_messages():
        return ${generator.get_messages(entity)}

    % if generator.md.is_relationship(entity):
    @classmethod
    def from_dict(cls, data_store: DataStore, **details) -> Self:
        self = from_dict(cls, **details)
        # Connections always connect to two blocks. Ports are also represented as blocks for this exact purpose.
        self.source = data_store.get(Collection.block, details['source'])
        self.target = data_store.get(Collection.block, details['target'])
        return self
    %elif  generator.md.is_instance_of(entity):
    @classmethod
    def from_dict(cls, data_store: DataStore, **details) -> Self:
        self = from_dict(cls, **details)
        if self.definition:
            self.definition = data_store.get(Collection.block, self.definition)
        if self.parameters:
            if isinstance(self.parameters, str):
                self.parameters = json.loads(self.parameters)
        else:
            self.parameters = {}
        return self

    def update(self, data: Dict[str, Any]):
        """ Overload of the `ModelEntity.update` function that takes parameters into account. """
        key_types = self.definition.get_parameter_specs()
        for k, v in data.items():
            if k in key_types:
                self.parameters[k] = key_types[k](v)
            else:
                if hasattr(self, k):
                    setattr(self, k, v)

    %endif

% endfor


@dataclass
class PortLabel(ms.ModeledShape):
    Id: shapes.HIDDEN = 0
    block: shapes.HIDDEN = None
    parent: shapes.HIDDEN = None
    diagram: shapes.HIDDEN = None

    logical_class = None

    @classmethod
    def repr_category(cls) -> ms.ReprCategory:
        return ms.ReprCategory.block

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
    properties_div.children = []
    _ = properties_div <= html.H3(f'{type(model).__name__}: {getattr(model, "name", "")}')
    _ = properties_div <= dataClassEditor(model, model.get_editable_parameters(), data_store, repr=repr, update=update)


def on_explorer_click(_event_name, _event_source, data_store, details):
    """ Called when an element was left-clicked. """
    def datastore_update(update: str):
        update_dict = json.loads(update)
        data_element.update(update_dict)
        data_store.update(data_element)

    target_dbid = details['target_dbid']
    target_type: str = details['target_type']
    data_element: ms.ModelEntity = details['data_element']
    update = details.get('update', False) or datastore_update
    properties_div = document['details']
    for e in properties_div.children:
        e.remove()
    properties_div.children = []
    _ = properties_div <= html.H3(f'{type(data_element).__name__}: {getattr(data_element, "name", "")}')
    _ = properties_div <= dataClassEditor(data_element, data_element.get_editable_parameters(), data_store, update=update)


def on_explorer_dblclick(data_store, details, tabview):
    """ Called when an element was double-clicked. """
    target_dbid: int = details['target_dbid']
    target_type: str = details['target_type']

    console.log(f"DBLCLICK {target_dbid} - {target_type}")

    # If a diagram is double-clicked, open it.
    if target_type in diagram_classes:
        svg_tag = html.SVG(id=target_dbid)
        svg_tag.classList.add('diagram')

        config = DiagramConfig(connections_from)
        diagram = diagrams.load_diagram(target_dbid, diagram_definitions[target_type], config, data_store, svg_tag)
        diagram_details = data_store.get(target_type, target_dbid)
        tabview.add_page(diagram_details.name, svg_tag, diagram)
        data_store.subscribe('shape_selected', svg_tag, on_diagram_selection)


data_config = DataConfiguration(
        hierarchy_elements=explorer_classes,
        block_entities=block_entities,
        relation_entities=relation_classes,
        port_entities=port_classes,
        base_url='/data'
    )

def run(explorer: str, canvas: str, details: str) -> Tuple[DataStore, TabView]:
    config = data_config

    data_store = DataStore(config)

    blank = document[explorer]
    diagram_tabview = TabView(canvas)

    # There can not be multiple definitions of the line-ends, so define them globally.
    svg_tag = html.SVG(id='line_ends', height=0, width=0)
    svg_tag <= getMarkerDefinitions()
    document <= svg_tag

    def on_dblclick(_event_name, event_source, data_store, details):
        """ Called when an element was left-clicked. """
        on_explorer_dblclick(data_store, details, diagram_tabview)

    data_store.subscribe('dblclick', blank, on_dblclick, context={'canvas': canvas})
    data_store.subscribe('click', blank, on_explorer_click)
    make_explorer(blank, data_store, allowed_children)

    @bind(blank, 'click')
    def close_contextmenu(ev):
        ev.stopPropagation()
        ev.preventDefault()
        if cm := document.get(id=context_menu_name):
            cm.close()

    # Return the data_store so it can be accessed in integration tests.
    return data_store, diagram_tabview
