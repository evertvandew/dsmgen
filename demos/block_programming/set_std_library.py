""" Script to load the standard library into the database """
import glob
import pathlib
from enum import IntEnum, auto
from dataclasses import dataclass, field
from itertools import chain
from os import path
from typing import List, Any, Tuple, Optional, Dict, Generator
from xml.etree import ElementTree as ET

from build import block_programming_data as dm
from build.block_programming_data import PinType, PinInterrupt


class byte:
    """ For use a data type"""
    pass

class word:
    """ For use a data type"""
    pass

@dataclass
class can_msg:
    address: word
    data: List[byte]

class PortType(IntEnum):
    Sync = auto()
    Async = auto()
    Buffered = auto()
    IOConfig = auto()

class Orientation(IntEnum):
    TOP = 2
    RIGHT = 4
    BOTTOM = 6
    LEFT = 8
    ANY = 9

class SimpleType(IntEnum):
    Int = auto()
    Float = auto()
    String = auto()
    Bool = auto()

@dataclass
class Parameter:
    param_type: type
    default: Optional[Any] = None

    def type_str(self) -> str:
        if isinstance(self.param_type, str):
            return self.param_type
        return self.param_type.__name__

@dataclass
class Port:
    port_type: PortType = PortType.Sync
    data_type: type | dm.PeripheralClass = int
    orientation: Orientation = Orientation.ANY
    order: int = 0
    parameters: Dict[str, Parameter] = field(default_factory=dict)

@dataclass
class BlockDefinition:
    description: str = ''
    inputs: Dict[str, Port] = field(default_factory=dict)
    outputs: Dict[str, Port] = field(default_factory=dict)
    parameters: Dict[str, Parameter] = field(default_factory=dict)


class vec_3d: pass
class Quaternion: pass


