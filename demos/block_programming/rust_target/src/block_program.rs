use crate::arduino_lib as lib;
use crate::arduino_lib::{Program, Connection, IoProcess, clock_tick};
use crate::hal_mock::OutputPin;


pub struct TheProgram<Pin1: OutputPin> {
    block1: lib::arduino_uno,
    block23: lib::counter,
    block28: lib::toggle,
    block31: lib::DO<Pin1>,
    connections: [lib::Connection; 3]
}


impl<Pin1: OutputPin> TheProgram<Pin1> {
    pub fn new(pin1: Pin1) -> Self {
        Self {
            block1: lib::arduino_uno::default(),
            block23: lib::counter::new(10),
            block28: lib::toggle::default(),
            block31: lib::DO::new(pin1),
            connections: [lib::Connection((1, 0), (2, 0)), lib::Connection((0, 0), (1, 0)), lib::Connection((2, 0), (3, 0))]
        }
    }
}

impl<Pin1: OutputPin> Program for TheProgram<Pin1> {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
        match index {
            0 => &mut self.block1,
            1 => &mut self.block23,
            2 => &mut self.block28,
            3 => &mut self.block31,
            _ => panic!("Block doesn't exist")
        }
    }
    fn get_connections(&self) -> std::slice::Iter<'_, Connection> {
        self.connections.iter()
    }
    fn get_arduino_block_id(&self) -> u8 {
        0
    }
}



#[cfg(test)]
mod tests {
    use super::*;
    use crate::hal_mock::{mock_dio};

    #[test]
    fn test_instantiation() {
        let pin = mock_dio::default();
        let mut the_program = TheProgram::new(pin);
        for i in 0..9 {
            clock_tick(&mut the_program);
            assert_eq!(the_program.block31.pin.value, 0);
        }
        clock_tick(&mut the_program);
        assert_eq!(the_program.block31.pin.value, 1);
        for i in 0..9 {
            clock_tick(&mut the_program);
            assert_eq!(the_program.block31.pin.value, 1);
        }
        clock_tick(&mut the_program);
        assert_eq!(the_program.block31.pin.value, 0);
    }
}