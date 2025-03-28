use std::collections::VecDeque;
use std::fmt::Debug;
use crate::hal_mock::OutputPin;


const SUBPROCESS_WRAPPER_ID: u8 = 255;


#[derive(Debug, PartialEq, Clone)]
pub enum PortValue {
    Integer(i32),
    Float(f64)
}
impl Default for PortValue {
    fn default() -> Self {
        PortValue::Integer(0)
    }
}



#[derive(Default, Debug)]
pub struct InputPort {
    pub value: PortValue,
    pub is_set: bool
}
impl InputPort {
    pub fn set_value(&mut self, value: PortValue) {
        self.value = value;
        self.is_set = true;
    }
}


#[derive(Default)]
pub struct OutputPort {
    pub value: PortValue,
    pub is_set: bool
}
impl OutputPort {
    pub fn set_value(&mut self, value: &PortValue) {
        self.value = value.clone();
        self.is_set = true;
    }
}

pub struct Connection (pub (u8, u8), pub (u8, u8));


pub trait IoProcess {
    fn update_input(&mut self, index: u8, value: PortValue) -> Vec<u8> {
        self.get_inputs()[index as usize].set_value(value);
        if self.get_inputs().iter().all(|i| i.is_set) {
            self.get_inputs().iter_mut().for_each(|i| i.is_set=false);
            self.evaluate()
        } else {
            vec![]
        }
    }
    fn evaluate(&mut self) -> Vec<u8>;
    fn get_inputs(&mut self) -> Vec<&mut InputPort>;
    fn get_outputs(&mut self) -> Vec<&mut OutputPort>;
}


pub trait Program {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess;
    fn get_connections(&self) -> std::slice::Iter<'_, Connection>;
    fn get_arduino_block_id(&self) -> u8;
}

fn find_connected<T: Program>(program: &T, block: u8, channel: u8) -> Vec<(u8, u8)> {
    program.get_connections().filter(|c| c.0.0==block && c.0.1==channel).map(|c|c.1).collect()
}

pub fn process_events<T: Program>(program: &mut T, events: &mut VecDeque<(u8, u8)>) {
    while events.len() > 0 {
        if let Some(event) = events.pop_front() {
            let value = program.get_block(event.0).get_outputs()[event.1 as usize].value.clone();
            for (block, channel) in find_connected(program, event.0, event.1) {
                program.get_block(block).update_input(channel, value.clone())
                    .iter()
                    .for_each(|e| events.push_back((block, *e)));
            }
        }
    }
}


pub fn clock_tick<T: Program>(program: &mut T) {
    let mut events: VecDeque<(u8, u8)> = VecDeque::new();
    events.push_back((program.get_arduino_block_id(),0));
    process_events(program, &mut events);
}



pub struct SubProgram {
    blocks: Vec<Box<dyn IoProcess>>,
    inputs: Vec<InputPort>,
    outputs: Vec<OutputPort>,
    connections: Vec<Connection>
}
impl SubProgram {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
        if index == SUBPROCESS_WRAPPER_ID {
            self
        } else if (index as usize) < self.blocks.len() {
            self.blocks.get_mut(index as usize).unwrap().as_mut()
        } else {
            panic!("Block doesn't exist")
        }
    }
    fn process_events(&mut self, events: &mut VecDeque<(u8, u8)>) {
        while events.len() > 0 {
            if let Some(event) = events.pop_front() {
                let value = match event.0 {
                    SUBPROCESS_WRAPPER_ID => self.inputs[event.1 as usize].value.clone(),
                    _ => self.get_block(event.0).get_outputs()[event.1 as usize].value.clone()
                };
                for (block, channel) in find_connected(self, event.0, event.1) {
                    match block {
                        SUBPROCESS_WRAPPER_ID => self.outputs.get_mut(channel as usize).unwrap().set_value(&value),
                        _ => self.get_block(block).update_input(channel, value.clone())
                            .iter()
                            .for_each(| e | events.push_back((block, * e)))
                    };
                }
            }
        }
    }
}
impl IoProcess for SubProgram {
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {
        self.inputs.iter_mut().collect()
    }
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {
        self.outputs.iter_mut().collect()
    }
    fn update_input(&mut self, index: u8, value: PortValue) -> Vec<u8> {
        self.outputs.iter_mut().for_each(|o| o.is_set=false);
        let mut input = &mut self.get_inputs()[index as usize];
        input.set_value(value);
        input.is_set = false;

        let mut events: VecDeque<(u8, u8)> = VecDeque::new();
        events.push_back((SUBPROCESS_WRAPPER_ID, index as u8));
        self.process_events(&mut events);
        (0u8..(self.outputs.len() as u8)).filter(|i| self.outputs[*i as usize].is_set).collect()
    }
    fn evaluate(&mut self) -> Vec<u8> {vec![]}
}
impl Program for SubProgram {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
        self.blocks.get_mut(index as usize).unwrap().as_mut()
    }
    fn get_connections(&self) -> std::slice::Iter<'_, Connection> {
        self.connections.iter()
    }
    fn get_arduino_block_id(&self) -> u8 {
        SUBPROCESS_WRAPPER_ID
    }
}

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


