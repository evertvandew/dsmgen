

#[derive(Debug)]
pub enum HardwareError {
    Err
}


pub trait OutputPin {
    type Error;
    fn set_low(&mut self) -> Result<(), Self::Error>;
    fn set_high(&mut self) -> Result<(), Self::Error>;
}


#[derive(Default, Debug)]
pub struct mock_dio {
    pub value: i32
}

impl OutputPin for mock_dio {
    type Error = HardwareError;
    fn set_low(&mut self) -> Result<(), Self::Error> {self.value = 0; Ok(())}
    fn set_high(&mut self) -> Result<(), Self::Error> {self.value = 1; Ok(())}
}
