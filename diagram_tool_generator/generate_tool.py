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
from typing import Self, Any, List, Dict
from itertools import chain

from mako.template import Template

import model_definition
import model_definition as mdef
from config import Configuration


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
    def __init__(self, config, module_name):
        self.config = config
        self.module_name = module_name

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
            pass
            if t := cls.__annotations__.get('parent', False):
                for d in get_inner_types(cls, t):
                    name = d.__name__
                    if name in all_names:
                        children[name].add(cls.__name__)
                    elif name == 'Self':
                        children[cls.__name__].add(cls.__name__)
        # Also look at the allowed "entities" in diagrams.
        for cls in [c for c in mdef.model_definition.all_model_items if 'entities' in c.__annotations__]:
            children[cls.__name__] |= {c.__name__ for c in get_inner_types(cls, cls.__annotations__['entities'])}
        self.children = children

        self.ordered_items = self.order_dependencies()
        self.md = md
        self.styling = mdef.styling_definition


    def get_logical_children(self, name: str):
        """ Determine which elements can be created as children of an item in the Logica Model. """
        # Determine which items depend on this item.
        # Relationships are NOT included, these are not explicit in the logical model.
        relationships = [c.__name__ for c in mdef.model_definition.relationship]
        children = [n for n in self.children[name] if n not in relationships]

        return children

    def get_allowed_ports(self) -> Dict[str, List[str]]:
        """ Determine which blocks can have which ports.
            Returns a dictionary of the names of blocks and a list of port types
        """
        result = {}
        for p in mdef.model_definition.port:
            # Assume the parent property is an XRef.
            for b in p.__annotations__['parent'].types:
                if issubclass(b, mdef.OptionalAnnotation):
                    continue
                l = result.setdefault(b.__name__, [])
                l.append(p.__name__)
        return result


    def get_diagram_attributes(self, cls):
        """ Retrieve the attributes of a class that a intended for editing by a user. """
        attrs = [f for f in fields(cls) if not mdef.hidden in self.get_type_options(f.type)]
        return attrs


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
            if mdef.optional in field_type.types:
                return 'OptionalRef(int)'
            return 'int'
        return field_type.__name__

    @staticmethod
    def get_type_options(field_type):
        if isinstance(field_type, model_definition.XRef):
            return Generator.get_type_options(field_type.types)
        if isinstance(field_type, list) or isinstance(field_type, tuple):
            return [o for t in field_type for o in Generator.get_type_options(t)]
        return [field_type] if isinstance(field_type, type) and issubclass(field_type, mdef.OptionalAnnotation) else []

    def get_html_type(self, field_type):
        if mdef.hidden in self.get_type_options(field_type):
            return 'shapes.HIDDEN'
        return self.get_type(field_type)

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

    def get_connections_from(self):
        """ Determine which connections can be started from the specific class. """
        all_connections = []
        for cls in mdef.model_definition.entity + mdef.model_definition.port:
            connections = [c for c in mdef.model_definition.relationship if cls in c.__annotations__['source'].types]
            options = {}
            for c in connections:
                for t in c.__annotations__['target'].types:
                    if isinstance(t, type) and issubclass(t, mdef.OptionalAnnotation):
                        continue
                    if t is Any:
                        l = options.setdefault('Any', [])
                        l.append(c.__name__)
                    else:
                        l = options.setdefault(t.__name__+'Representation', [])
                        l.append(c.__name__)
            lines = [f'{k}: [{", ".join(o)}]' for k, o in options.items()]
            all_connections.append(f"{cls.__name__}Representation: {{ {', '.join(lines)} }}")
        return all_connections


def generate_tool(config: Configuration):
    # Find and import the specified model
    module_name = os.path.splitext(os.path.basename(config.model_def))[0].replace('spec', '')
    spec = importlib.util.spec_from_file_location(module_name, config.model_def)
    new_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(new_mod)

    homedir = config.homedir
    tooldir = os.path.dirname(__file__)




    def ensure_dir_exists(p):
        ap = os.path.normpath(os.path.join(homedir, p))
        if not os.path.exists(ap):
            os.mkdir(ap)
        return ap

    config.server_dir = ensure_dir_exists(config.server_dir)
    config.client_dir = ensure_dir_exists(config.client_dir)

    def hdir(basedir, p):
        """ Return a directory relative to the homedir """
        return os.path.normpath(os.path.join(homedir, basedir, p))

    generator = Generator(config, module_name)

    #for cls in mdef.model_definition.entity:
    #    for f in fields(cls):
    #        print(f'{cls.__name__}.{f.name}: {get_type(f.type)} = {get_default(f.type)}')

    for tmpl, target in [
        ('templates/client.html', f'{config.client_dir}/{module_name}client.html'),
        ('templates/client.py', f'{config.client_dir}/{module_name}client.py'),
        ('templates/data_model.py', f'{config.server_dir}/{module_name}data.py'),
        ('templates/server.py', f'{config.server_dir}/{module_name}run.py'),
    ]:
        print(f'Rendering {tmpl} to {target}')
        template = Template(open(hdir(tooldir, tmpl)).read())
        result = template.render(
            config=config,
            generator=generator
        )
        with open(target, 'w') as out:
            out.write(result)



if __name__ == '__main__':
    generate_tool(Configuration('sysml_spec.py'))
