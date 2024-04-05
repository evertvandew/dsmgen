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
from math import inf
from point import Point
import enum

class XP(enum.IntEnum):
    LEFT = 1
    OVERLAP = 2
    RIGHT = 3
class YP(enum.IntEnum):
    BELOW = 1
    OVERLAP = 2
    ABOVE = 3

Directions = enum.IntEnum('Directions', "TOP LEFT BOTTOM RIGHT")

def routeSquare(start_block, finish_block, waypoints):
    def extend_wp(w):
        # Each wp will have one co-ordinate at infinity.
        if abs(w.x) == inf:
            return (Point(x=-inf, y=w.y), Point(x=inf, y=w.y))
        return (Point(x=w.x, y=-inf), Point(x=w.x, y=inf))

    ranges = [(start_block[0], start_block[0] + start_block[1])]
    ranges.extend([extend_wp(wp) for wp in waypoints])
    ranges.append((finish_block[0], finish_block[0] + finish_block[1]))
    centers = [(r[0]+r[1])/2 for r in ranges]

    points = []

    for i, j in zip(range(len(ranges)-1), range(1, len(ranges))):

        current_range, next_range = ranges[i], ranges[j]
        current_center, next_center = centers[i], centers[j]

        # Check if there can be a direct line between the ranges
        xpos = XP.LEFT if next_range[1].x < current_range[0].x else (
            XP.RIGHT if next_range[0].x > current_range[1].x else XP.OVERLAP
        )
        ypos = YP.BELOW if next_range[1].y < current_range[0].y else (
            YP.ABOVE if next_range[0].y > current_range[1].y else YP.OVERLAP
        )

        # Detect a waypoint that runs through the start of finish object
        handled = False
        if i==0:
            if next_range[0].x == -inf and (current_range[0].y <= next_center.y <= current_range[1].y):
                # peek ahead to see which side of the object we need to be
                if centers[j+1].x < current_center.x:
                    points.append(Point(x=current_range[0].x, y=next_center.y))
                else:
                    points.append(Point(x=current_range[1].x, y=next_center.y))
                handled = True
            elif next_range[0].y == -inf and (current_range[0].x <= next_center.x <= current_range[1].x):
                # peek ahead to see which side of the object we need to be
                if centers[j + 1].y < current_center.y:
                    points.append(Point(x=next_center.x, y=current_range[0].y))
                else:
                    points.append(Point(x=next_center.x, y=current_range[1].y))
                handled = True
        if j == len(ranges)-1:
            if current_range[0].x == -inf and (next_range[0].y <= current_center.y <= next_range[1].y):
                # Look behind to see which side of the object we need to be
                if centers[i-1].x < next_center.x:
                    points.append(Point(x=next_range[0].x, y=current_center.y))
                else:
                    points.append(Point(x=next_range[1].x, y=current_center.y))
                handled = True
            elif current_range[0].y == -inf and (next_range[0].x <= current_center.x <= next_range[1].x):
                # look behind to see which side of the object we need to be
                if centers[i- 1].y < next_center.y:
                    points.append(Point(x=current_center.x, y=next_range[0].y))
                else:
                    points.append(Point(x=current_center.x, y=next_range[1].y))
                handled = True

        # Check if a waypoint is connecting to a waypoint
        if (not handled) and current_range[1].x == inf and next_range[1].y == inf:
            handled = True
            points.append(Point(x=next_range[0].x, y=current_range[0].y))
        if (not handled) and current_range[1].y == inf and next_range[1].x == inf:
            handled = True
            points.append(Point(x=current_range[0].x, y=next_range[0].y))
        #Detect situations where there is overlap between objects or waypoints
        if handled:
            pass
        elif ypos == YP.OVERLAP:
            if current_center.x < next_center.x:
                x1 = current_range[1].x
                x2 = next_range[0].x
            else:
                x1 = current_range[0].x
                x2 = next_range[1].x

            # If the whole block is overlapped, draw the line from the center of the smallest
            if current_range[0].y < next_range[0].y:
                if current_range[1].y > next_range[1].y:
                    y = next_center.y
                else:
                    y = (current_range[1].y + next_range[0].y) / 2
            else:
                if current_range[1].y > next_range[1].y:
                    y = (next_range[1].y + current_range[0].y) / 2
                else:
                    y = current_center.y

            points.append(Point(x=x1, y=y))
            points.append(Point(x=x2, y=y))
        elif xpos == XP.OVERLAP:
            # A vertical line
            if current_center.y < next_center.y:
                y1 = current_range[1].y
                y2 = next_range[0].y
            else:
                y1 = current_range[0].y
                y2 = next_range[1].y

            # If the whole block is overlapped, draw the line from the center of the smallest range
            if current_range[0].x < next_range[0].x:
                if current_range[1].x > next_range[1].x:
                    x = next_center.x
                else:
                    x = (current_range[1].x + next_range[0].x) / 2
            else:
                if current_range[1].x > next_range[1].x:
                    x = (next_range[1].x + current_range[0].x) / 2
                else:
                    x = current_center.x


            points.append(Point(x=x, y=y1))
            points.append(Point(x=x, y=y2))
        else:
            # No overlap: draw a line in three parts.
            v = next_center - current_center
            if abs(v.y) > abs(v.x):
                if v.y > 0:
                    quadrant = Directions.TOP
                    start = Point(current_center.x, current_range[1].y)
                    end = Point(next_center.x, next_range[0].y)
                else:
                    quadrant = Directions.BOTTOM
                    start = Point(current_center.x, current_range[0].y)
                    end = Point(next_center.x, next_range[1].y)
            elif v.x > 0:
                quadrant = Directions.RIGHT
                start = Point(current_range[1].x, current_center.y)
                end = Point(next_range[0].x, next_center.y)
            else:
                quadrant = Directions.LEFT
                start = Point(current_range[0].x, current_center.y)
                end = Point(next_range[1].x, next_center.y)

            middle = (start + end) / 2
            if quadrant in [Directions.TOP, Directions.BOTTOM]:
                    p1 = Point(current_center.x, middle.y)
                    p2 = Point(next_center.x, middle.y)
            else:
                    p1 = Point(middle.x, current_center.y)
                    p2 = Point(middle.x, next_center.y)

            points.extend([start, p1, p2, end])
    return points
