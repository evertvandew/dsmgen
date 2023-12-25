""" Stub of the Brython HTML interface """

from typing import Self, Iterable, List, Dict, Callable
from enum import Enum
import re
from copy import copy
from dataclasses import dataclass
from test_frame import prepare, test, run_tests
from .events import Event


def flatten(data):
    """ Flatten a tag and its descendants. """
    if isinstance(data, Iterable) and not isinstance(data, str) and not isinstance(data, bytes):
        for d in data:
            yield from flatten(d)
    else:
        yield data
        if children := getattr(data, 'children', False):
            yield from flatten(children)

class AttributeOperator(Enum):
    """ The various types of selections done on attributes.
        The value of each entry is the RE pattern to match on.
    """
    has = ""
    equals = '='
    contains_word = '~='
    equals_upto_hyphen = r'[|]='
    startswith = r'\^='
    endswith = '[$]='
    contains = '[*]='

###############################################################################
# Objects to store the parameters to the various selectors.
# Core selectors have a `test` function to check a single node.
# Combination selectors have a `filter` function to check relationships between nodes.
class PsuedoClass:
    name: str
class PsuedoElement:
    name: str
class Selector:
    pc: PsuedoClass
    pe: PsuedoElement

@dataclass
class BaseSelector(Selector):
    name: str
    def filter(self, node):
        for item in flatten(node):
            if self.test(item):
                yield item

@dataclass
class UniversalSelector(BaseSelector):
    name: str = ''
    def test(self, node):
        return True

class TypeSelector(BaseSelector):
    def test(self, node):
        return node.tagname().lower() == self.name.lower()

class ClassSelector(BaseSelector):
    def test(self, node):
        return self.name in node.classList

class IdSelector(BaseSelector):
    def test(self, node):
        return node.attrs.get('id', '0') == self.name

@dataclass
class AttributeSelector(BaseSelector):
    value: str|None
    operator: AttributeOperator
    flag: ''
    def __post_init__(self):
        ivalue = self.value.lower()
        if self.operator == AttributeOperator.has:
            def t(node):
                return self.name in node.attrs
            self.test = t
        else:
            def t(node):
                if self.flag == 'i':
                    value = self.value.lower()
                    attr = node.attrs.get(self.name, '').lower()
                else:
                    value = self.value
                    attr = node.attrs.get(self.name, '')
                if self.operator == AttributeOperator.equals:
                    return attr == value
                elif self.operator == AttributeOperator.contains_word:
                    return value in attr.split()
                elif self.operator == AttributeOperator.equals_upto_hyphen:
                    return attr == value or attr.startswith(value+'-')
                elif self.operator == AttributeOperator.startswith:
                    return attr.startswith(value)
                elif self.operator == AttributeOperator.endswith:
                    return attr.endswith(value)
                elif self.operator == AttributeOperator.contains:
                    return value in attr
            self.test = t

class Combinator(Enum):
    NextSibling = '[+]'
    SubsequentSibling = '~'
    Child = '>'
    Column = r'\|\|'
    Descendant = ' '

@dataclass
class SelectorList:
    selectors: Selector
    def filter(self, node):
        # Yield each element that maches a test once and only once.
        # Collect all matches in a set to make them unique.
        all_nodes = {n for s in self.selectors for n in s.filter(node)}
        for item in all_nodes:
            yield item


@dataclass
class SelectorCombinator:
    a: BaseSelector
    b: BaseSelector
    t: Combinator

    def filter(self, node):
        match self.t:
            case Combinator.NextSibling:
                # Find two subsequent matching children
                for item in flatten(node):
                    for a, b in zip(item.children[:-1], item.children[1:]):
                        if self.a.test(a) and self.b.test(b):
                            yield b
            case Combinator.SubsequentSibling:
                # Find any child matching b if there is a child matching a
                for item in flatten(node):
                    if any(self.a.test(child) for child in item.children):
                        for child in item.children:
                            if self.b.test(child):
                                yield child
            case Combinator.Child:
                for item in flatten(node):
                    if self.a.test(item):
                        for child in item.children:
                            if self.b.test(child):
                                yield child
            case Combinator.Descendant:
                for item in flatten(node):
                    if self.a.test(item):
                        yield from self.b.filter(item.children)
            case _:
                RuntimeError("Combinator not (yet) supported")

