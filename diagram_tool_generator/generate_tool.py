#!/bin/env python3.11
"""
Generate and write source files for a complete model editing tool.

The tool is split in an HTML + Javascript client, and a Python server.
The server has an SQL database as backend, the generated files manage this database using Alchemy.
The client uses some React, but are mainly pure javascript. Bootstrap is used for styling.

The files are generated from Mako templates. I like Mako because you can make them self-contained.
E.g. Jinja2 is better when a lot templates share the same base, Mako is better if you want a few highly specialized templates.
In this case, each template generates a totally different type of output, so Mako is much more convenient.
With Jinja2, we'd be fighting to get all the different functionality pushed into the templating context.

"""

import os, os.path
import sys
import importlib
from dataclasses import fields
from typing import Self, Any

from mako.template import Template

import model_definition as mdef
from config import Configuration


home = os.path.dirname(__file__)


def get_inner_types(owner, field_type):
    """ Find out what the inner type of a field is. Used to find cross-references between items. """
    if type(field_type) in [list, tuple]:
        possible_types = [t for t in field_type if not (isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation))]
        if Self in field_type:
            possible_types.append(owner)
        assert possible_types, f'No type defined for field {field_type}'
        return (t for ts in possible_types for t in get_inner_types(owner, ts))
    if isinstance(field_type, mdef.XRef):
        return [t for t in field_type.types if not (isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation))]
    return [field_type]


def determine_dependencies(all_names):
    xrefs = {}

    # Find all references to these names
    for name, cls in all_names.items():
        my_xrefs = [t.__name__ for f in fields(cls) for t in get_inner_types(cls, f.type) if
                    isinstance(t, type) and t.__name__ in all_names and t != cls]
        xrefs[name] = set(my_xrefs)
    return xrefs




class Generator:
    def __init__(self, config):
        self.config = config

        # Generate some look up tables and dependency lists
        md = mdef.model_definition
        all_names: dict[str, Any] = {c.__name__: c for c in md.all_model_items}
        # Check there are no duplicates in the names.
        assert len(all_names) == len(md.all_model_items), 'Duplicate names in the definitions'
        self.all_names = all_names

        self.dependencies = determine_dependencies(all_names)

        # Collect which children can be created for a model item.
        children = {n: set() for n in all_names}
        # First invert the "parent" relationship
        for cls in mdef.model_definition.all_model_items:
            if t := cls.__annotations__.get('parent', False):
                for d in get_inner_types(cls, t):
                    name = d.__name__
                    if name in all_names:
                        children[name].add(cls.__name__)
        # Also look at the allowed "entities" in diagrams.
        for cls in [c for c in mdef.model_definition.all_model_items if 'entities' in c.__annotations__]:
            children[cls.__name__] |= {c.__name__ for c in get_inner_types(cls, cls.__annotations__['entities'])}
        self.children = children

        self.ordered_items = self.order_dependencies()
        self.md = md


    def get_logical_children(self, name: str):
        """ Determine which elements can be created as children of an item in the Logica Model. """
        # Determine which items depend on this item.
        # Relationships are NOT included, these are not explicit in the logical model.
        relationships = [c.__name__ for c in mdef.model_definition.relationship]
        children = [n for n in self.children[name] if n not in relationships]

        return children

    def order_dependencies(self):
        # Order the elements by the number of xrefs they have
        order_items = []
        last_nr_ordered = 0
        while len(order_items) < len(self.all_names):
            for name, xr in self.dependencies.items():
                if name in order_items:
                    continue
                # Check if all dependencies already have been ordered
                if all(n in order_items for n in xr):
                    order_items.append(name)
            # If during this pass no new items were ordered, there is a circular reference.
            if len(order_items) == last_nr_ordered:
                # A circular reference can not be ordered.
                raise RuntimeError("Ordering stuck on circular reference")
            last_nr_ordered = len(order_items)
        return [self.all_names[n] for n in order_items]



    def get_type(self, field_type):
        """ Return the type of an attribute for use in the client """
        if isinstance(field_type, tuple):
            possible_types = [t for t in field_type if not (isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation)) ]
            assert possible_types, f'No type defined for field {field_type}'
            if len(possible_types) == 1:
                return self.get_type(possible_types[0])
            return ' | '.join(self.get_type(t) for t in possible_types)
        if isinstance(field_type, list):
            return f'[{", ".join(self.get_type(t) for t in field_type)}]'
        if isinstance(field_type, mdef.selection):
            return f'IntEnum("InstantEnum", "{" ".join(field_type.options)}")'
        if isinstance(field_type, mdef.XRef):
            return 'int'
        return field_type.__name__

    def get_default(self, field_type):
        if isinstance(field_type, list):
            return 'field(default_factory=list)'
        if isinstance(field_type, tuple):
            possible_types = [t for t in field_type if not (isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation)) ]
            assert possible_types, f'No type defined for field {field_type}'
            if len(possible_types) == 1:
                return self.get_default(possible_types[0])
            return 'None'
        if isinstance(field_type, mdef.selection):
            return '1'
        if field_type is int:
            return '0'
        if field_type is str:
            return '""'
        if field_type is mdef.longstr:
            return '""'
        if field_type is float:
            return '0.0'
        return None




def generate_tool(config: Configuration):
    # Find and import the specified model
    module_name = os.path.splitext(os.path.basename(config.model_def))[0]
    spec = importlib.util.spec_from_file_location(module_name, config.model_def)
    new_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(new_mod)

    generator = Generator(config)

    #for cls in mdef.model_definition.entity:
    #    for f in fields(cls):
    #        print(f'{cls.__name__}.{f.name}: {get_type(f.type)} = {get_default(f.type)}')

    for tmpl, target in [
        ('templates/client.tmpl', os.path.join(config.client_dir, f'{module_name}.html')),
        ('templates/data_model.tmpl', os.path.join(config.server_dir, f'{module_name}_data.py'))
    ]:
        template = Template(open(os.path.join(home, tmpl)).read())
        result = template.render(
            config=config,
            generator=generator
        )
        with open(target, 'w') as out:
            out.write(result)



if __name__ == '__main__':
    generate_tool(Configuration('sysml_model.py'))
