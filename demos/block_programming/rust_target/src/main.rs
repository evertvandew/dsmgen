
mod arduino_lib;
mod block_program;
mod hal_mock;

use block_program::TheProgram;
use hal_mock::{mock_dio};


fn main() {
    let mut led = mock_dio::default();
    let mut the_program = TheProgram::new(led);
    
    println!("Starting application");    
}
