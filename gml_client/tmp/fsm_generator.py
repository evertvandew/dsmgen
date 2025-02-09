
import os
import sys
from contextlib import contextmanager
from dataclasses import field, dataclass
from typing import Self, Dict, Any

import tatsu
from tatsu.mixins.indent import IndentPrintMixin
from tatsu.model import ModelBuilderSemantics, NodeWalker

home = os.path.dirname(__file__)
grammar = f'{home}/fsm.ebnf'
parser_file = f'{home}/fsm_parser.py'

if not os.path.exists(parser_file) or os.path.getmtime(grammar) > os.path.getmtime(parser_file):
    result = tatsu.to_python_sourcecode(open(grammar).read(), filename=parser_file)
    with open(parser_file, 'w') as out:
        out.write(result)
import fsm_parser
parser = fsm_parser.FSMParser(semantics=ModelBuilderSemantics())

def filter(ast, clsname):
    return [a for a in ast[3] if type(a).__name__ == clsname]


class MyWalker(NodeWalker):
    def walk_default(self, node):
        if type(node) in [int, float, str]:
            return
        for c in node.ast:
            if type(c) not in [int, float, str]:
                self.walk(c)

def reconstruct_code(ast, indent=4) -> str:
    """ Recursively reconstruct a code snippet """
    parts = [' '*indent+a if isinstance(a, str) else reconstruct_code(a, indent+4) for a in ast]
    return '\n'.join(parts)

@dataclass
class NameSpaceDetails:
    name: str
    ast: Any
    parent: Self = None
    names: Dict[str, Any] = field(default_factory=dict)

class NameSpaceBuilder(MyWalker):
    def __init__(self):
        self.namespaces = []
        self.current_namespace = None
        self.current_fsm = None
        self.current_state = None

    @contextmanager
    def namespace(self, name, node):
        details = NameSpaceDetails(name, node, self.current_namespace)
        if self.current_namespace:
            self.current_namespace.names[name] = details
        else:
            self.namespaces.append(details)
        self.current_namespace = details
        try:
            yield self.current_namespace
        finally:
            self.current_namespace = self.current_namespace.parent
    def addname(self, name, node):
        self.current_namespace.names[name] = node

    def walk_Transition(self, node):
        self.walk_default(node)
        event_name = node.ast[1].ast
        node.name = event_name
        node.code = None
        if len(node.ast) > 5:
            node.code = node.ast[5].code
        if isinstance(event_name, tuple):
            event_name = event_name[0]
        self.addname('on'+event_name, node)
    def walk_Argument(self, node):
        name = node.ast[1]
        node.name = name
        self.addname(name, node)
    def walk_Event(self, node):
        if isinstance(node.ast, str):
            name = node.ast
        else:
            name = node.ast[1]
        node.name = name
        self.addname(name, node)
        if name == '_':
            self.current_state.is_default = True
            self.current_fsm.default_state.append(self.current_state)


    def walk_Variable(self, node):
        name = node.ast[1]
        node.name = name
        self.addname(name, node)


    def walk_State(self, node):
        old_state = self.current_state
        self.current_state = node
        node.is_default = False
        name = node.ast[1]
        node.name = name
        with self.namespace(name, node) as ns:
            node.ns = ns
            self.walk_default(node)

            self.addname('onentry', '\n'.join(n for n in node.ast[3] if isinstance(n, str)))
        self.current_state = old_state

    def walk_FsmDefinition(self, node):
        old_fsm = self.current_fsm
        self.current_fsm = node
        node.default_state = []
        name = node.ast[1]
        node.name = name
        with self.namespace(name, node) as ns:
            node.ns = ns
            self.walk_default(node)
        self.current_fsm = old_fsm

    def walk_Code(self, node):
        node.code = reconstruct_code(node.ast)


class FsmRenderer(MyWalker, IndentPrintMixin):
    def walk_FsmDefinition(self, node):
        arguments = filter(node.ast, 'Argument')
        events = filter(node.ast, 'Event')
        variables = filter(node.ast, 'Variable')
        states = [s for s in filter(node.ast, 'State')]

        name = node.name

        state_transitions = {}
        argument_names = [a.ast[1] for a in arguments]
        self.print(f"class {name.capitalize()} {{")
        with self.indent():
            self.print(f'constructor({", ".join(argument_names)}) {{')
            with self.indent():
                for n in arguments + events + variables + states:
                    self.walk(n)
                # for arg in argument_names:
                #     self.print(f'this.{arg} = {arg};')

                assert len(node.default_state) == 1
                initial_state_name = node.default_state[0].name
                self.print(f'this.current_state = this.{initial_state_name}_state.on_entry();')
            self.print('}')
        self.print('}')

        self.print(f'let fsm1 = new {name.capitalize()}();')

    def walk_State(self, node):
        name = node.name
        entry_node = node.ns.names.get('onentry', '') or node.ns.names.get('on_', '')
        entry_code = entry_node.code if entry_node else '{ }'
        self.print(f'this.state_{name} = {{')
        with self.indent():
            self.print(f'on_entry: function() {entry_code.strip()}')
        self.print('}')


def generate_JS(istream=sys.stdin, template=open('template.html'), ostream=sys.stdout):
    text = istream.read()
    model = parser.parse(text)
    walker = NameSpaceBuilder()
    walker.walk(model)
    renderer = FsmRenderer()
    renderer.output_stream = ostream
    renderer.walk(model)

def run():
    generate_JS(open('demo.app'), open('template.html'))


if __name__ == '__main__':
    run()
