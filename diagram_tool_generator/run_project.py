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
import os.path
import sys
import importlib
import generate_tool
from pathlib import Path
import shutil


def home_dir(fname):
    return f'../../{fname}'


def copy(source, target):
    if not os.path.exists(target):
        shutil.copy(source, target)

def copy_tree(source, target):
    if not os.path.exists(target):
        shutil.copytree(source, target)



def create_environment(project):
    # Generate the tool, create directories, clean up etc.
    for d in ['build', 'build/data', 'build/public']:
        if not os.path.exists(d):
            os.mkdir(d)

    Path('build/__init__.py').touch()


def run(specs, project, port):
    # Generate all the components of the tool.
    create_environment(project)
    config = generate_tool.Configuration(
        specs, client_dir='build/public', dbase_url='sqlite:///build/data/diagrams.sqlite3',
        pub_dir = os.path.normpath(os.path.dirname(__file__) + '/../public/')
    )
    generate_tool.generate_tool(config)

    # Run the generated tool
    sys.path.append('build')
    runlibname = f'{project}_run'
    runlib = importlib.import_module(runlibname)
    runlib.run(port, home_dir('client_src'))
