
import subprocess

import os, os.path
import sys
import subprocess
import glob



def generate_tool(project):
    # Generate the tool, create directories, clean up etc.
    for d in ['public', 'build', 'build/data']:
        if not os.path.exists(d):
            os.mkdir(d)
    subprocess.run(f"../../diagram_tool_generator/generate_tool.py {project}_spec.py", shell=True)

    links = ['public/stylesheet.css', 'public/src', 'public/assets']
    for link in links:
        if not os.path.exists(link):
            os.symlink(os.path.abspath(f'../../{link}'), link)


# Generate all the components of the tool.
specs = glob.glob('*_spec.py')
project = os.path.basename(specs[0]).split('_spec')[0]
generate_tool(project)
sys.path.append('build')

from block_programming_run import run
run(5101)
