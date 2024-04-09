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

import enum
from browser import svg, console
from fontsizes import font_sizes
from itertools import chain
from square_routing import Point, routeSquare

try:
    import pyphen
    pyphen.language_fallback('nl_NL_variant1')
except:
    pyphen = None



###############################################################################
# Support for rendering text
class VAlign(enum.IntEnum):
    TOP = 1
    CENTER = 2
    BOTTOM = 3

class HAlign(enum.IntEnum):
    LEFT = 10
    CENTER = 11
    RIGHT = 12
    JUSTIFIED = 13

POINT_TO_PIXEL = 1.3333

def getTextWidth(text, font_file='Arial.ttf', fontsize='10'):
    font = font_sizes[font_file]['sizes']
    normalized_width = 1 / POINT_TO_PIXEL / int(fontsize)
    normalized_size = sum(font.get(ord(ch), font[32]) for ch in text)
    return normalized_size / normalized_width


def wrapText(text, width, font_file='Arial.ttf', fontsize='10'):
    # Separate into words and determine the size of each part
    font = font_sizes[font_file]['sizes']
    parts = text.split()
    normalized_width = width / POINT_TO_PIXEL / int(fontsize)
    sizes = [sum(font.get(ord(ch), font[32]) for ch in part) for part in parts]
    if pyphen:
        dic = pyphen.Pyphen(lang='nl_NL')

    # Now fill the lines
    line_length = 0
    lines = []
    current_line = []
    for size, part in zip(sizes, parts):
        if pyphen:
            while line_length + size + font[32]*(len(current_line)-1) > normalized_width:
                # Only hyphenate if the remaining space is more than 4 characters
                if normalized_width - line_length > 4*size/len(part):
                    # Find the largest part that fits
                    for a, b in dic.iterate(part):
                        a = a + '-'
                        size = sum(font.get(ord(ch), font[32]) for ch in a)
                        if line_length + size + font[32]*(len(current_line)-1) <= normalized_width:
                            current_line.append(a)
                            part = b
                            line_length += size
                            size = sum(font.get(ord(ch), font[32]) for ch in b)
                            break
                    else:
                        # No part fitted. Check this is not an empty line, otherwise the word will never fit.
                        if not current_line:
                            # Just add the word and let the user deal with it.
                            size = sum(font.get(ord(ch), font[32]) for ch in part)
                            break
                lines.append(' '.join(current_line))
                current_line = []
                line_length = 0
        elif current_line and line_length + size + font[32] * (len(current_line) - 1) > normalized_width:
            lines.append(' '.join(current_line))
            current_line = []
            line_length = 0
        current_line.append(part)
        line_length += size
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def renderText(text, d):
    font_file = d.getStyle('font', 'Arial')+'.ttf'
    fontsize = float(d.getStyle('fontsize', 12))
    xmargin = int(d.getStyle('xmargin', '5'))
    ymargin = int(d.getStyle('ymargin', xmargin))
    lines = wrapText(text, d.width-2*xmargin, font_file, fontsize)
    # Now render these lines
    anchor = {HAlign.LEFT: 'start', HAlign.CENTER: 'middle', HAlign.RIGHT: 'end'}[d.getStyle('halign', HAlign.LEFT)]
    lineheight = font_sizes[font_file]['lineheight'] * fontsize * float(d.getStyle('linespace', '1.5'))
    # Calculate where the text must be placed.
    xpos = int({HAlign.LEFT: d.x+xmargin, HAlign.CENTER: d.x+d.width/2, HAlign.RIGHT: d.x+d.width-xmargin}[d.getStyle('halign', HAlign.LEFT)])
    ypos = {VAlign.TOP: d.y+ymargin,
            VAlign.CENTER: d.y+(d.height-(len(lines)+.5)*lineheight)/2,
            VAlign.BOTTOM: d.y+d.height-len(lines)*lineheight*fontsize - ymargin
           }[d.getStyle('valign', VAlign.CENTER)]

    rendered = [svg.text(line, x=xpos, y=int(ypos+lineheight*(i+1)), text_anchor=anchor, font_size=fontsize,
                         font_family=d.getStyle('font', 'Arial'), fill=d.getStyle('textcolor'))
                for i, line in enumerate(lines)]
    return rendered


