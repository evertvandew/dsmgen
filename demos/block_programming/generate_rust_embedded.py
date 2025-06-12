#!/usr/bin/env python3

import sys
import argparse
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os.path
import subprocess
import yaml

from supported_mcus import CpuSupport
from supported_mcus import supported_mcus


try:
    from build import block_programming_data as dm
except:
    print("Could not import the data model. Was the project run?")
    print("Running the file `run.py` in this directory will generate the file this program needs.")
    sys.exit(1)



@dataclass
class ProgramData:
    blocks: List[Any]
    connections: List[Any]
    ports: Dict[int, Any]

    @staticmethod
    def export_block(block) -> dict:
        return {
            'Id': block.Id,
            'type_name': block._entity.name,
            'type_id': block._entity.Id,
            'parameters': block.parameters,
            'type_parameters': block._entity.parameters,
            'diagram': block.diagram,
            'parent': block.parent
        }
    @staticmethod
    def export_connection(connection) -> dict:
        return {
            'Id': connection.Id,
            'type_name': type(connection._entity).__name__,
            'source': connection.source_repr_id,
            'target': connection.target_repr_id
        }
    @staticmethod
    def export_port(port) -> dict:
        return {
            'Id': port.Id,
            'name': port._entity.name,
            'type_name': type(port._entity).__name__,
            'parent_block': port.parent,
            'parent_type_id': port.block,
            'order': port.order,
            'parameters': {k:v for k, v in port._entity.__dict__.items() if k not in ["order", "orientation", "Id", "name", "parent", "__classname__"]}
        }

    def export(self) -> dict:
        base_dict = {
            "blocks": [self.export_block(b) for b in self.blocks],
            "connections": [self.export_connection(c) for c in self.connections],
            "ports": [self.export_port(p) for p in self.ports.values()],
        }
        base_dict['block_lu'] = {int(b['Id']): b for b in base_dict['blocks']}
        base_dict['connection_lu'] = {int(c['Id']): c for c in base_dict['connections']}
        base_dict['port_lu'] = {int(p['Id']): p for p in base_dict['ports']}
        return base_dict


def get_program_data(name: str) -> Optional[ProgramData]:
    """ name: path to the program, including its own name."""
    #  For now, only support root programs.
    assert '/' not in name

    # First find the diagram _entity
    with dm.session_context() as session:
        result = session.query(dm._Entity).filter(dm._Entity.type == dm.EntityType.Diagram
             and dm._Entity.subtype == 'ProgramDefinition'
             and dm._Entity.parent == 2
        ).all()

        diagrams = [dm.AWrapper.load_from_db(repr) for repr in result]
        diagram = [d for d in diagrams if getattr(d, 'name', '') == name]
        if len(diagram) != 1:
            return None

        # Find the elements associated with the program (diagram)
        # Plus the associated model item
        result = (session.query(dm._Representation, dm._Entity)
                  .filter(dm._Representation.diagram == diagram[0].Id)
                  .filter(dm._Entity.Id == dm._Representation.entity)
                  .all())

        data = []
        for repr, entity in result:
            d = dm.AWrapper.load_from_db(repr)
            d._entity = dm.AWrapper.load_from_db(entity)
            data.append(d)

        # Return the blocks and connections
        blocks = [d for d in data if d.category in [dm.ReprCategory.block, dm.ReprCategory.block_instance]]
        relationships = [d for d in data if d.category == dm.ReprCategory.relationship]
        ports = {d.Id:d for d in data if d.category == dm.ReprCategory.port}
        return ProgramData(blocks, relationships, ports)

def write_resource_getter(port: dict, data:dict) -> str:
    connection = [c for c in data['connections'] if c['target'] == port['Id']]
    if not connection:
        return 'NoResource()'
    else:
        source_port = data['port_lu'][connection[0]['source']]
        return f'pins.{source_port['name'].lower()}'


def write_block_construction(block, data) -> str:
    values = []
    if block['type_parameters']:
        parameters = block['parameters']
        if isinstance(parameters, dict) and len(parameters) == 1 and 'parameters' in parameters:
            parameters = parameters['parameters']
        values = [repr(parameters[i.split(':')[0]]) for i in block['type_parameters'].split(',')]
    resources = [p for p in data['ports'] if p['parent_block'] == block['Id'] and p['type_name'] == dm.ConfigInput.__name__]
    resource_definitions = [write_resource_getter(p, data) for p in resources]
    values = ', '.join(resource_definitions+values)
    return f'block{block['Id']}({values})'

