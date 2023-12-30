
from dataclasses import dataclass
import math
from math import inf
from typing import List, Tuple

@dataclass
class Point:
    x: float
    y: float
    def __str__(self):
        return f"({self.x}, {self.y})"
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    def __truediv__(self, scalar):
        return Point(self.x/scalar, self.y/scalar)
    def __mul__(self, scalar):
        return Point(self.x*scalar, self.y*scalar)
    def __rmul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)
    def __len__(self):
        return math.sqrt(self.x*self.x + self.y*self.y)
    def norm(self):
        return self.__len__()
    def dot(self, other):
        return self.x*other.x + self.y*other.y
    def astuple(self):
        return (float(self.x), float(self.y))
    def transpose(self):
        return Point(x=self.y, y=-self.x)
    def __json__(self):
        return self.astuple()

def load_waypoints(s: str) -> List[Tuple[float, float]]:
    """ The Brython JSON decoder doesn't handle infinity, so we need a workaround. """
    # Check the string doesn't contain anything weird
    # Do not allow parenthesis, as function calls are dangerous.
    if '(' in s:
        return []
    # We are going to use Python `eval` to parse this string, where inf is used instead of Infinity
    py_s = s.replace('Infinity', 'inf')
    coods = eval(py_s)
    return [Point(*c) for c in coods]