#[cfg(test)]
mod tests {
    use super::*;
    use crate::hal_mock::{mock_dio};
        
    #[test]
    fn test_update_do1() {
        let mut do1 = DO::new(mock_dio::default());
        assert_eq!(do1.update_input(0, PortValue::Integer(1)), vec![]);
        assert_eq!(do1.input.value, PortValue::Integer(1i32));
        assert_eq!(do1.pin.value, 1i32);
        assert_eq!(do1.input.is_set, false);

        do1.update_input(0, PortValue::Integer(0));
        assert_eq!(do1.input.value, PortValue::Integer(0i32));
        assert_eq!(do1.pin.value, 0i32);
        assert_eq!(do1.input.is_set, false);
    }

    #[test]
    fn test_update_toggle() {
        let mut tgl = toggle::default();
        assert_eq!(tgl.update_input(0, PortValue::Integer(1)), vec![0u8]);
        assert_eq!(tgl.input.value, PortValue::Integer(1i32));
        assert_eq!(tgl.out.value, PortValue::Integer(1i32));
        assert_eq!(tgl.input.is_set, false);

        assert_eq!(tgl.update_input(0, PortValue::Integer(2)), vec![0u8]);
        assert_eq!(tgl.input.value, PortValue::Integer(2i32));
        assert_eq!(tgl.out.value, PortValue::Integer(0i32));
        assert_eq!(tgl.input.is_set, false);
    }

    #[test]
    fn test_update_counter() {
        let mut cntr = counter::new(100);
        for i in 1..=99 {
            assert_eq!(cntr.update_input(0, PortValue::Integer(1)), vec![]);
            assert_eq!(cntr.current, i);
            assert_eq!(cntr.total, 0);
        }
        assert_eq!(cntr.update_input(0, PortValue::Integer(1)), vec![0u8]);
        assert_eq!(cntr.current, 0);
        assert_eq!(cntr.total, 1);

        for i in 1..=99 {
            assert_eq!(cntr.update_input(0, PortValue::Integer(1)), vec![]);
            assert_eq!(cntr.current, i);
            assert_eq!(cntr.total, 1);
        }
        assert_eq!(cntr.update_input(0, PortValue::Integer(1)), vec![0u8]);
        assert_eq!(cntr.current, 0);
        assert_eq!(cntr.total, 2);
    }

    #[test]
    fn test_update_gain() {
        let mut gn = gain::new(3f64);
        assert_eq!(gn.update_input(0, PortValue::Float(0f64)), vec![0u8]);
        assert_eq!(gn.output.value, PortValue::Float(0f64));
        assert_eq!(gn.update_input(0, PortValue::Float(1f64)), vec![0u8]);
        assert_eq!(gn.output.value, PortValue::Float(3f64));
        assert_eq!(gn.update_input(0, PortValue::Float(-2f64)), vec![0u8]);
        assert_eq!(gn.output.value, PortValue::Float(-6f64));
    }

    #[test]
    fn test_update_subprocess() {
        let pin1 = mock_dio::default();
        let mut sp = SubProgram{
            blocks: vec![
                Box::new(counter::new(10)),
                Box::new(toggle::default()),
            ],
            inputs: vec![InputPort::default()],
            outputs: vec![OutputPort::default()],
            connections: vec![
                Connection((SUBPROCESS_WRAPPER_ID, 0), (0,0)),
                Connection((0,0), (1,0)),
                Connection((1,0), (SUBPROCESS_WRAPPER_ID,0))
            ]
        };
        for i in 0..9 {
            assert_eq!(sp.update_input(0, PortValue::Integer(0)), vec![]);
            assert_eq!(sp.blocks[1].get_outputs()[0].value, PortValue::Integer(0));
        }
        assert_eq!(sp.update_input(0, PortValue::Integer(0)), vec![0]);
        assert_eq!(sp.blocks[1].get_outputs()[0].value, PortValue::Integer(1));

        for i in 0..9 {
            assert_eq!(sp.update_input(0, PortValue::Integer(0)), vec![]);
            assert_eq!(sp.blocks[1].get_outputs()[0].value, PortValue::Integer(1));
        }
        assert_eq!(sp.update_input(0, PortValue::Integer(0)), vec![0]);
        assert_eq!(sp.blocks[1].get_outputs()[0].value, PortValue::Integer(0));
    }
}