def write_block_declaration(block: dict, data: dict) -> str:
    # return f'lib::{block._entity.name} block{block.Id}'

    values = []
    if block['type_parameters']:
        parameters = block['parameters']
        if isinstance(parameters, dict) and len(parameters) == 1 and 'parameters' in parameters:
            parameters = parameters['parameters']
        values = [repr(parameters[i.split(':')[0]]) for i in block['type_parameters'].split(',')]
    resources = [p for p in data['ports'] if p['parent_block'] == block['Id'] and p['type_name'] == dm.ConfigInput.__name__]
    resource_definitions = [write_resource_getter(p, data) for p in resources]
    values = ', '.join(resource_definitions+values)
    return f'lib::{block['type_name']}({values})'


def write_connection(connection: dict, port_lu: dict, block_lu: dict) -> Optional[str]:
    # Some connections
    if connection['type_name'] == dm.ConfigChannel.__name__:
        return None
    source_port = port_lu[connection['source']]
    target_port = port_lu[connection['target']]
    source_block = block_lu[source_port['parent_block']]
    target_block = block_lu[target_port['parent_block']]
    return (f'Connection(({source_block['order']}, {source_port['order']}),'
            f'({target_block['order']}, {target_port['order']}))')

def write_resource_acquisition(connection: dict, port_lu: dict) -> Optional[str]:
    if not connection['type_name'] == dm.ConfigChannel.__name__:
        return None
    source_port = port_lu[connection['source']]
    target_port = port_lu[connection['target']]
    resource_name = source_port['name']
    return f'auto& resource{target_port['Id']} = pins.{resource_name.lower()};'

def create_project(name: str, mcu_settings: CpuSupport):
    # delete the project if it already exists
    if os.path.exists(name):
        subprocess.run(f'rm -rf {name}', shell=True)

    # Create the project using cargo
    project_name = name.replace('_', '-')
    mcu_settings.create_project(project_name, mcu_settings)
    subprocess.run(f'cp rust_target/src/*.rs {name}/src', shell=True)


def write_program(cpu_support:CpuSupport, data: dict):
    #initializations = [write_resource_acquisition(c, data) for c in data.connections]
    blocks = [b for b in sorted(data['blocks'], key=lambda i: i['Id']) if b['parent'] is None]
    block_lu = data['block_lu']
    port_lu = data['port_lu']
    for i, b in enumerate(blocks):
        b['order'] = i
        for port_type in ['Input', 'Output']:
            for j, port in enumerate(p for p in sorted(data['ports'], key=lambda k: k['Id'])
                                     if p['parent_block'] == b['Id'] and p['type_name'] == port_type):
                port['order'] = j
    initializations = [write_block_construction(b, data) for b in blocks]
    block_declarations = [write_block_declaration(b, data) for b in data['blocks']]
    connections = [write_connection(c, port_lu, block_lu) for c in data['connections']]

    initializations = [i for i in initializations if i is not None]
    connections = [c for c in connections if c is not None]

    blockss = ',\n            '.join(block_declarations)
    connectionss = ',\n            '.join(connections)

    main_code = cpu_support.main_template.format(blocks=blockss, connections=connectionss)
    return main_code



def lookup_resource_type(port: Dict):
    return {
        1: 'InputPin',
        2: 'OutputPin',
        3: 'IOPin',
        4: 'Timer',
        5: 'Uart',
        6: 'CAN',
        7: 'ADC',
        8: 'I2C',
        9: 'SPI',
        10: 'Watchdog'
    }[port['parameters']['peripheral_class']]


def deindent(prefix: str, text: str) -> str:
    offset = len(prefix)
    lines = []
    for s in text.splitlines():
        if s.startswith(prefix):
            lines.append(s[offset:])
        else:
            lines.append(s)
    return '\n'.join(lines)

def indent(prefix: str, text: str) -> str:
    lines = []
    for s in text.splitlines():
        lines.append(prefix+s)
    return '\n'.join(lines)


