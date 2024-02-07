
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

    copy(home_dir('public/stylesheet.css'), 'build/public/stylesheet.css')
    copy_tree(home_dir('public/assets'), 'build/public/assets')
    copy_tree(home_dir('public/src'), 'build/public/src')

    Path('build/__init__.py').touch()


def run(specs, project, port):
    # Generate all the components of the tool.
    create_environment(project)
    config = generate_tool.Configuration(
        specs, client_dir='build/public', dbase_url='sqlite:///build/data/diagrams.sqlite3'
    )
    generate_tool.generate_tool(config)

    # Run the generated tool
    sys.path.append('build')
    runlibname = f'{project}_run'
    runlib = importlib.import_module(runlibname)
    runlib.run(port, home_dir('client_src'))
