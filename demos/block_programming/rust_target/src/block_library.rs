use crate::block_base::{OutputPort, InputPort, IoProcess, PortValue, Connection, ProcessIOGetter,
                        Program, SUBPROCESS_WRAPPER_ID};
use embedded_hal::digital::OutputPin;



pub struct ProcessIO<const m: usize, const n: usize> {
    pub inputs: [InputPort; m],
    pub outputs: [OutputPort; n]
}
impl<const m: usize, const n: usize> ProcessIO<m, n> {
    pub fn new() -> Self {
        ProcessIO{
            inputs: core::array::from_fn(|_| InputPort::default()),
            outputs: core::array::from_fn(|_| OutputPort::default())
        }
        //ProcessIO{inputs: [InputPort::default(); m], outputs: [OutputPort::default(); n]}
    }
}
impl<const m: usize, const n: usize> ProcessIOGetter for ProcessIO<m, n> {
    fn get_inputs(&mut self) -> &mut [InputPort] {&mut self.inputs}
    fn get_outputs(&mut self) -> &mut [OutputPort] {&mut self.outputs}
}
impl<const m: usize, const n: usize> core::default::Default for ProcessIO<m, n> {
    fn default() -> Self { Self::new() }
}


///////////////////////////////////////////////////////////////////////////////
// COUNTER
#[derive(Default)]
pub struct counter {
    pub channels: ProcessIO<1, 1>,
    pub maxcount: u32,
    pub current: u32,
    pub total: i32
}
impl counter {
    pub fn new(maxcount: u32) -> Self{
        Self{
            channels: ProcessIO::<1, 1>::new(),
            maxcount,
            ..Default::default()
        }
    }
}
impl IoProcess for counter {
    fn evaluate(&mut self) {
        self.current += 1;
        if self.current >= self.maxcount {
            self.current = 0;
            self.total += 1;
            self.channels.outputs[0].set_value(&PortValue::Integer(self.total));
        }
    }
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter {&mut self.channels}
}


///////////////////////////////////////////////////////////////////////////////
// TOGGLE
#[derive(Default)]
pub struct toggle {
    pub channels: ProcessIO<1, 1>
}
impl toggle {
    pub fn new() -> Self {toggle{channels:  ProcessIO::<1, 1>::new()}}
}
impl IoProcess for toggle {
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter {&mut self.channels}
    fn evaluate(&mut self) {
        if let PortValue::Integer(value) = self.channels.outputs[0].value {
            if value == 0i32 {
                self.channels.outputs[0].set_value(&PortValue::Integer(1));
            } else {
                self.channels.outputs[0].set_value(&PortValue::Integer(0));
            }
        }
    }
}


///////////////////////////////////////////////////////////////////////////////
// DO (Digital Output)
pub struct DO<Pin> {
    pub channels: ProcessIO<1, 0>,
    pub pin: Pin,
}
impl <Pin: OutputPin> DO<Pin> {
    pub fn new(pin: Pin, _pintype: u8) -> Self {
        Self {
            channels: ProcessIO::<1, 0>::new(),
            pin,
        }
    }
}
impl<Pin: OutputPin> IoProcess for DO<Pin> {
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter {&mut self.channels}
    fn evaluate(&mut self) {
        if let PortValue::Integer(value) = self.channels.inputs[0].value {
            if value == 0 {
                let _ = self.pin.set_low();
            } else {
                let _ = self.pin.set_high();
            }
        }
    }
}



///////////////////////////////////////////////////////////////////////////////
// gain
pub struct gain {
    pub channels: ProcessIO<1, 1>,
    pub gain: f64
}
impl gain {
    pub fn new(gain: f64) -> Self {
        Self {
            channels: ProcessIO::<1, 1>::new(),
            gain
        }
    }
}
impl IoProcess for gain {
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter {&mut self.channels}
    fn evaluate(&mut self) {
        if let PortValue::Float(value) = self.channels.inputs[0].value {
            self.channels.outputs[0].set_value(&PortValue::Float(value * self.gain));
        }
    }
}


pub struct arduino_uno {
    pub channels: ProcessIO<0, 1>,
    count: i32
}
impl arduino_uno {
    pub fn new() -> Self {arduino_uno{channels: ProcessIO::<0, 1>::new(), count: 0}}
}
impl IoProcess for arduino_uno {
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter {&mut self.channels}
    fn evaluate(&mut self) {
        self.channels.outputs[0].set_value(&PortValue::Integer(self.count));
        self.count += 1;
    }
}