def parse_attribute_selector(s):
    for attr in AttributeOperator:
        if attr.value == '':
            if m := re.fullmatch(r'([a-zA-Z0-9_-]*)(\s*([iIsS]))?', s):
                return AttributeSelector(m.group(1), '', attr, (m.group(3) or 's').lower())
        elif m := re.fullmatch(r'([a-zA-Z0-9_-]*)'+attr.value+r'"([^"]*)"(\s*([iIsS]))?', s):
            return AttributeSelector(m.group(1), m.group(2), attr, (m.group(4) or 's').lower())
    raise RuntimeError(f'Could not parse attribute selector {s}')


def parse_selector(s):
    """ Convert a selector string into a selector object of the correct type. """
    # Check for the Universal selector
    liststack = []
    selector = None
    while s:
        start_s = copy(s)
        # Parse the various selectors
        if s[0] == '*':
            selector = UniversalSelector()
            s = s[1:]
        elif m := re.match(r'::([\w-]+)', s):
            selector.pe = m.group(1)
            s = s[m.span()[1]:]
        elif m := re.match(r':([\w-]+)', s):
            selector.pc = m.group(1)
            s = s[m.span()[1]:]
        elif m := re.match(r'([\w-]+)', s):
            selector = TypeSelector(m.group(1))
            s = s[m.span()[1]:]
        elif m := re.match(r'[.]([\w-]+)', s):
            selector = ClassSelector(m.group(1))
            s = s[m.span()[1]:]
        elif m := re.match(r'#([\w-]+)', s):
            selector = IdSelector(m.group(1))
            s = s[m.span()[1]:]
        elif m := re.match(r'\[(.+?)\]', s):
            selector = parse_attribute_selector(m.group(1))
            s = s[m.span()[1]:]

        # Parse the various combinators
        elif m := re.match(r'\s*,\s*', s):
            liststack.append(selector)
            selector = None
            s = s[m.span()[1]:]
        else:
            for comb in Combinator:
                if m := re.match(r'\s*?'+comb.value+r'\s*', s):
                    s = s[m.span()[1]:]
                    part2 = parse_selector(s)
                    s = ''
                    selector = SelectorCombinator(selector, part2, comb)
                    break
        if s == start_s:
            raise RuntimeError("Unable to parse selector")
    if liststack:
        liststack.append(selector)
        return SelectorList(liststack)
    return selector