stdlib = {
    'Basic IO': {
        'DI': BlockDefinition(
            inputs={'trigger': Port(), 'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin)},
            outputs={'value': Port(data_type=bool)},
            parameters={'type': Parameter(PinType, PinType.pull_up)}
        ),
        'DO': BlockDefinition(
            inputs={'input': Port(data_type=bool), 'enable': Port(port_type=PortType.Async, data_type=bool), 'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin)},
            parameters={'type': Parameter(PinType, PinType.two_state)}
        ),
        'Interrupt': BlockDefinition(
            inputs={'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin)},
            outputs={'trigger': Port()},
            parameters={'edge': Parameter(PinInterrupt, PinInterrupt.falling_edge)}
        ),
        'AnalogIn': BlockDefinition(
            inputs={'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin), 'trigger': Port()},
            outputs={'value': Port(data_type=float)},
            parameters={'range': Parameter(Tuple[float, float], (0.0, 100.0))}
        ),
        'PWM': BlockDefinition(
            inputs={
                'input': Port(data_type=float),
                'enable': Port(port_type=PortType.Async, data_type=bool),
                'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'timer': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Timer)
            },
            parameters={'range': Parameter(Tuple[float, float], (0.0, 100.0))}
        ),
        'Clock': BlockDefinition(
            inputs={'timer': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Timer)},
            outputs={'trigger': Port()},
            parameters={'frequency': Parameter(int, 1000)}
        ),
        'Counter': BlockDefinition(
            inputs={
                'trigger': Port(),
                'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'timer': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Timer)
            },
            outputs={'count': Port()}
        ),
        'Encoder Input': BlockDefinition(
            inputs={
                'trigger': Port(),
                'a_pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'b_in': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'timer': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Timer)
            },
            outputs={'position': Port()},
            parameters={'nr_ticks': Parameter(int)}
        ),
        'PulseGenerator': BlockDefinition(
            inputs={
                'enable': Port(),
                'pattern': Port(data_type=List[int]),
                'pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'timer': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Timer)
            },
            parameters={'frequency': Parameter(int)}
        ),
        'UART': BlockDefinition(
            inputs={
                'data_tx': Port(port_type=PortType.Buffered, data_type=byte),
                'tx_pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'rx_pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'uart': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Uart)
            },
            outputs={'data_rx': Port(data_type=byte)},
            parameters={'baudrate': Parameter(int, 9600)}
        ),
        'CAN': BlockDefinition(
            inputs={
                'data_tx': Port(port_type=PortType.Buffered, data_type=can_msg),
                'filter': Port(port_type=PortType.Async, data_type=word),
                'data_pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'enable_pin': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.IOPin),
                'can_device': Port(port_type=PortType.IOConfig, data_type=dm.PeripheralClass.Can)
            },
            outputs={'data_rx': Port(data_type=can_msg)},
            parameters={'baudrate': Parameter(int, 500000)}
        ),
    },
    'constant': BlockDefinition(
        outputs={'out': Port()},
        parameters={'type': Parameter(SimpleType), 'value': Parameter(str)}
    ),
    'conversions': {
        'mux': BlockDefinition(
            #inputs = lambda b: {f'in_{i+1}' for i in range(b.parameters['nr_inputs'])},
            inputs = {'a': Port(), 'b': Port()},
            outputs = {'out': Port()},
            parameters = {'nr_inputs': Parameter(int,2)}
        ),
        'demux': BlockDefinition(
            #outputs=lambda b: {f'out_{i + 1}' for i in range(b.parameters['nr_outputs'])},
            outputs = {'a': Port(), 'b': Port()},
            inputs={'in': Port()},
            parameters={'nr_outputs': Parameter(int, 2)}
        ),
    },
    'math': {
        'sum': BlockDefinition(
            #inputs=lambda b: {f'in_{i + 1}' for i in range(b.parameters['nr_inputs'])},
            inputs={'a': Port(), 'b': Port()},
            outputs={'out': Port()},
            parameters={'nr_inputs': Parameter(int, 2)}
        ),
        'mult': BlockDefinition(
            inputs={'a': Port(), 'b': Port()},
            outputs={'out': Port()},
        ),
        'gain': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'gain': Parameter(float, 1.0)}
        ),
        'expression': BlockDefinition(
            #inputs=lambda b: {f'in_{i + 1}' for i in range(b.parameters['nr_inputs'])},
            inputs={'a': Port(), 'b': Port()},
            outputs={'out': Port()},
            parameters={'nr_inputs': Parameter(int, 2), 'expression': Parameter(str)}
        ),
        'integrate': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'gain': Parameter(float, 1.0)}
        ),
        'differentiate': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'gain': Parameter(float, 1.0)}
        ),
        'low_pass': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'cutoff': Parameter(float, 1.0)}
        ),
        'high_pass': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'cutoff': Parameter(float, 1.0)}
        ),
        'transfer_function': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'transfer_function': Parameter(str)}
        ),
        'PID_controller': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()},
            parameters={'P': Parameter(float, 1.0), 'I': Parameter(float, 0.0), 'D': Parameter(float, 0.0)}
        ),
        'average': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()}
        ),
        'quaternions': {
            'rotate': BlockDefinition(
                inputs={'in': Port(vec_3d), 'r': Port(Quaternion)},
                outputs={'out': Port(vec_3d)}
            ),
            'add_rotations': BlockDefinition(
                inputs={'in': Port(Quaternion), 'r': Port(Quaternion)},
                outputs={'out': Port(Quaternion)}
            ),
            'normalize': BlockDefinition(
                inputs={'in': Port(Quaternion)},
                outputs={'out': Port(Quaternion)}
            ),
        }
    },
    'logic': {
        'counter': BlockDefinition(
            inputs={'in': Port(), 'reset': Port()},
            outputs={'count': Port(), 'overflow': Port(port_type=PortType.Async)},
            parameters={'initial': Parameter(int, 0), 'maximum': Parameter(int, None)}
        ),
        'toggle': BlockDefinition(
            inputs={'in': Port()},
            outputs={'out': Port()}
        )
    }
}

