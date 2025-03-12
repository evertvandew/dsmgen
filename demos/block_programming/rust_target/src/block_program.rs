
use crate::arduino_lib as lib;
use crate::arduino_lib::IoProcess;
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
            block23: lib::counter::new(1000),
            block28: lib::toggle::default(),
            block31: lib::DO::new(pin1),
            connections: [lib::Connection((1,1), (2,0)), lib::Connection((0,0), (1,0)), lib::Connection((2,1), (3,0))]
        }
    }
    
    fn find_connected(&self, block: u8, channel: u8) -> Vec<(u8, u8)> {
        self.connections.iter().filter(|c| c.0.0==block && c.0.1==channel).map(|c|c.1).collect()
    }
    
    pub fn tick(&mut self) {
        for (block, channel) in self.find_connected(0,0) {
            match block {
                0 => (),
                1 => {self.block23.update_input(channel, 0);()},
                _ => ()
            };
        }
    }
}