class tag:
    """ Base class for all tags.
        Tags have a uniform interface, so no tags need custom attributes or code.
    """
    def __init__(self, content='', **kwargs):
        self.text = ''
        self.children = []
        self.parent = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.style = {}
        if content:
            if isinstance(content, str):
                if '<' in content:
                    raise RuntimeError("HTML content is not (yet) supported by this mockup")
                self.text = content
            elif isinstance(content, tag):
                self.children = [content]
            elif isinstance(content, Iterable):
                self.children = list(content)
            else:
                raise RuntimeError("Unrecognized content")
        if 'className' in kwargs:
            kwargs['Class'] = kwargs['className']
        if 'text' in kwargs:
            self.text = kwargs['text']
            del kwargs['text']
        self.attrs = kwargs
        self.classList = set(self.attrs.get('Class', '').split())
        if 'style' in kwargs:
            if isinstance(kwargs['style'], str):
                self.style = {k:v for k, v in [l.strip().split(':', maxsplit=1) for l in kwargs['style'].split(';')]}
            else:
                assert isinstance(kwargs['style'], dict)
                self.style = kwargs['style']

    def __repr__(self):
        children = ''.join(str(c) for c in self.children)
        return f"{self.tagname()}({self.text} {children})"

    def __le__(self, other: Self|str|Iterable):
        if isinstance(other, tag):
            # Check if the element is moved to another place.
            if other.parent:
                other.parent.children.remove(other)
                other.parent = None
            self.children.append(other)
            other.parent = self
        elif isinstance(other, str):
            if '<' in other:
                raise RuntimeError("HTML content is not (yet) supported by this mockup")
            else:
                self.attrs['text'] = other
        elif isinstance(other, Iterable):
            for item in other:
                self.__le__(item)

    def __getitem__(self, key):
        for item in flatten(self):
            if item.attrs.get('id', '') == key:
                return item
        # Raise an IndexError so that the "in" operator will work.
        # The KeyError is not handled by the "in" operator.
        raise IndexError(f'Id {key} not found')

    def __delitem__(self, key):
        try:
            item = self[key]
            parent = item.parent
            parent.children.remove(item)
        except IndexError:
            return

    def __add__(self, other):
        if isinstance(other, tag):
            self <= other
        elif isinstance(other, str):
            assert '<' not in other, "HTML is not (yet) supported"
            self.text += other
        else:
            raise RuntimeError(f'Cannot add object of type {type(other).__name__} to tag')
        return self

    @property
    def className(self):
        return self.attrs.get('Class', '')
    @className.setter
    def className(self, name):
        self.attrs['Class'] = name
        self.classList = set(self.attrs.get('Class', '').split())

    @property
    def html(self):
        return self.render(self.children)

    @html.setter
    def html(self, s):
        if not s:
            # Clear all children
            self.children = []
        else:
            # In future, we could implement parsing with e.g. the builtin HTMLParser.
            raise NotImplementedError("Parsing HTML is not (yet) supported by this mockup")

    def get(self, **kwargs):
        if 'selector' in kwargs:
            selector = parse_selector(kwargs['selector'])
            return list(set(selector.filter(self)))
        items = list(flatten(self.children))
        for key, value in kwargs.items():
            items = [c for c in items if getattr(c, key, '') == value]
        return items

    def clear(self):
        self.children = []

    def remove(self):
        # Unlink this element from the document DOM.
        if self.parent:
            self.parent.children.remove(self)

    def select(self, key):
        return self.get(selector=key)

    def select_one(self, key):
        result = self.select(key)
        return result[0] if result else None

    def tagname(self):
        return type(self).__name__

    def bind(self, event, cb):
        self.subscribers.setdefault(event, []).append(cb)
    def unbind(self, event, cb=None):
        if cb is None:
            self.subscribers[event] = []
        else:
            handlers = self.events(event)
            if cb in handlers:
                i = handlers.index(cb)
                handlers.remove(i)
    def events(self, event: str):
        return self.subscribers.get(event, [])
    def dispatchEvent(self, event: Event):
        if not event.target:
            event.target = self
        for h in self.subscribers.get(event.type, []):
            h(event)
        if event.bubbles and not event.cancelBubble and self.parent:
            self.parent.dispatchEvent(event)

###############################################################################
# Definition of all the tags supported by Brython.
# These could be generated more efficiently than typing all the classes out like this,
# but now editors and e.g. mypy can check on their correct usage.
class A(tag): pass

class ABBR(tag): pass

class ACRONYM(tag): pass

class ADDRESS(tag): pass

class APPLET(tag): pass

class AREA(tag): pass

class B(tag): pass

class BASE(tag): pass

class BASEFONT(tag): pass

class BDO(tag): pass

class BIG(tag): pass

class BLOCKQUOTE(tag): pass

class BODY(tag):
    def getElementById(self, id: str):
        return self[id]

    def createElement(self, tagName: str):
        cls = globals()[tagName.upper()]
        return cls()
    def appendChild(self, element):
        self.children.append(element)

class BR(tag): pass

class BUTTON(tag): pass

class CAPTION(tag): pass

class CENTER(tag): pass

class CITE(tag): pass

class CODE(tag): pass

class COL(tag): pass

class COLGROUP(tag): pass

class DD(tag): pass

class DEL(tag): pass

class DFN(tag): pass

class DIR(tag): pass

