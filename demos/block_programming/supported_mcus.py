
from dataclasses import dataclass
from typing import Callable
import subprocess



@dataclass
class CpuSupport:
    name: str
    board_name: str
    cargo_template: str
    main_template: str
    create_project: Callable

def create_arduino(project_name, cpu_support):
    cmd = f'cargo generate --git {cpu_support.cargo_template} -n {project_name} -d board="{cpu_support.board_name}"'
    print('Executing:', cmd)
    subprocess.run(cmd,
                   shell=True)


supported_mcus = [
    CpuSupport(
        'arduino_uno',
        "Arduino Uno",
        'https://github.com/Rahix/avr-hal-template.git',
        """#![no_std]
#![no_main]

use block_library as lib;

use panic_halt as _;

#[arduino_hal::entry]
fn main() -> ! {{
    let dp = arduino_hal::Peripherals::take().unwrap();
    let pins = arduino_hal::pins!(dp);

    let mut the_program = Program{{
        blocks: vec![
            {blocks}
        ],
        connections: vec![
            {connections}
        ]
    }};
 
    loop {{
        lib::clock_tick(&mut the_program);
        arduino_hal::delay_ms(1);
    }}
}}""",
        create_arduino
    )
]