def read_pinconfig(fname: pathlib.Path) -> Dict[str, BlockDefinition]:
    ns = {'mcu': 'http://mcd.rou.st.com/modules.php?name=mcu'}
    xml = ET.parse(fname)
    mcu = xml.find('.', ns)
    pins = {
        p.attrib['Position']: (p.attrib['Name'], ','.join([s.attrib['Name'] for s in p.findall('mcu:Signal', ns)]))
        for p in xml.findall('.//mcu:Pin', ns)
    }
    orientation_lu = {0: Orientation.LEFT, 1: Orientation.BOTTOM, 2: Orientation.RIGHT, 3: Orientation.TOP}
    match mcu.attrib['Package']:
        case "LQFP32":
            orientations = {str(k+1): (orientation_lu[k // 8], k % 8) for k in range(32)}
        case "LQFP64":
            orientations = {str(k+1): (orientation_lu[k // 16], k % 16) for k in range(64)}
        case "LQFP144":
            orientations = {str(k+1): (orientation_lu[k // 36], k % 36) for k in range(144)}
        case _:
            raise RuntimeError(f"Packege {mcu.attrib['Package']} not supported")

    pin_ports = {f'{k}: {v[0]}': Port(
        PortType.IOConfig,
        orientation=orientations[k][0],
        order=orientations[k][1],
        parameters={'function': Parameter(f'selection({v[1]})')}
    ) for k, v in pins.items()}

    peripherals = {}
    pc = dm.PeripheralClass
    for name, peripheral_class in dict(TIM1_8=pc.Timer, ADC=pc.Adc, I2C=pc.I2c, UART=pc.Uart, USART=pc.Uart, SPI=pc.Spi,
                                       CAN=pc.Can, WWDG=pc.Watchdog).items():
        peripherals.update({t.attrib['InstanceName']: Port(
            PortType.IOConfig,
            data_type=peripheral_class
        ) for t in mcu.findall('mcu:IP', ns) if t.attrib['Name'] == name})

    return {
        'io_pins': BlockDefinition('', {}, pin_ports),
        'peripherals': BlockDefinition(outputs=peripherals)
    }


def read_pinconfigs(p: pathlib.Path, wanted_mcus: List[str]):
    files = list(chain.from_iterable(glob.glob(path.join(p, w)) for w in wanted_mcus))
    micro_controllers = {path.basename(f).split('.')[0]: read_pinconfig(f) for f in files}
    return micro_controllers

def arduino():
    pins = {f'D{i+1}': Port(PortType.IOConfig, orientation=Orientation.RIGHT) for i in range(14)}
    pins.update({f'A{i}': Port(PortType.IOConfig, orientation=Orientation.RIGHT) for i in range(6)})
    pins['timer_tick'] = Port(PortType.Async, orientation=Orientation.RIGHT)
    return {'arduino_uno': BlockDefinition(outputs=pins)}


mcus = read_pinconfigs(
    '/opt/st/stm32cubeide_1.16.1/plugins/com.st.stm32cube.common.mx_6.12.1.202409122256/db/mcu',
    ['STM32F446R*', 'STM32H743ZIT*']
)
mcus.update(arduino())


stdlib['Micro Controllers'] = mcus


def create_instances(lib: Dict, parent: dm.LibraryFolder) -> Generator[dm.LibraryFolder | dm.BlockDefinition, None, None]:
    for name, value in lib.items():
        if isinstance(value, dict):
            # Create a new Library folder
            new_folder = dm.LibraryFolder(name=name, parent=parent.Id)
            yield new_folder
            # Recurse into the contents of the folder
            yield from create_instances(value, new_folder)
        elif isinstance(value, BlockDefinition):
            # Create a new Library block
            paramstr = ','.join(f'{n}:{t.param_type.__name__}' for n, t in value.parameters.items())
            new_block = dm.BlockDefinition(name=name, parent=parent.Id, parameters=paramstr)
            yield new_block
            # Add the inputs and outputs
            for n, i in value.inputs.items():
                match i.port_type:
                    case PortType.IOConfig:
                        yield dm.ConfigInput(name=n, peripheral_class=i.data_type, parent=new_block.Id, orientation=Orientation.LEFT)
                    case PortType.Sync:
                        yield dm.Input(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.LEFT)
                    case PortType.Async:
                        yield dm.AsyncInput(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.LEFT)
                    case PortType.Buffered:
                        yield dm.BufferedIn(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.LEFT)
            for n, i in value.outputs.items():
                match i.port_type:
                    case PortType.IOConfig:
                        paramstr = ','.join(f'{n}:{t.type_str()}' for n, t in i.parameters.items())
                        yield dm.ConfigOutput(name=n, peripheral_class=i.data_type, parent=new_block.Id, parameters=paramstr,
                                              orientation=i.orientation, order=i.order,
                                              )
                    case PortType.Sync:
                        yield dm.Output(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.RIGHT)
                    case PortType.Async:
                        yield dm.AsyncOutput(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.RIGHT)
                    case PortType.Buffered:
                        yield dm.BufferedOut(name=n, parent=new_block.Id, data_type=i.data_type.__name__, orientation=Orientation.RIGHT)

def store_library(name: str, library):
    dm.init_db()
    with dm.session_context() as session:
        # Delete any existing standard library
        lib = dm.LibraryFolder.retrieve(1, session)
        assert lib.name == 'Library'
        existing_stdlib = None
        for l in session.query(dm._Entity).filter(dm._Entity.parent==lib.Id):
            if l.subtype == dm.LibraryFolder.__name__:
                lo = dm.LibraryFolder.decode(l)
                if lo.name == 'stdlib':
                    existing_stdlib = l
        if existing_stdlib:
            # Because of the parent and "on_cascade - delete" rule, we only need to delete the parent.
            session.delete(existing_stdlib)
            session.commit()

        # Create the standard library object. This also tells us which IDs will be generated by the DB.
        stdlib_obj = dm.LibraryFolder(name='stdlib', parent=lib.Id, description='Standard library for use with micro controllers')
        stdlib_obj.store(session)
        assert stdlib_obj.Id

        for b in create_instances(stdlib, stdlib_obj):
            b.store(session)

store_library('stdlib', stdlib)