class DIV(tag): pass

class DL(tag): pass

class DT(tag): pass

class EM(tag): pass

class FIELDSET(tag): pass

class FONT(tag): pass

class FORM(tag): pass

class FRAME(tag): pass

class FRAMESET(tag): pass

class H1(tag): pass

class H2(tag): pass

class H3(tag): pass

class H4(tag): pass

class H5(tag): pass

class H6(tag): pass

class HEAD(tag): pass

class HR(tag): pass

class HTML(tag): pass

class I(tag): pass

class IFRAME(tag): pass

class IMG(tag): pass

class INPUT(tag):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'value' in kwargs:
            self.value = kwargs['value']
            del kwargs['value']
        else:
            self.value = 0 if self.attrs.get('type', 'text') == 'number' else ''

class INS(tag): pass

class ISINDEX(tag): pass

class KBD(tag): pass

class LABEL(tag): pass

class LEGEND(tag): pass

class LI(tag): pass

class LINK(tag): pass

class MAP(tag): pass

class MENU(tag): pass

class META(tag): pass

class NOFRAMES(tag): pass

class NOSCRIPT(tag): pass

class OBJECT(tag): pass

class OL(tag): pass

class OPTGROUP(tag): pass

class OPTION(tag): pass

class P(tag): pass

class PARAM(tag): pass

class PRE(tag): pass

class Q(tag): pass

class S(tag): pass

class SAMP(tag): pass

class SCRIPT(tag): pass

class SELECT(tag):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = 0

class SMALL(tag): pass

class SPAN(tag): pass

class STRIKE(tag): pass

class STRONG(tag): pass

class STYLE(tag): pass

class SUB(tag): pass

class SUP(tag): pass


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

class SVG(tag):
    def getScreenCTM(self) -> DOMMatrix:
        # Return the default transformation matrix
        # No offset, rotation, scaling or skewing
        return DOMMatrix()

class TABLE(tag): pass

class TBODY(tag): pass

class TD(tag): pass

class TEXTAREA(INPUT): pass

class TFOOT(tag): pass

class TH(tag): pass

class THEAD(tag): pass

class TITLE(tag): pass

class TR(tag): pass

class TT(tag): pass

class U(tag): pass

class UL(tag): pass

class VAR(tag): pass

class ARTICLE(tag): pass

class ASIDE(tag): pass

class AUDIO(tag): pass

class BDI(tag): pass

class CANVAS(tag): pass

class COMMAND(tag): pass

class DATA(tag): pass

class DATALIST(tag): pass

class EMBED(tag): pass

class FIGCAPTION(tag): pass

class FIGURE(tag): pass

class FOOTER(tag): pass

class HEADER(tag): pass

class KEYGEN(tag): pass

class MAIN(tag): pass

class MARK(tag): pass

class MATH(tag): pass

class METER(tag): pass

class NAV(tag): pass

class OUTPUT(tag): pass

class PROGRESS(tag): pass

class RB(tag): pass

class RP(tag): pass

class RT(tag): pass

class RTC(tag): pass

class RUBY(tag): pass

class SECTION(tag): pass

class SOURCE(tag): pass

class SUMMARY(tag): pass

class TEMPLATE(tag): pass

class TIME(tag): pass

class TRACK(tag): pass

class VIDEO(tag): pass

class WBR(tag): pass

class DETAILS(tag): pass

class DIALOG(tag):
    def showModal(self):
        if not self.parent:
            document <= self

    def close(self):
        pass

class MENUITEM(tag): pass

class PICTURE(tag): pass


