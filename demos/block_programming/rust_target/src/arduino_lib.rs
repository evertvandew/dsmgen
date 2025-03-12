use std::fmt::Debug;
use crate::hal_mock::OutputPin;

#[derive(Default, Debug)]
pub struct InputPort {
    pub value: i32,
    pub is_set: bool
}
impl InputPort {
    pub fn set_value(&mut self, value: i32) {
        self.value = value;
        self.is_set = true;
    }
}

#[derive(Default)]
pub struct OutputPort {
    pub value: i32
}

pub struct Connection (pub (u8, u8), pub (u8, u8));


pub trait IoProcess {
    fn update_input(&mut self, index: u8, value: i32) -> Vec<u8> {
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

#[derive(Default)]
pub struct arduino_uno {
    pub timer_tick: OutputPort
}


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
        if self.current > self.maxcount {
            self.current = 0;
            self.total += 1;
            self.overflow.value = self.total;
            vec![0]
        } else {
            vec![]
        }
    }
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.overflow]}
}



#[derive(Default)]
pub struct toggle {
    pub input: InputPort,
    pub out: OutputPort
}
impl IoProcess for toggle {
    fn get_inputs(&mut self) -> Vec<&mut InputPort> {vec![&mut self.input]}
    fn get_outputs(&mut self) -> Vec<&mut OutputPort> {vec![&mut self.out]}
    fn evaluate(&mut self) -> Vec<u8> {
        if self.out.value == 0i32 {
            self.out.value = 1;
        } else {
            self.out.value = 0;
        }
        println!("Toggle updated");
        vec![0]
    }
}


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
        if self.input.value == 0i32 {
            let _ = self.pin.set_low();
        } else {
            let _ = self.pin.set_high();
        }
        vec![]
    }
}




#[cfg(test)]
mod tests {
    use super::*;
    use crate::hal_mock::{mock_dio};
        
    #[test]
    fn test_update_do1() {
        let mut do1 = DO::new(mock_dio::default());
        assert_eq!(do1.update_input(0, 1), vec![]);
        assert_eq!(do1.input.value, 1i32);
        assert_eq!(do1.pin.value, 1i32);
        assert_eq!(do1.input.is_set, false);

        do1.update_input(0, 0);
        assert_eq!(do1.input.value, 0i32);
        assert_eq!(do1.pin.value, 0i32);
        assert_eq!(do1.input.is_set, false);
    }

    #[test]
    fn test_update_toggle() {
        let mut tgl = toggle::default();
        assert_eq!(tgl.update_input(0, 1), vec![0u8]);
        assert_eq!(tgl.input.value, 1i32);
        assert_eq!(tgl.out.value, 1i32);
        assert_eq!(tgl.input.is_set, false);

        assert_eq!(tgl.update_input(0, 2), vec![0u8]);
        assert_eq!(tgl.input.value, 2i32);
        assert_eq!(tgl.out.value, 0i32);
        assert_eq!(tgl.input.is_set, false);
    }
}
