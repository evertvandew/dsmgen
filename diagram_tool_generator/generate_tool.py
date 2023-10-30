"""
Generate and write source files for a complete model editing tool.

The tool is split in an HTML + Javascript client, and a Python server.
The server has an SQL database as backend, the generated files manage this database using Alchemy.
The client uses some React, but are mainly pure javascript. Bootstrap is used for styling.

The files are generated from Mako templates. I like Mako because you can make them self-contained.
E.g. Jinja2 is better when a lot templates share the same base, Mako is better if you want highly specialized templates.
"""

import os
import sys
import importlib

import model_definition
from config import Configuration
from server_generator import generate_server
from dbase_model import generate_dbmodel
from client_generator import generate_client


def generate_tool(config: Configuration):
    # Find and import the specified model
    spec = importlib.util.spec_from_file_location(config.model_def, m)
    new_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(new_mod)

    generate_server(model_definition.model_definition, config)
    generate_dbmodel(model_definition.model_definition, config)
    generate_client(model_definition.model_definition, config)


if __name__ == '__main__':
    generate_tool(Configuration('sysml_model.py'))