###############################################################################
# Unit tests for this file, focussing on the selector parsing and filtering.
@prepare
def selector_parsing_tests():
    @test
    def base_selectors():
        assert type(parse_selector('*')) == UniversalSelector
        assert parse_selector('.pietje') == ClassSelector('pietje')
        assert parse_selector('#pietje') == IdSelector('pietje')
        assert parse_selector('pietje') == TypeSelector('pietje')
    @test
    def attribute_selectors():
        assert parse_selector('[href]') == AttributeSelector('href', '', AttributeOperator.has, 's')
        assert parse_selector('[href="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.equals, 's')
        assert parse_selector('[href~="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.contains_word, 's')
        assert parse_selector('[href|="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.equals_upto_hyphen, 's')
        assert parse_selector('[href^="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.startswith, 's')
        assert parse_selector('[href$="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.endswith, 's')
        assert parse_selector('[href*="pietje"]') == AttributeSelector('href', 'pietje', AttributeOperator.contains, 's')
        assert parse_selector('[href*="pietje" s]') == AttributeSelector('href', 'pietje', AttributeOperator.contains, 's')
        assert parse_selector('[href*="pietje" S]') == AttributeSelector('href', 'pietje', AttributeOperator.contains, 's')
        assert parse_selector('[href*="pietje" I]') == AttributeSelector('href', 'pietje', AttributeOperator.contains, 'i')
        assert parse_selector('[href*="pietje" i]') == AttributeSelector('href', 'pietje', AttributeOperator.contains, 'i')
    @test
    def combinations():
        assert parse_selector('.pietje, .puk, .keteldorp') == SelectorList([ClassSelector('pietje'), ClassSelector('puk'), ClassSelector('keteldorp')])
        assert parse_selector('.pietje || .puk  .keteldorp') == SelectorCombinator(ClassSelector('pietje'),
                                                           SelectorCombinator(ClassSelector('puk'), ClassSelector('keteldorp'), Combinator.Descendant),
                                                           Combinator.Column)
        assert parse_selector('.pietje + .puk') == SelectorCombinator(ClassSelector('pietje'), ClassSelector('puk'), Combinator.NextSibling)
        assert parse_selector('.pietje ~ .puk') == SelectorCombinator(ClassSelector('pietje'), ClassSelector('puk'), Combinator.SubsequentSibling)
        assert parse_selector('.pietje > .puk') == SelectorCombinator(ClassSelector('pietje'), ClassSelector('puk'), Combinator.Child)
    @test
    def psuedo():
        s = parse_selector('.pietje:before .puk::after')
        assert s.a.pc == 'before'
        assert s.b.pe == 'after'

@prepare
def selector_filter_tests():
    test_set = BODY(
        [
            DIV([
                SPAN(text="Dit is een test", Class="chapter text"),
                INPUT(id='myvalue', name="value1", Class='edit'),
                A(text="Klik mij", href="http://pietje.puk"),
                FORM([
                    BUTTON(),
                    INPUT()
                ])
            ], id="1", Class='pietje puk'),
            DIV([
                INPUT(name="value2", Class='edit', flag='btn-primary'),
                BUTTON(text="Click Me", onclick="onBtnClick()", Class='edit btn')
            ], id="2", Class="olivier bommel"),
            INPUT(name="value3", Class='outside')
        ]
    )
    @test
    def core_selectors():
        assert len(test_set.select('*')) == 12
        assert len(test_set.select('INPUT')) == 4
        assert len(test_set.select('.edit')) == 3
        assert len(test_set.select('#myvalue')) == 1
        assert len(test_set.select('[onclick]')) == 1
        assert len(test_set.select('[href*=".puk"]')) == 1
        assert len(test_set.select('[Class*="ie"]')) == 2
        assert len(test_set.select('[flag|="btn"]')) == 1
        assert len(test_set.select('[Class~="btn"]')) == 1
        assert len(test_set.select('[onclick^="onbtnclick" i]')) == 1
        assert len(test_set.select('[onclick$="click()" i]')) == 1
    @test
    def combination_selectors():
        assert len(test_set.select('INPUT, BUTTON')) == 6
        assert len(test_set.select('.edit, .btn')) == 3
        assert len(test_set.select('INPUT + BUTTON')) == 1
        assert len(test_set.select('INPUT ~ BUTTON')) == 2
        assert len(test_set.select('DIV INPUT')) == 3
        assert len(test_set.select('DIV > INPUT')) == 2


if __name__ == '__main__':
    run_tests()