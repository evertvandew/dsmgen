import importlib
import sys
from argparse import ArgumentParser
import typing

import model_definition as mdef
from generate_tool import load_specification


def generate_graphviz(args):
    module, name, _ = load_specification(args.specification)
    model = module.md

    lines = ['digraph {']

    diagrams = model.diagrams
    relationships = model.relationship
    ports = model.port

    blocks = [b for b in model.blocks if b not in diagrams]
    folders = [b for b in model.hierarchy if b not in diagrams and b not in blocks and b not in ports]

    # Define the blocks
    for o in blocks:
        lines.append(f'{o.__name__} [shape=box];')
    for o in ports:
        lines.append(f'{o.__name__} [shape=circle];')
    for o in relationships:
        lines.append(f'{o.__name__} [shape=diamond];')
    for o in folders:
        lines.append(f'{o.__name__} [shape=folder];')
    for o in diagrams:
        lines.append(f'{o.__name__} [shape=Msquare];')

    # Generate the hierarchical structure
    for o in model.hierarchy:
        for p in o.__annotations__['parent'].types:
            parent_name = p if isinstance(p, str) \
                else o.__name__ if p == typing.Self \
                else 'Any' if p == typing.Any \
                else p.__name__
            lines.append(f'{parent_name} -> {o.__name__}')

    # Generate instantation lines
    for o in model.instance_of:
        for p in o.__annotations__['definition'].types:
            parent_name = p if isinstance(p, str) \
                else o.__name__ if p == typing.Self \
                else 'Any' if p == typing.Any \
                else p.__name__
            lines.append(f'{parent_name} -> {o.__name__} [style=dashed]')

    # Generate relationship lines
    for o in model.relationship:
        s, t = [o.__annotations__[k].types for k in ['source', 'target']]
        links = set(s + t)
        for l in links:
            parent_name = l if isinstance(l, str) \
                else o.__name__ if l == typing.Self \
                else 'Any' if l == typing.Any \
                else l.__name__
            color = 'darkgreen' if l not in s else 'red' if l not in t else 'blue'
            lines.append(f'{parent_name} -> {o.__name__} [style=dotted color={color}]')


    # Generate the output
    lines.append('}')
    result = ('\n'.join(lines))
    if args.output:
        with open(args.output, 'w') as o:
            o.write(result)
    else:
        print(result)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('specification')
    parser.add_argument('-o', '--output', default='')
    args = parser.parse_args()

    generate_graphviz(args)
