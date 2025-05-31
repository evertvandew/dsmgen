


pub trait AVecDeque<T: Copy + Default> {
    fn push_back(&mut self, value: T);
    fn pop_front(&mut self) -> Option<T>;
    fn len(&self) -> usize;
    fn space(&self) -> usize;
    fn full(&self) -> bool;
    fn empty(&self) -> bool;
}



pub struct VecDeque<const N: usize, T: Copy + Default> {
    data: [T;N],
    head: usize,
    size: usize
}
impl<const N: usize, T: Copy + Default> VecDeque<N, T> {
    pub fn new() -> Self {
        VecDeque{data: [T::default(); N], head: 0, size:0}
    }
}
impl<const N: usize, T: Copy + Default> AVecDeque<T> for VecDeque<N, T> {
    fn push_back(&mut self, value: T) {
        if self.size < N {
            self.data[self.head] = value;
            self.head = if self.head < N-1 {self.head+1} else {0};
            self.size += 1;
        }
    }
    fn pop_front(&mut self) -> Option<T> {
        if self.size == 0 {
            None
        } else {
            self.size -= 1;
            if self.size < self.head {
                Some(self.data[self.head - self.size - 1])
            } else {
                Some(self.data[N + self.head - self.size - 1])
            }
        }
    }
    fn len(&self) -> usize {self.size as usize}
    fn space(&self) -> usize {N - self.size}
    fn full(&self) -> bool {self.size == N}
    fn empty(&self) -> bool {self.size == 0}
}




#[cfg(test)]
mod tests {
    use super::*;
        
    #[test]
    fn test_construct() {
        let mut q: VecDeque<100, u8> = VecDeque::new();
        assert_eq!(q.len(), 0);
        assert!(q.empty());
        assert!(!q.full());
        assert_eq!(q.space(), 100);
        assert_eq!(q.pop_front(), None);
    }
    #[test]
    fn test_fill_empty_fully() {
        let mut q: VecDeque<100, u8> = VecDeque::new();
        for i in 0..100 {
            assert!(!q.full());
            q.push_back(i as u8);
            assert_eq!(q.len(), i+1);
            assert!(!q.empty());
        }
        assert_eq!(q.size, 100);
        assert_eq!(q.head, 0);
        assert!(q.full());
        
        for i in 0..100 {
            assert!(!q.empty());
            assert_eq!(q.pop_front(), Some(i as u8));
            assert_eq!(q.len(), 100-i-1);
            assert!(!q.full());
        }
        assert_eq!(q.pop_front(), None);
        assert!(q.empty());
    }
    #[test]
    fn test_fill_empty_partially() {
        let mut q: VecDeque<100, u8> = VecDeque::new();
        for _ in 0..100 {
            for i in 0..100-10 {
                q.push_back(i as u8);
                assert_eq!(q.len(), i+1);
            }
            for i in 0..100-10 {
                assert_eq!(q.pop_front(), Some(i as u8));
                assert_eq!(q.len(), 100-i-11);
            }
            assert_eq!(q.pop_front(), None);
        }
    }
    #[test]
    fn test_small_queue() {
    }
}
