
try:
    from browser import document, alert, svg, console, window
except:
    document = {}
    alert = None
    class svg:
        pass
    svg_elements = ['line', 'circle', 'path', 'rect']
    functions = {k: (lambda self, **kargs: kargs) for k in svg_elements}
    svg.__dict__.update(functions)

from dataclasses import dataclass, field
from diagrams import styled, Shape, HAlign, VAlign, renderText, Diagram, Relationship

@dataclass
@styled(default_style=dict(blockcolor='#FFFBD6', font='Arial', fontsize='16', textcolor='black', xmargin=2, ymargin=2, halign=HAlign.LEFT, valign=VAlign.CENTER))
class Note(Shape):
    description: str = ''
    fold_size = 10
    def getPoints(self):
        x, y, w, h = self.x, self.y, self.width, self.height
        f = self.fold_size
        return ' '.join(f'{x+a},{y+b}' for a, b in [(0,0), (w-f,0), (w,f), (w-f,f), (w-f,0), (w,f), (w,h), (0,h)])
    def getShape(self):
        g = svg.g()
        outline = svg.polygon(points=self.getPoints(), fill=self.getStyle('blockcolor'), stroke=self.getStyle('bordercolor'), stroke_width=self.getStyle('bordersize'))
        g <= outline
        for line in renderText(self.description, self.x, self.y, self.width, self.height, self):
            g <= line
        return g

    def updateShape(self, shape):
        rect = shape.children[0]
        rect['points'] = self.getPoints()
        for i, line in enumerate(shape.children[1:]):
            # Remove the text elements
            shape.removeChild(line)
        for line in renderText(self.description, self.x, self.y, self.width, self.height, self):
            shape <= line

@dataclass
class Anchor(Relationship):
    source: (Note, ) = None
    dest: (Shape, Relationship) = None
    name: str = ''


@dataclass
@styled(default_style=dict(font='Arial', fontsize='16', textcolor='black', xmargin=2, ymargin=2, halign=HAlign.CENTER, valign=VAlign.CENTER))
class NamedShape(Shape):
    description: str = ''
    def getShape(self):
        g = svg.g()
        # Add the core rectangle
        g <= svg.rect(x=self.x, y=self.y, width=self.width, height=self.height,
                      stroke_width=self.getStyle('bordersize'),
                      stroke=self.getStyle('bordercolor'),
                      fill=self.getStyle('blockcolor'))
        # Add the text
        g <= renderText(self.name, x=self.x, y=self.y, width=self.width, height=self.height, style=self)
        # Return the group of objects
        return g

    def updateShape(self, shape):
        # Update the rect
        rect = shape.children[0]
        rect['x'], rect['y'], rect['width'], rect['height'] = self.x, self.y, self.width, self.height
        # Delete the previous text
        for line in shape.children[1:]:
            # Remove the text elements
            shape.removeChild(line)
        # Add the new text
        for line in renderText(self.name, self.x, self.y, self.width, self.height):
            shape <= line

@dataclass
class Class(NamedShape):
    abstract: bool = False
    def getStyle(self, key):
        """ The formatting of this class depends on whether it is abstract or not. """
        if key == 'fontmodifier':
            return 'IB' if self.abstract else 'B'
        return super().getStyle(key)


@dataclass
@styled(default_style=dict(endmarker='triangledopen', startmarker='none'))
class Inheritance(Relationship):
    name: str = ''
    source: (Class,) = field(default_factory=list)
    Dest: (Class,) = field(default_factory=list)

@dataclass
@styled(default_style=dict(endmarker='arrowopen', startmarker='none'))
class Association(Relationship):
    name: str = ''
    source_multiplicity: str = ''
    dest_multiplicity: str = ''
    source: (Class,) = field(default_factory=list)
    Dest: (Class,) = field(default_factory=list)

@dataclass
@styled(default_style=dict(endmarker='diamondopen', startmarker='none'))
class Aggregation(Association):
    pass

@dataclass
@styled(default_style=dict(endmarker='diamond', startmarker='none'))
class Composition(Association):
    pass


class ClassDefinitionDiagram(Diagram):
    allowed_blocks = [Note, Class]

###############################################################################

@styled(default_style=dict(font='Arial', fontmodifier='U', fontsize='16', textcolor='black', xmargin=2, ymargin=2, halign=HAlign.CENTER, valign=VAlign.CENTER))
class Instance(NamedShape):
    pass

class CooperationDiagram(Diagram):
    allowed_blocks = [Note, Instance]

###############################################################################


class UseCase(NamedShape):
    pass

class Actor(NamedShape):
    pass

class UseCaseDiagram(Diagram):
    allowed_blocks = [Note, UseCase, Actor, Instance]

###############################################################################

class State(NamedShape):
    pass

class StartState(Shape):
    pass

class StopState(Shape):
    pass

class Choice(Shape):
    pass

class StateTransition(Relationship):
    source: (State, StartState, Choice)
    dest: (State, StopState, Choice)

class StateDiagram(Diagram):
    allowed_blocks = [Note, StartState, StopState, State, Choice]


diagrams = [ClassDefinitionDiagram, CooperationDiagram, UseCaseDiagram, ]