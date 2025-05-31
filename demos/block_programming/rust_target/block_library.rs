use std::collections::VecDeque;
use std::fmt::Debug;
use crate::hal_mock::OutputPin;
use crate::block_base::{OutputPort, InputPort, IoProcess, PortValue, Connection, SubProgram,
                        SUBPROCESS_WRAPPER_ID};

////////////////////////////////////////////////////////////////////////////////////////////////////
#[derive(Default)]
pub struct arduino_uno {
    pub timer_tick: OutputPort
}
impl IoProcess for arduino_uno {
    fn evaluate(&mut self) -> Vec<u8> {
        vec![0]
    }
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.timer_tick]}
}

///////////////////////////////////////////////////////////////////////////////
// COUNTER
#[derive(Default)]
pub struct counter {
    pub input: InputPort,
    pub overflow: OutputPort,
    pub maxcount: u32,
    pub current: u32,
    pub total: i32
}
impl counter {
    pub fn new(maxcount: u32) -> Self{
        Self{
            maxcount,
            ..Default::default()
        }
    }
}
impl IoProcess for counter {
    fn evaluate(&mut self) -> Vec<u8> {
        self.current += 1;
        if self.current >= self.maxcount {
            self.current = 0;
            self.total += 1;
            self.overflow.value = PortValue::Integer(self.total);
            vec![0]
        } else {
            vec![]
        }
    }
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.overflow]}
}


///////////////////////////////////////////////////////////////////////////////
// TOGGLE
#[derive(Default)]
pub struct toggle {
    pub input: InputPort,
    pub out: OutputPort
}
impl IoProcess for toggle {
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.out]}
    fn evaluate(&mut self) -> Vec<u8> {
        if let PortValue::Integer(value) = self.out.value {
            if value == 0i32 {
                self.out.value = PortValue::Integer(1);
            } else {
                self.out.value = PortValue::Integer(0);
            }
            vec![0]
        } else {
            vec![]
        }
    }
}


///////////////////////////////////////////////////////////////////////////////
// DO (Digital Output)
pub struct DO<Pin> {
    pub pin: Pin,
    pub input: InputPort
}
impl <Pin: OutputPin> DO<Pin> {
    pub fn new(pin: Pin) -> Self {
        Self {
            pin,
            input: InputPort::default()
        }
    }
}
impl<Pin: OutputPin> IoProcess for DO<Pin> {
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![]}
    fn evaluate(&mut self) -> Vec<u8> {
        if let PortValue::Integer(value) = self.input.value {
            if value == 0 {
                let _ = self.pin.set_low();
            } else {
                let _ = self.pin.set_high();
            }
        }
        vec![]
    }
}



///////////////////////////////////////////////////////////////////////////////
// gain
pub struct gain {
    pub input: InputPort,
    pub output: OutputPort,
    pub gain: f64
}
impl gain {
    pub fn new(gain: f64) -> Self {
        Self {
            input: InputPort::default(),
            output: OutputPort::default(),
            gain
        }
    }
}
impl IoProcess for gain {
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.output]}
    fn evaluate(&mut self) -> Vec<u8> {
        if let PortValue::Float(value) = self.input.value {
            self.output.value = PortValue::Float(value * self.gain);
            vec![0]
        } else {
            vec![]
        }
    }
}
