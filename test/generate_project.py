"""
Build manager for the generated project files.
Importing this module will ensure the project is built and artifacts generated.
"""

import os, os.path
import subprocess

def generate_tool():
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run("../diagram_tool_generator/generate_tool.py sysml_spec.py", shell=True)
    if not os.path.exists('public/src'):
        os.symlink(os.path.abspath('../public/src'), 'public/src')


# Generate all the components of the tool.
generate_tool()
