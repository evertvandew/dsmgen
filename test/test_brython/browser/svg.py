
from dataclasses import dataclass

from .html import tag

@dataclass
class DOMMatrix:
    a: float = 1.0   # m11
    b: float = 0.0   # m12
    c: float = 0.0   # m21
    d: float = 1.0   # m22
    e: float = 0.0   # m41
    f: float = 0.0   # m42

    def is2D(self) -> bool:
        return True

class svg_tag(tag):
    def getScreenCTM(self) -> DOMMatrix:
        # Return the default transformation matrix
        # No offset, rotation, scaling or skewing
        return DOMMatrix()

    def __setitem__(self, key, value):
        self.attr[key] = value
    def __getitem__(self, key):
        return self.attr[key]

class drawn_tag(svg_tag):
    stroke: str
    stroke_width: float
    fill: str

class a(svg_tag):
    pass

class altGlyph(svg_tag):
    pass

class  altGlyphDef(svg_tag):
    pass

class  altGlyphItem(svg_tag):
    pass

class  animate(svg_tag):
    pass

class  animateColor(svg_tag):
    pass

class  animateMotion(svg_tag):
    pass

class  animateTransform(svg_tag):
    pass

class  circle(drawn_tag):
    cx: float
    cy: float
    r: float

class  clipPath(svg_tag):
    pass

class  color_profile(svg_tag):
    pass

class  cursor(svg_tag):
    pass

class  defs(svg_tag):
    pass

class  desc(svg_tag):
    pass

class  ellipse(drawn_tag):
    cx: float
    cy: float
    rx: float
    ry: float

class  feBlend(svg_tag):
    pass

class  g(svg_tag):
    pass

class  image(svg_tag):
    x: float
    y: float
    width: float
    height: float
    href: str

class  line(drawn_tag):
    x1: float
    y1: float
    x2: float
    y2: float

class  linearGradient(svg_tag):
    pass

class  marker(svg_tag):
    pass

class  mask(svg_tag):
    pass

class  path(drawn_tag):
    d: str

class  pattern(svg_tag):
    pass

class  polygon(drawn_tag):
    points: str

class  polyline(drawn_tag):
    points: str

class  radialGradient(svg_tag):
    pass

class  rect(drawn_tag):
    x: float
    y: float
    width: float
    height: float

class  stop(svg_tag):
    pass

class  svg(svg_tag):
    pass

class  text(drawn_tag):
    x: float
    y: float
    dx: str = None
    dy: str = None

class textPath(svg_tag):
    href: str
class  tref(svg_tag):
    pass

class  tspan(text):
    pass


class  use(svg_tag):
    pass