def drawSquaredLine(start, end, gridline):
    p1, p2 = [Point(p.x, p.y) + Point(p.width, p.height)/2 for p in [start, end]]
    points = routeSquare((p1, Point(0,0)), (p2, Point(0,0)), [gridline])

    waypoints = ''.join(f'L {p.x} {p.y} ' for p in points[1:])
    start, end = points[0], points[-1]
    path = f"M {start.x} {start.y} {waypoints}"

    return svg.path(d=path, stroke='black', stroke_width=2, fill=None,
                             marker_end='url(#endarrow)')


###############################################################################
# Some predetermined shapes

class BasicShape:
    style_items = {'bordercolor': '#000000', 'bordersize': '2', 'blockcolor': '#ffffff'}
    @classmethod
    def getShape(cls, details):
        raise NotImplementedError
    @classmethod
    def updateShape(cls, shape, details):
        raise NotImplementedError
    @staticmethod
    def getDescriptor(name):
        name = name.lower()
        for cls in BasicShape.getShapeTypes():
            if cls.__name__.lower() == name.lower():
                return cls
        raise RuntimeError(f"Unknown shape type {name}")
    @classmethod
    def getShapeTypes(cls):
        return cls.__subclasses__() + list(chain.from_iterable(c.getShapeTypes() for c in cls.__subclasses__()))

    @classmethod
    def getType(cls):
        return cls.__name__.lower()

    @classmethod
    def getStyle(cls, key, details):
        # Find a default value for the style item
        default = cls.style_items.get(key, None)
        if default is None:
            for c in cls.mro():
                if key in c.style_items:
                    default = c.style_items[key]
                    break
        return details.getStyle(key, default)

    @classmethod
    def getDefaultStyle(cls):
        """ Return a new dictionary with defaults for all stylable items in the shape and its bases. """
        style = {}
        for base in reversed(cls.mro()):
            style.update(getattr(base, 'style_items', {}))
        style.update(cls.style_items)
        return style


class Rect(BasicShape):
    style_items = {'cornerradius': '0'}
    @classmethod
    def getShape(cls, details):
        return svg.rect(x=str(details.x), y=str(details.y), width=str(details.width), height=str(details.height),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('bordercolor', details),
                        fill=cls.getStyle('blockcolor', details),
                        ry=cls.getStyle('cornerradius', details))
    @classmethod
    def updateShape(cls, shape, details):
        shape['width'], shape['height'] = str(details.width), str(details.height)
        shape['x'], shape['y'] = str(details.x), str(details.y)
        shape['ry'] = cls.getStyle('cornerradius', details)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"

