#![no_std]
#![no_main]

mod block_library;
mod block_base;
mod vecdeque;

use embedded_hal::digital::OutputPin;
use block_library as lib;
use crate::block_base::{clock_tick, Connection, Program, IoProcess};

use panic_halt as _;


struct TheProgram<Pin: OutputPin> {
    block0: lib::arduino_uno,
    block1: lib::counter,
    block2: lib::toggle,
    block3: lib::DO<Pin>,
    connections: [Connection; 3],
}
impl<Pin: OutputPin> TheProgram<Pin> {
    fn new(pin: Pin) -> Self {
        Self{
            block0: lib::arduino_uno::new(),
            block1: lib::counter::new(100),
            block2: lib::toggle::new(),
            block3: lib::DO::new(pin, 1),
            connections: [
                Connection((1, 0),(2, 0)),
                Connection((0, 0),(1, 0)),
                Connection((2, 0),(3, 0))
            ]
        }
    }
}
impl<Pin: OutputPin> Program for TheProgram<Pin> {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
        match index {
            0 => &mut self.block0,
            1 => &mut self.block1,
            2 => &mut self.block2,
            3 => &mut self.block3,
            _ => core::panic!("Unknown block ID")
        }
    }
    fn get_connections(&self) -> &[Connection] {
        &self.connections
    }
    fn get_arduino_block_id(&self) -> u8 {0}
}


#[arduino_hal::entry]
fn main() -> ! {
    let dp = arduino_hal::Peripherals::take().unwrap();
    let pins = arduino_hal::pins!(dp);

    let mut the_program = TheProgram::new(pins.d13.into_output());
 
    loop {
        clock_tick(&mut the_program);
        arduino_hal::delay_ms(1);
    }
}
