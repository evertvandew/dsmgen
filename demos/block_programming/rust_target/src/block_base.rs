
use crate::vecdeque::{AVecDeque, VecDeque};

pub const SUBPROCESS_WRAPPER_ID: u8 = 255;


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

#[derive(Default, Clone)]
pub struct Connection (pub (u8, u8), pub (u8, u8));


pub trait ProcessIOGetter {
    fn get_inputs(&mut self) -> &mut [InputPort];
    fn get_outputs(&mut self) -> &mut [OutputPort];
}

pub trait IoProcess {
    fn update_input(&mut self, index: u8, value: PortValue) {
        self.get_io().get_inputs()[index as usize].set_value(value);
        if self.get_io().get_inputs().iter().all(|i| i.is_set) {
            self.get_io().get_inputs().iter_mut().for_each(|i| i.is_set=false);
            self.get_io().get_outputs().iter_mut().for_each(|i| i.is_set=false);
            self.evaluate()
        }
    }
    fn evaluate(&mut self);
    fn get_io(&mut self) -> &mut dyn ProcessIOGetter;
}


pub trait Program {
    fn get_block(&mut self, index: u8) -> &mut dyn IoProcess;
    fn get_connections(&self) -> &[Connection];
    fn get_arduino_block_id(&self) -> u8;
}

fn find_connected(connections: &[Connection], block: u8, channel: u8) -> impl Iterator<Item = (u8, u8)> + use<'_> {
    connections.iter().filter(move |c| c.0.0==block && c.0.1==channel).map(|c|c.1)
}

pub fn process_events<T: Program>(program: &mut T, events: &mut dyn AVecDeque<(u8, u8)>) {
    while let Some(event) = events.pop_front() {
        let value = program.get_block(event.0).get_io().get_outputs()[event.1 as usize].value.clone();
        let mut updated = VecDeque::<100, (u8, u8)>::new();
        // We need two steps, separating the read-only use of program from mutable use.
        // The "updated" queue decouples the two.
        for (block_index, channel) in find_connected(program.get_connections(), event.0, event.1) {
            updated.push_back((block_index, channel));
        }
        while let Some((block_index, channel)) = updated.pop_front() {
            let mut block = program.get_block(block_index);
            block.update_input(channel, value.clone());
            block.get_io().get_outputs()
                .iter()
                .enumerate()
                .filter(|(e, o)| o.is_set)
                .for_each(|(e, o)| events.push_back((block_index, e.try_into().unwrap())));
        }
    }
}


pub fn clock_tick<T: Program>(program: &mut T) {
    let mut events: VecDeque<100, (u8, u8)> = VecDeque::new();
    events.push_back((program.get_arduino_block_id(),0));
    process_events(program, &mut events);
}


//
// pub struct SubProgram {
//     pub blocks: Vec<Box<dyn IoProcess>>,
//     pub inputs: Vec<InputPort>,
//     pub outputs: Vec<OutputPort>,
//     pub connections: Vec<Connection>
// }
// impl SubProgram {
//     fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
//         if index == SUBPROCESS_WRAPPER_ID {
//             self
//         } else if (index as usize) < self.blocks.len() {
//             self.blocks.get_mut(index as usize).unwrap().as_mut()
//         } else {
//             panic!("Block doesn't exist")
//         }
//     }
//     fn process_events(&mut self, events: &mut VecDeque<(u8, u8)>) {
//         while events.len() > 0 {
//             if let Some(event) = events.pop_front() {
//                 let value = match event.0 {
//                     SUBPROCESS_WRAPPER_ID => self.inputs[event.1 as usize].value.clone(),
//                     _ => self.get_block(event.0).get_outputs()[event.1 as usize].value.clone()
//                 };
//                 for (block, channel) in find_connected(self, event.0, event.1) {
//                     match block {
//                         SUBPROCESS_WRAPPER_ID => self.outputs.get_mut(channel as usize).unwrap().set_value(&value),
//                         _ => self.get_block(block).update_input(channel, value.clone())
//                             .iter()
//                             .for_each(| e | events.push_back((block, * e)))
//                     };
//                 }
//             }
//         }
//     }
// }
// impl IoProcess for SubProgram {
//     fn get_inputs(&mut self) -> Vec<&mut InputPort> {
//         self.inputs.iter_mut().collect()
//     }
//     fn get_outputs(&mut self) -> Vec<&mut OutputPort> {
//         self.outputs.iter_mut().collect()
//     }
//     fn update_input(&mut self, index: u8, value: PortValue) -> Vec<u8> {
//         self.outputs.iter_mut().for_each(|o| o.is_set=false);
//         let mut input = &mut self.get_inputs()[index as usize];
//         input.set_value(value);
//         input.is_set = false;
//
//         let mut events: VecDeque<(u8, u8)> = VecDeque::new();
//         events.push_back((SUBPROCESS_WRAPPER_ID, index as u8));
//         self.process_events(&mut events);
//         (0u8..(self.outputs.len() as u8)).filter(|i| self.outputs[*i as usize].is_set).collect()
//     }
//     fn evaluate(&mut self) -> Vec<u8> {vec![]}
// }
// impl Program for SubProgram {
//     fn get_block(&mut self, index: u8) -> &mut dyn IoProcess {
//         self.blocks.get_mut(index as usize).unwrap().as_mut()
//     }
//     fn get_connections(&self) -> std::slice::Iter<'_, Connection> {
//         self.connections.iter()
//     }
//     fn get_arduino_block_id(&self) -> u8 {
//         SUBPROCESS_WRAPPER_ID
//     }
// }
