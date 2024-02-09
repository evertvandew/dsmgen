"""
Build manager for the generated project files.
Importing this module will ensure the project is built and artifacts generated.
"""

import os, os.path
import generate_tool as gt


def generate_tool():
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    gt.generate_tool(gt.Configuration("sysml_spec.py"))
    if not os.path.exists('public/src'):
        os.symlink(os.path.abspath('../public/src'), 'public/src')


# Generate all the components of the tool.
# As Python only imports modules once, this will get executed once no matter how many times it is imported
generate_tool()