class ProgramGenerator:
    def __init__(self, block_id, program_data, mcu_block=None):
        self.block_id = block_id
        self.program_data = program_data
        self.my_blocks = [b for b in self.program_data['blocks'] if b['parent'] == self.block_id]
        self.mcu_block = self.my_blocks.index(program_data['block_lu'][mcu_block])
        block_ids = set(b['Id'] for b in self.my_blocks)
        self.my_ports = [p for p in self.program_data['ports'] if p['parent_block'] in block_ids]
        port_ids = set(p['Id'] for p in self.my_ports)
        self.my_connections = [c for c in self.program_data['connections'] if c['source'] in port_ids and c['type_name'] != 'ConfigChannel']
        # Order the ports
        input_counts = {i:0 for i in block_ids}
        output_counts = {i:0 for i in block_ids}
        for p in self.my_ports:
            # Don't order the configuration ports: those are for compile time, not runtime connections.
            if 'config' in p['type_name'].lower():
                continue
            if 'output' in p['type_name'].lower():
                p['order'] = output_counts[p['parent_block']]
                output_counts[p['parent_block']] += 1
            else:
                p['order'] = input_counts[p['parent_block']]
                input_counts[p['parent_block']] += 1
        pass

    @property
    def inner_blocks(self):
        return self.my_blocks
    @property
    def inner_ports(self):
        return self.my_ports
    @property
    def parameters(self):
        """ Return a tuple (name, recipient, type, port_id) """
        config_ports = [p for p in self.inner_ports if p['type_name'] == 'ConfigInput']
        connection_lu = {c['target']: c['source'] for c in self.program_data['connections']}
        return [(p['name'], p['parent_block'], lookup_resource_type(p), p['Id'], connection_lu.get(p['Id'], None))
                for p in config_ports]

    @property
    def connections(self):
        return self.my_connections

    def block_constructor(self, block_id):
        block = self.inner_blocks[block_id]
        values = []
        if block['type_parameters']:
            parameters = block['parameters']
            if isinstance(parameters, dict) and len(parameters) == 1 and 'parameters' in parameters:
                parameters = parameters['parameters']
            type_parameters = block['type_parameters']
            if isinstance(type_parameters, str):
                type_parameters_names = [i.split(':')[0] for i in type_parameters.split(',')]
            else:
                type_parameters_names = type_parameters.keys()
            values = [repr(parameters[k]) for k in type_parameters_names]
        resources = [p for p in self.program_data['ports'] if
                     p['parent_block'] == block['Id'] and p['type_name'] == dm.ConfigInput.__name__]
        if resources:
            resource_order_lu = {p[3]: i for i, p in enumerate(self.parameters)}
            resource_txts = [f'P{resource_order_lu[p['Id']]}' for p in resources]
            resource_definitions = [r.lower() for r in resource_txts]
            resource_txt = ', '.join(resource_txts)
            values = ', '.join(resource_definitions + values)
            return f'lib::{block['type_name']}::new::<{resource_txt}>({values})'
        values = ', '.join(values)
        return f'lib::{block['type_name']}::new({values})'

    def connection_constructor(self, connection_id:int) -> str:
        order = {b['Id']:i for i, b in enumerate(self.inner_blocks)}
        connection = self.connections[connection_id]
        port_lu = self.program_data['port_lu']
        block_lu = self.program_data['block_lu']
        if connection['type_name'] == dm.ConfigChannel.__name__:
            return ''
        source_port = port_lu[connection['source']]
        target_port = port_lu[connection['target']]
        source_block = order[source_port['parent_block']]
        target_block = order[target_port['parent_block']]
        return (f'Connection(({source_block}, {source_port['order']}),'
                f'({target_block}, {target_port['order']}))')

    def get_program_name(self):
        return self.program_data['block_lu'][self.block_id] if self.block_id else "TheProgram"

    def get_param_decl(self):
        if parameters := self.parameters:
            return '<' + ', '.join(f'P{i}: {p[2]}' for i, p in enumerate(parameters)) + '>'
        return ''

    def get_param_ref(self):
        if parameters := self.parameters:
            return '<' + ', '.join(f'P{i}' for i, p in enumerate(parameters)) + '>'
        return ''

    def get_constructor_args(self):
        if parameters := self.parameters:
            return ', '.join(f'p{i}: P{i}' for i, p in enumerate(parameters))
        return ''

    def get_block_decl(self, b_id):
        b = self.inner_blocks[b_id]
        parameter_lu = {p[1]: p for p in self.parameters}
        result = f'lib::{b['type_name']}'
        if b['Id'] in parameter_lu:
            pargs = '<' + ','.join(f'P{i}' for i, p in enumerate(self.parameters) if p[1] == b['Id']) + '>'
            result += pargs
        return result

    def get_blocks_decl(self):
        block_params = {}
        for i, p in enumerate(self.parameters):
            if p[1] not in block_params:
                block_params[p[1]] = [f'P{i}']
            else:
                block_params[p[1]].append(f'P{i}')
        block_params = {i: '<'+', '.join(v)+'>' for i, v in block_params.items()}
        return ',\n                '.join(f'block{i}: lib::{b['type_name']}{block_params.get(b['Id'], '')}' for i, b in enumerate(self.inner_blocks))

    def get_program_instance_args(self):
        """ Determine the arguments to pass to a program when instantiating it. """
        args = []
        for parameter in self.parameters:
            resource = self.program_data['port_lu'][parameter[4]]
            match parameter[2]:
                case 'OutputPin':
                    args.append(f'pins.{resource['name'].lower()}.into_output()')
                case 'InputPin':
                    args.append(f'pins.{resource['name'].lower()}.into_input()')
                case _:
                    assert False, f"Resources of type {parameter[2]} are not yet supported"
        return ', '.join(args)

    def get_program_declaration(self):
        return deindent('            ', f"""
            struct {self.get_program_name()}{self.get_param_decl()} {{
                {self.get_blocks_decl()},
                connections: [Connection; {len(self.connections)}]
            }}
            """)
    def get_my_implementation(self):
        block_constructs = ',\n                        '.join(f'block{i}: {self.block_constructor(i)}' for i, _ in enumerate(self.inner_blocks))
        connect_constructs = ',\n'.join(self.connection_constructor(i) for i, _ in enumerate(self.connections))
        return deindent('            ', f"""
            impl{self.get_param_decl()} {self.get_program_name()}{self.get_param_ref()} {{
                fn new({self.get_constructor_args()}) -> Self {{
                    Self{{
                        {block_constructs},
                        connections: [
{indent('                            ', connect_constructs)}
                        ]
                    }}
                }}
            }}""")

    def get_program_implementation(self):

        block_list = ',\n                        '.join(f"{i:<3}=> &mut self.block{i}" for i, _ in enumerate(self.inner_blocks))
        return deindent('            ',f"""
            impl{self.get_param_decl()} Program for {self.get_program_name()}{self.get_param_ref()} {{
                fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {{
                    match index {{
                        {block_list},
                        _  => core::panic!("Unknown block ID")
                    }}
                }}
                fn get_connections(&self) -> &[Connection] {{
                    &self.connections
                }}
                fn get_arduino_block_id(&self) -> u8 {{{self.mcu_block}}}
            }}
        """)

    def get_implementations(self):
        result = [self.get_my_implementation(), self.get_program_implementation()]
        if self.block_id:
            result.append(self.get_ioprocess_implementation())
        return '\n'.join(result)

    def get_program(self):
        return f"""
            {self.get_program_declaration()}
            {self.get_implementations()}
            """


