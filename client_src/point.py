"""
Copyright© 2024 Evert van de Waal

This file is part of dsmgen.

Dsmgen is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Dsmgen is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Foobar; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""
from dataclasses import dataclass
import math
from math import inf        # Do not delete: used when loading the waypoints.
from typing import List, Tuple, Self

@dataclass
class Point:
    x: float
    y: float
    def __str__(self) -> str:
        return f"({self.x}, {self.y})"
    def __add__(self, other) -> Self:
        return Point(self.x + other.x, self.y + other.y)
    def __sub__(self, other) -> Self:
        return Point(self.x - other.x, self.y - other.y)
    def __truediv__(self, scalar) -> Self:
        return Point(self.x/scalar, self.y/scalar)
    def __mul__(self, scalar) -> Self:
        return Point(self.x*scalar, self.y*scalar)
    def __rmul__(self, scalar) -> Self:
        return Point(self.x * scalar, self.y * scalar)
    def norm(self) -> float:
        return math.sqrt(self.x*self.x + self.y*self.y)
    def normalize(self) -> Self:
        l = self.norm()
        if l > 1e-10:
            return self / l
        return self
    def dot(self, other) -> float:
        return self.x*other.x + self.y*other.y
    def astuple(self) -> Tuple[float, float]:
        return (float(self.x), float(self.y))
    def transpose(self) -> Self:
        return Point(x=self.y, y=-self.x)
    def rot(self, angle: float) -> Self:
        """ Rotate the vector by a specific angle (in radians). """
        c = math.cos(angle)
        s = math.sin(angle)
        return Point(x=c*self.x-s*self.y, y=s*self.x+c*self.y)
    def __json__(self) -> Tuple[float, float]:
        return self.astuple()

def load_waypoints(s: str) -> List[Point]:
    """ The Brython JSON decoder doesn't handle infinity, so we need a workaround. """
    if not s:
        return []
    # Check the string doesn't contain anything weird
    # Do not allow parenthesis, as function calls are dangerous.
    if '(' in s:
        return []
    # We are going to use Python `eval` to parse this string, where inf is used instead of Infinity
    py_s = s.replace('Infinity', 'inf')
    coods = eval(py_s)
    return [Point(*c) for c in coods]
