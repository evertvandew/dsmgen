
import os.path
import sys
import glob


TOOL_HOME = os.path.abspath('../../diagram_tool_generator')

if TOOL_HOME not in sys.path:
    sys.path.append(TOOL_HOME)


# Do a basic check if the spec file compiles.
import block_programming_spec
print("The specification file can be parsed")

import run_project

specs = glob.glob('*_spec.py')[0]
project = os.path.basename(specs)[:-8]

run_project.run(specs, project, 5101)