class Circle(BasicShape):
    style_items = {}
    @classmethod
    def getShape(cls, details):
        return svg.circle(cx=str(details.x+details.width//2), cy=str(details.y+details.height//2),
                        r=str(min([details.width, details.height])//2),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('bordercolor', details),
                        fill=cls.getStyle('blockcolor', details))
    @classmethod
    def updateShape(cls, shape, details):
        shape['r'] = str((details.width + details.height) // 4)
        shape['cx'], shape['cy'] = str(details.x+details.width//2), str(details.y+details.height//2)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width};stroke:{stroke};fill:{fill}"

class Square(BasicShape):
    style_items = {}
    @classmethod
    def getShape(cls, details):
        return svg.rect(x=str(details.x), y=str(details.y),
                        width=str((details.width+details.height)//2),
                        height=str((details.width+details.height)//2),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('bordercolor', details),
                        fill=cls.getStyle('blockcolor', details))
    @classmethod
    def updateShape(cls, shape, details):
        shape['width'] = str((details.width + details.height) // 2)
        shape['height'] = str((details.width + details.height) // 2)
        shape['x'], shape['y'] = str(details.x), str(details.y)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"

class Ellipse(BasicShape):
    style_items = {}
    @classmethod
    def getShape(cls, details):
        return svg.ellipse(cx=str(details.x+details.width//2), cy=str(details.y+details.height//2),
                        rx=str(details.width//2), ry=str(details.height//2),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('bordercolor', details),
                        fill=cls.getStyle('blockcolor', details))
    @classmethod
    def updateShape(cls, shape, details):
        shape['rx'], shape['ry'] = str(details.width//2), str(details.height//2)
        shape['cx'], shape['cy'] = str(details.x+details.width//2), str(details.y+details.height//2)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"

class Note(BasicShape):
    style_items = {'fold_size': '10'}
    @classmethod
    def getPoints(cls, details):
        x, y, w, h = details.x, details.y, details.width, details.height
        f = int(cls.getStyle('fold_size', details))
        return [(x+a,y+b) for a, b in [(0,0), (w-f,0), (w,f), (w-f,f), (w-f,0), (w,f), (w,h), (0,h), (0,0)]]
    @classmethod
    def getShape(cls, details):
        outline = svg.polyline(points=' '.join(f'{x},{y}' for x, y in cls.getPoints(details)),
                              fill=cls.getStyle('blockcolor', details), stroke=cls.getStyle('bordercolor', details),
                              stroke_width=cls.getStyle('bordersize', details))
        return outline
    @classmethod
    def updateShape(cls, shape, details):
        shape['points'] = ' '.join(f'{x},{y}' for x, y in cls.getPoints(details))
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"

class Component(BasicShape):
    style_items = {'ringwidth': '15', 'ringheight': '10', 'ringpos': '25', 'cornerradius': '0'}
    @classmethod
    def getShape(cls, details):
        g = svg.g()
        # Add the basic rectangle
        g <= Rect.getShape(details)
        # Add the two binder rings
        rw, rh, rp = [int(cls.getStyle(i, details)) for i in 'ringwidth ringheight ringpos'.split()]
        rp = rp * details.height // 100
        g <= svg.rect(x=str(details.x-rw//2),
                      y=str(details.y+rp),
                      width=cls.getStyle('ringwidth', details),
                      height=cls.getStyle('ringheight', details),
                      stroke_width=cls.getStyle('bordersize', details),
                      stroke=cls.getStyle('bordercolor', details),
                      fill=cls.getStyle('blockcolor', details))
        g <= svg.rect(x=str(details.x-rw//2),
                      y=str(details.y+details.height-rp-rh),
                      width=cls.getStyle('ringwidth', details),
                      height=cls.getStyle('ringheight', details),
                      stroke_width=cls.getStyle('bordersize', details),
                      stroke=cls.getStyle('bordercolor', details),
                      fill=cls.getStyle('blockcolor', details))
        return g
    @classmethod
    def updateShape(cls, shape, details):
        # Update the large square
        Rect.updateShape(shape.children[0], details)
        # Update the rings
        rw, rh, rp = [int(cls.getStyle(i, details)) for i in 'ringwidth ringheight ringpos'.split()]
        rp = rp * details.height // 100
        r1, r2 = shape.children[1:]
        r1['x'] = str(details.x-rw//2)
        r2['x'] = str(details.x-rw//2)
        r1['y'] = str(details.y+rp)
        r2['y'] = str(details.y+details.height-rp-rh)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        style = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"
        for child in shape.children:
            child['style'] = style

class Diamond(Note):
    @classmethod
    def getPoints(cls, details):
        return [(details.x+a, details.y+b) for a, b in [
            (details.width//2,0),
            (details.width,details.height//2),
            (details.width//2,details.height),
            (0,details.height//2),
            (details.width//2,0)]]

class Folder(Note):
    style_items = {'tabheight': 5, 'tabwidth': 50}
    @classmethod
    def getPoints(cls, details):
        h = cls.getStyle('tabheight', details)
        w = int(cls.getStyle('tabwidth', details))*details.width//100
        return [(details.x+a, details.y+b) for a, b in [
            (0, -h),
            (w, -h),
            (w, 0),
            (details.width, 0),
            (details.width, details.height),
            (0, details.height),
            (0, -h)]]

class ClosedCircle(Circle):
    @classmethod
    def getShape(cls, details):
        shape = Circle.getShape(details)
        shape['fill'] = cls.getStyle('bordercolor', details)
        return shape
    @classmethod
    def updateShape(cls, shape, details):
        Circle.updateShape(shape, details)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        shape['style'] = f"stroke_width:{stroke_width};stroke:{stroke};fill:{stroke}"

class RingedClosedCircle(BasicShape):
    style_items = {'space': '25'}
    @classmethod
    def getShape(cls, details):
        r = min([details.width, details.height]) // 2
        space = int(cls.getStyle('space', details)) * r // 100
        ball = ClosedCircle.getShape(details)
        ball['r'] = int(r - space)
        ring = Circle.getShape(details)
        ring['fill'] = 'none'
        g = svg.g()
        g <= ball
        g <= ring
        return g
    @classmethod
    def updateShape(cls, shape, details):
        r = (details.width + details.height) // 4
        space = int(cls.getStyle('space', details)) * r // 100
        ClosedCircle.updateShape(shape.children[0], details)
        Circle.updateShape(shape.children[1], details)
        shape.children[0]['r'] = int(r - space)
        shape.children[1]['fill'] = 'none'

class Bar(Rect):
    style_items = {'blockcolor': 'black'}
    @classmethod
    def getShape(cls, details):
        return svg.rect(x=str(details.x), y=str(details.y), width=str(details.width), height=str(details.height),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('blockcolor', details),
                        fill=cls.getStyle('blockcolor', details),
                        ry=cls.getStyle('cornerradius', details))
    @classmethod
    def updateShape(cls, shape, details):
        shape['width'], shape['height'] = str(details.width), str(details.height)
        shape['x'], shape['y'] = str(details.x), str(details.y)
        shape['ry'] = cls.getStyle('cornerradius', details)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('blockcolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"stroke_width:{stroke_width}; stroke:{stroke}; fill:{fill}"


class Hexagon(Note):
    style_items = {'bump': '15'}
    @classmethod
    def getPoints(cls, details):
        bump = int(cls.getStyle('bump', details))
        return [(details.x+a, details.y+b) for a, b in [
            (0, 0),
            (details.width, 0),
            (details.width+bump, details.height//2),
            (details.width, details.height),
            (0, details.height),
            (-bump, details.height//2),
            (0,0)]]

class Octagon(Hexagon):
    @classmethod
    def getPoints(cls, details):
        bump = int(cls.getStyle('bump', details))
        return [(details.x+a, details.y+b) for a, b in [
            (0, 0),
            (details.width, 0),
            (details.width+bump, details.height//4),
            (details.width+bump, 3*details.height//4),
            (details.width, details.height),
            (0, details.height),
            (-bump, 3*details.height//4),
            (-bump, details.height//4),
            (0,0)]]

class Box(Note):
    style_items = {'offset': '10'}
    @classmethod
    def getPoints(cls, details):
        offset = int(cls.getStyle('offset', details))
        return [(details.x + a, details.y + b) for a, b in [
            (0, 0),
            (details.width, 0),
            (details.width, details.height),
            (0, details.height),
            (0, 0),
            (offset, -offset),
            (details.width+offset, -offset),
            (details.width, 0),
            (details.width + offset, -offset),
            (details.width + offset, -offset+details.height),
            (details.width, details.height)
        ]]

class Drum(BasicShape):
    style_items = {'curve_height': '15'}
    @classmethod
    def getPath(cls, details):
        h, w = details.height, details.width
        x1, y1 = details.x, details.y
        x2, y2 = x1+w, y1+h
        ch = int(cls.getStyle('curve_height', details)) * w // 100
        return ' '.join([f'M {x1} {y1}',
                         f'v {h}',
                         f'C {x1} {y2+ch} {x2} {y2+ch} {x2} {y2}',
                         f'v -{h}',
                         f'C {x2} {y1+ch} {x1} {y1+ch} {x1} {y1}',
                         f'C {x1} {y1-ch} {x2} {y1-ch} {x2} {y1}'])

    @classmethod
    def getShape(cls, details):
        return svg.path(d=cls.getPath(details),
                        stroke_width=cls.getStyle('bordersize', details),
                        stroke=cls.getStyle('bordercolor', details),
                        fill=cls.getStyle('blockcolor', details))

    @classmethod
    def updateShape(cls, shape, details):
        shape['d'] = cls.getPath(details)
        stroke_width = cls.getStyle('bordersize', details)
        stroke = cls.getStyle('bordercolor', details)
        fill = cls.getStyle('blockcolor', details)
        shape['style'] = f"fill:{fill}; stroke_width:{stroke_width}; stroke:{stroke}"

class Stickman(Drum):
    style_items = {'proportions': '25 33 66'}
    @classmethod
    def getPath(cls, details):
        proportions = [int(i) for i in cls.getStyle('proportions', details).split()]
        x1 = details.x
        x2 = details.x + details.width//2
        x3 = details.x + details.width
        y1 = details.y
        r = details.height * proportions[0] // 200
        y2 = y1 + proportions[0] * details.height // 100
        y3 = y1 + proportions[1] * details.height // 100
        y4 = y1 + proportions[2] * details.height // 100
        y5 = y1 + details.height
        return f'M {x2-1} {y2} a {r} {r} 0 1 1 1 0 L {x2} {y4} M {x1} {y3} L {x3} {y3} M {x1} {y5} L {x2} {y4} L {x3} {y5}'


class ObliqueRect(Drum):
    style_items = {'step': '10'}
    @classmethod
    def getPath(cls, details):
        step = int(cls.getStyle('step', details))
        return f'M {details.x} {details.y} h {details.width+step} l -{step} {details.height} h -{details.width+step} l {step} -{details.height}'

class Tunnel(Drum):
    style_items = {'curvature': 20}
    @classmethod
    def getPath(cls, details):
        curve = int(cls.getStyle('curvature', details)) * details.height // 100
        return f'M {details.x} {details.y} h {details.width} c {-curve} {details.height//3} {-curve} {2*details.height//3} 0 {details.height} h -{details.width}  c {-curve} -{details.height//3} {-curve} -{2*details.height//3} 0 -{details.height}'

class Document(Drum):
    style_items = {'step': '15'}
    @classmethod
    def getPath(cls, details):
        step = int(cls.getStyle('step', details))
        return f'M {details.x} {details.y} h {details.width} v {details.height} c -{details.width/2} -{step} -{details.width/2} {step} -{details.width} 0 v -{details.height}'

class Tape(Drum):
    style_items = {'step': '15'}
    @classmethod
    def getPath(cls, details):
        step = int(cls.getStyle('step', details))
        return f'M {details.x} {details.y} c {details.width/2} {step} {details.width/2} -{step} {details.width} 0 v {details.height} c -{details.width/2} -{step} -{details.width/2} {step} -{details.width} 0 v -{details.height}'

class TriangleDown(Drum):
    style_items = {}
    @classmethod
    def getPath(cls, details):
        return f'M {details.x} {details.y} h {details.width} l -{details.width//2} {details.height} L {details.x} {details.y}'

class TriangleUp(Drum):
    style_items = {}
    @classmethod
    def getPath(cls, details):
        return f'M {details.x} {details.y+details.height} h {details.width} l -{details.width//2} -{details.height} L {details.x} {details.y+details.height}'

class Hourglass(Drum):
    style_items = {}
    @classmethod
    def getPath(cls, details):
        return f'M {details.x} {details.y} h {details.width} l -{details.width} {details.height} h {details.width} l -{details.width} -{details.height}'

class Label(Note):
    style_items = {'bump': '15'}
    @classmethod
    def getPoints(cls, details):
        bump = int(cls.getStyle('bump', details))
        return [(details.x+a, details.y+b) for a, b in [
            (0, 0),
            (details.width, 0),
            (details.width+bump, details.height//2),
            (details.width, details.height),
            (0, details.height),
            (0,0)]]


def normalize_path(d: str):
    parts = [p if ',' not in p else [float(f) for f in p.split(',')] for p in d.split()]
    # Make the path relative
    relative_parts = []
    assert parts[0] == 'M'
    position = parts[1]
    count = 0
    command = None
    relative_parts.extend(parts[:2])
    min_pos = parts[1]
    max_pos = parts[1]
    for p in parts[2:]:
        if isinstance(p, str):
            command = p
            relative_parts.append(p.lower())
            count = 0
            continue
        if command == 'C':
            match count:
                case 0: # First control point
                    relative_parts.append([p[0] - position[0], p[1] - position[1]])
                    count = 1
                case 1: # Second control point
                    relative_parts.append([p[0] - position[0], p[1] - position[1]])
                    count = 2
                case 2: # Endpoint
                    relative_parts.append([p[0] - position[0], p[1] - position[1]])
                    position = p
                    count = 0   # In case we have a poly-bezier path here.
        if command == 'c':
            match count:
                case 0: # First control point
                    relative_parts.append(p)
                    count = 1
                case 1: # Second control point
                    relative_parts.append(p)
                    count = 2
                case 2: # Endpoint
                    relative_parts.append(p)
                    position = [p[0] + position[0], p[1] + position[1]]
                    count = 0   # In case we have a multi-bezier path here.
        if command in 'ML':
            relative_parts.append([p[0] - position[0], p[1] - position[1]])
            position = p
        if command == 'ml':
            relative_parts.append(p)
            position = [p[0] + position[0], p[1] + position[1]]
        if command in 'HV':
            hv = 0 if command.lower() == 'h' else 1
            relative_parts.append(float(p) - position[hv])
            position = [p if i==hv else f for i,f in enumerate(position)]
        if command == 'hv':
            hv = 0 if command.lower() == 'h' else 1
            relative_parts.append(float(p))
            position = [p+f if i==hv else f for i,f in enumerate(position)]
        min_pos = [a if a < b else b for a, b in zip(position, min_pos)]
        max_pos = [a if a > b else b for a, b in zip(position, max_pos)]

    # Scale the path to [0,0], [1,1]
    scale = [max_pos[0]-min_pos[0], max_pos[1]-min_pos[1]]
    normalize_parts = []
    for p in relative_parts:
        if isinstance(p, str):
            command = p
            normalize_parts.append(p)
            continue
        if command == 'h':
            normalize_parts.append(p/scale[0])
        elif command == 'v':
            normalize_parts.append(p/scale[1])
        else:
            normalize_parts.append([p[0] / scale[0], p[1] / scale[1]])
    # Apply the offset (only the first coordinate is absolute)
    normalize_parts[1] = [a-(b/s) for a, b, s in zip(normalize_parts[1], min_pos, scale)]
    return normalize_parts

class Cloud(Drum):
    style_items = {}
    # Normalize a path generated by InkScape for easy moving and scaling.
    # All steps must be relative to the first position.
    d = 'M 33.158846,50.637579 C 24.723638,32.861747 44.647127,18.397258 62.128717,33.206332 73.12788,10.907646 106.48349,17.249888 104.54954,35.879815 c 21.01165,6.106901 10.9017,34.898043 -5.715567,32.584623 0.721563,13.176636 -21.693818,15.09918 -28.593097,6.650085 C 63.325548,83.805268 44.881237,81.566417 43.120355,70.929496 27.384339,81.579617 15.079869,55.78997 33.158846,50.637579 Z'
    parts = normalize_path(d)

    @classmethod
    def getPath(cls, details):
        # Scale the co-ordinates
        size = [details.width, details.height]
        parts = [[f*size[i] for i,f in enumerate(p)] if isinstance(p, list) else p for p in cls.parts]
        # Set the origin of the shape
        parts[1] = [parts[1][0]+details.x, parts[1][1]+details.y]
        # Return the results as a string.
        return ' '.join([','.join(str(f) for f in p) if isinstance(p, list) else p for p in parts])

###################################################################################################
# Define possible line endings. 
# Also open and closed variants are generated. Open ones are named "<name>open"

# The strings to define endings follow SVG "Path" conventions.
# The coordinates are as follows:
#   * The x coordinate is in the direction to the line, the y perpendicular to it.
#   * The line touches the connection point at (10, 5)
#   * The marker is to be drawn inside the rectangle -5 <= x <= 10 and 0 <= y <= 10)


closed_line_endings = {
    'arrow': "M 0 1.5 L 0 8.5 L 10 5 z",
    'halfarrow': 'M 0 5 L 0 8.5 L 10 5 z',
    'pointer': "M 1 5 L 0 8 L 10 5 L 0 2 z",
    'triangle': "M 0 0 L 0 10 L 10 5 z",
    'diamond': "M 0 5 L 5 10 L 10 5 L 5 0 z",
    'longdiamond': 'M -5 5 L 2.5 10 L 10 5 L 2.5 0 z',
    'square': "M 0 0 L 0 10 L 10 10 L 10 0 z"
}
wire_line_endings = {
    'hat': 'M 10 5 L 5 10 M 10 5 L 5 0',
    'linearrow': 'M 10 5 L 0 10 M 10 5 L 0 0',
    'halflinearrow': 'M 10 5 L 0 10',
    'one': 'M 5 0 v 10',
    'only_one': 'M 5 0 v 10 h -5 v -10',
    'zero_or_one': 'M 5 0 v 10 M 2 5 a 3,3 0 1,0 6,0 a 3,3 0 1,0 -6,0',
    'many': 'M 0 5 l 10 5 M 0 5 l 10 -5',
    'zero_or_many': 'M 0 5 l 10 5 M 0 5 l 10 -5 M -3 5 a 3,3 0 1,0 6,0 a 3,3 0 1,0 -6,0',
    'one_or_many': 'M 0 0 v 10 M 0 5 l 10 5 M 0 5 l 10 -5'
}

line_patterns = {
    'dashed': 'stroke-dasharray="20,20"',
    'dotted': 'stroke-dasharray="5,5"',
    'solid': ''
}

all_line_endings = list(closed_line_endings) + [f'{n}open' for n in closed_line_endings] + list(wire_line_endings)

def getMarkerDefinitions():
    defs = svg.defs()
    for name, path in closed_line_endings.items():
        marker = svg.marker(id=name, viewBox="-5 0 15 10", refX="10", refY="5", markerWidth="15", markerHeight="10",
                            orient="auto-start-reverse")
        marker <= svg.path(d=path, fill="black")
        defs <= marker
        marker = svg.marker(id=name + 'open', viewBox="-5 0 15 10", refX="10", refY="5", markerWidth="15", markerHeight="10",
                            orient="auto-start-reverse")
        marker <= svg.path(d=path, fill="white", stroke='black')
        defs <= marker

    for name, path in wire_line_endings.items():
        marker = svg.marker(id=name, viewBox="-5 0 15 10", refX="10", refY="5", markerWidth="15", markerHeight="10",
                            orient="auto-start-reverse")
        marker <= svg.path(d=path, fill="none", stroke='black')
        defs <= marker

    return defs

###############################################################################
# Some icons / glyphs used in the application
def chain_icon(x, y, s, stroke='#000000', fill='#ffffff'):
    g = svg.g()
    w = s * 4/100
    g <= svg.rect(x=x,y=y+s*4/10,width=s/2.5, height=s/5,ry=s/10, stroke=stroke, fill=fill, stroke_width=w)
    g <= svg.rect(x=x+s*1.5/2.5,y=y+s*4/10,width=s/2.5, height=s/5,ry=s/10, stroke=stroke, fill=fill, stroke_width=w)
    g <= svg.rect(x=x+s*3/10, y=y+s*9/20, width=s/2.5, height=s/10, fill=stroke, stroke=fill, stroke_width=1.2*w)
    return g

def pointer_icon(x, y, s, stroke='#000000', fill='#ffffff'):
    points = '-5 -.7, 1 -.5, 0 -3, 10 0, 0 3, 1 .5, -5 .5'
    points = [[float(i.strip()) for i in c.strip().split()] for c in points.split(',')]
    points = [(s*(i+5)/15+x, s*j/15+y+s/2) for i, j in points]
    points = ', '.join(f'{i} {j}' for i, j in points)
    return svg.polygon(points=points, stroke='black')



