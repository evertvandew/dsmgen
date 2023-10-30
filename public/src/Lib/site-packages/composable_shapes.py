
import svg_shapes as ss
from shapes import Shape
from fontsizes import font_sizes
from dataclasses import dataclass, field


@dataclass
class TextShape:
    text: str = ''

    @classmethod
    def minSizes(cls, details):
        font_file = details.getStyle('font', 'Arial') + '.ttf'
        fontsize = float(details.getStyle('fontsize', 12))
        font = font_sizes[font_file]['sizes']
        width = sum([font.get(ord(ch), font[32]) for ch in details.text])
        return ss.POINT_TO_PIXEL * fontsize * width, fontsize * ss.POINT_TO_PIXEL


@dataclass
class PlainStackableShape(Shape):
    text: TextShape = field(default_factory=TextShape)
    lug_offset = 20
    lug_width = 20
    lug_height = 5
    margin = 5

    shape = None

    def minSizes(self):
        """ Return the minimum sizes for the width and the height """
        width, height = self.text.min_sizes()
        width = max(width, self.lug_width + self.lug_offset)
        return width + 2* self.margin, height + 2*self.margin + self.lug_height
    def setOuterSizes(self, width, height):
        self.outsize = (width, height)
    def getShape(self):
        g = ss.svg.g()
        # Add the outline
        g <= ss.svg.polyline(
            points='',
            fill=self.getStyle('blockcolor'), stroke=self.getStyle('bordercolor'),
            stroke_width=self.getStyle('bordersize'))
        # Add the text
        g <= self.TextWidget.getShape(self)
        self.updateShape(g)
        return g
    def updateShape(self, shape):
        outline = shape.children[0]
        text = shape.children[1]
        outline['points'] = ' '.join(f'{x+self.x},{y+self.y}' for x, y in self.getPoints())
        self.text.updateShape(text)

    def getPoints(self, d):
        return [(0,0),
                    (self.lug_offset,0), (self.lug_offset,self.lug_height), (self.lug_offset+self.lug_width,self.lug_height), (self.lug_offset+self.lug_width,0),
                    (self.width,0),
                    (self.width,self.height),
                    (self.lug_offset+self.lug_width,self.height),(self.lug_offset+self.lug_width,self.lug_height+self.height), (self.lug_offset,self.lug_height+self.height),(self.lug_offset,self.height),
                    (0,self.height)]