class ArduinoCodeGenerator:
    def __init__(self, name: str, program_data, mcu_block: int):
        self.name = name
        self.program_data = program_data
        self.mcu_block = mcu_block

    def get_program_generator(self, block_id):
        return ProgramGenerator(block_id, self.program_data, self.mcu_block)

    def full_program(self):
        program_generator = self.get_program_generator(None)
        return deindent('            ', f"""
            #![no_std]
            #![no_main]
            
            mod block_library;
            mod block_base;
            mod vecdeque;
            
            use embedded_hal::digital::{{OutputPin}};
            use block_library as lib;
            use crate::block_base::{{clock_tick, Connection, Program, IoProcess}};
            
            use panic_halt as _;
            
            {indent('            ', program_generator.get_program())}
            
            #[arduino_hal::entry]
            fn main() -> ! {{
                let dp = arduino_hal::Peripherals::take().unwrap();
                let pins = arduino_hal::pins!(dp);

                let mut the_program = TheProgram::new({program_generator.get_program_instance_args()});

                loop {{
                    clock_tick(&mut the_program);
                    arduino_hal::delay_ms(1);
                }}
            }}
            """)

    @property
    def program_name(self):
        return self.name.replace('_', '-')


def code_generator(name: str, program_data, mcu_block):
    return ArduinoCodeGenerator(name, program_data, mcu_block)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('program_name', nargs='*', )
    parser.add_argument('--test', '-t', action='store_true')
    parser.add_argument('--export-data', '-d', action='store_true')
    args = parser.parse_args()

    if not args.test:
        dm.changeDbase('sqlite:///build/data/diagrams.sqlite3')
        for program_name in args.program_name:
            data = get_program_data(program_name).export()
            if not data:
                print(f"Could not find program named {args.program_name}", file=sys.stderr)
                sys.exit(1)

            if args.export_data:
                yaml.dump(data, open(program_name + '.yml', 'w'), sort_keys=True, indent=4)

            # Find the MCU being used in the program
            supported_mcus = {m.name: m for m in supported_mcus}
            mcu_block = [b for b in data['blocks'] if b['type_name'] in supported_mcus]
            assert len(mcu_block) == 1
            mcu_settings = supported_mcus[mcu_block[0]['type_name']]
            proj_name = program_name.replace('_', '-')
            create_project(proj_name, mcu_settings)

            generator = ArduinoCodeGenerator(proj_name, data, 1)
            open(f'{proj_name}/src/main.rs', 'w').write(generator.full_program())
    else:
        define_tests()
        from test_frame import run_tests
        run_tests()
