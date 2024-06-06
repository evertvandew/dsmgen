""" Stub of the Brython HTML interface """

from typing import Self, Iterable, List, Dict, Callable, Optional, Any, Tuple, Union
from enum import Enum
import re
from copy import copy
from dataclasses import dataclass
from test_frame import prepare, test, run_tests


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
                    attr = str(node.attrs.get(self.name, '')).lower()
                else:
                    value = self.value
                    attr = str(node.attrs.get(self.name, ''))
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
    Either = ','

@dataclass
class SelectorList:
    selectors: Selector
    def filter(self, node):
        """ Yield only elements that match all tests """
        # First apply each test separately to each node
        # Then find the intersection of each set of filtered nodes.
        sets = [set(s.filter(node)) for s in self.selectors]
        result = sets[0]
        if len(sets) > 1:
            for s in sets[1:]:
                result = result.intersection(s)
        return result

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
            case Combinator.Either:
                # Yield each element that matches either of the tests -- but only once if it meets multiple tests.
                # Collect all matches in a set to make them unique.
                all_nodes = {n for s in [self.a, self.b] for n in s.filter(node)}
                for item in all_nodes:
                    yield item

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
            liststack[-1].pe = m.group(1)
            s = s[m.span()[1]:]
        elif m := re.match(r':([\w-]+)', s):
            liststack[-1].pc = m.group(1)
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
        else:
            for comb in Combinator:
                if m := re.match(r'\s*?'+comb.value+r'\s*', s):
                    selector = liststack.pop(-1)
                    s = s[m.span()[1]:]
                    part2 = parse_selector(s)
                    s = ''
                    selector = SelectorCombinator(selector, part2, comb)
                    break
        if s == start_s:
            raise RuntimeError("Unable to parse selector")
        if selector is not None:
            liststack.append(selector)
        selector = None

    if len(liststack) > 1:
        return SelectorList(liststack)
    return liststack[0]


class Style:
    """ In Brython, the class can be treated as a dict or as a regular object with members. """
    def __init__(self, d: Optional[Dict[str, Any] | List[Tuple[str, Any]]]):
        if isinstance(d, dict):
            self.__dict__.update(d)
        elif isinstance(d, list):
            for k, v in d:
                self.__dict__[k] = v
    def __setitem__(self, key: str, value: Any):
        self.__dict__[key] = value
    def __getitem__(self, key: str, default: Optional[Any] = None):
        if default is not None:
            return getattr(self, key, default)
        return getattr(self, key)
    def __str__(self):
        return str(self.__dict__)

class DOMNode:
    """ Base class for all tags.
        Tags have a uniform interface, so no tags need custom attributes or code.
    """
    def __init__(self, content='', **kwargs):
        self.text = ''
        self.children = []
        self.parent = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.style = Style({})
        if 'className' in kwargs:
            kwargs['Class'] = kwargs['className']
        if 'text' in kwargs:
            self.text = kwargs['text']
            del kwargs['text']
        self.attrs = {k.replace('_', '-'): v for k, v in kwargs.items()}
        self.classList = set(self.attrs.get('Class', '').split())
        if 'style' in kwargs:
            if isinstance(kwargs['style'], str):
                self.style = Style({k:v for k, v in [l.strip().split(':', maxsplit=1) for l in kwargs['style'].split(';')]})
            else:
                assert isinstance(kwargs['style'], dict)
                self.style = Style(kwargs['style'])
        if content:
            if isinstance(content, str):
                if '<' in content:
                    raise RuntimeError("HTML content is not (yet) supported by this mockup")
                self.text = content
            elif isinstance(content, DOMNode):
                self <= content
            elif isinstance(content, Iterable):
                self <= content
            else:
                raise RuntimeError("Unrecognized content")

    def __repr__(self):
        children = ''.join(str(c) for c in self.children)
        return f"{self.tagname()}({self.text} {children})"

    def __le__(self, other: Union['DOMNode', str, Iterable]) -> None:
        if isinstance(other, DOMNode):
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
                self.text = other
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
        if isinstance(other, DOMNode):
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
            # Filter the elements, and ensure each element is unique
            return list(dict.fromkeys(selector.filter(self)))
        items = list(flatten(self.children))
        for key, value in kwargs.items():
            items = [c for c in items if getattr(c, key, '') == value]
        return items

    def clear(self):
        self.text = ''
        self.children = []
        self.parent = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.style = Style({})

    def remove(self):
        # Unlink this element from the document DOM.
        if self.parent:
            while self in self.parent.children:
                self.parent.children.remove(self)

    def select(self, key) -> List["DOMNode"]:
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
    def dispatchEvent(self, event):
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
class A(DOMNode): pass

class ABBR(DOMNode): pass

class ACRONYM(DOMNode): pass

class ADDRESS(DOMNode): pass

class APPLET(DOMNode): pass

class AREA(DOMNode): pass

class B(DOMNode): pass

class BASE(DOMNode): pass

class BASEFONT(DOMNode): pass

class BDO(DOMNode): pass

class BIG(DOMNode): pass

class BLOCKQUOTE(DOMNode): pass

class BODY(DOMNode):
    def getElementById(self, id: str):
        return self[id]

    def createElement(self, tagName: str):
        cls = globals()[tagName.upper()]
        return cls()
    def appendChild(self, element):
        self.children.append(element)

class BR(DOMNode): pass

class BUTTON(DOMNode): pass

class CAPTION(DOMNode): pass

class CENTER(DOMNode): pass

class CITE(DOMNode): pass

class CODE(DOMNode): pass

class COL(DOMNode): pass

class COLGROUP(DOMNode): pass

class DD(DOMNode): pass

class DEL(DOMNode): pass

class DFN(DOMNode): pass

class DIR(DOMNode): pass

class DIV(DOMNode): pass

class DL(DOMNode): pass

class DT(DOMNode): pass

class EM(DOMNode): pass

class FIELDSET(DOMNode): pass

class FONT(DOMNode): pass

class FORM(DOMNode): pass

class FRAME(DOMNode): pass

class FRAMESET(DOMNode): pass

class H1(DOMNode): pass

class H2(DOMNode): pass

class H3(DOMNode): pass

class H4(DOMNode): pass

class H5(DOMNode): pass

class H6(DOMNode): pass

class HEAD(DOMNode): pass

class HR(DOMNode): pass

class HTML(DOMNode): pass

class I(DOMNode): pass

class IFRAME(DOMNode): pass

class IMG(DOMNode): pass

class INPUT(DOMNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'value' in kwargs:
            self.value = kwargs['value']
            del kwargs['value']
        else:
            self.value = 0 if self.attrs.get('type', 'text') == 'number' else ''

class INS(DOMNode): pass

class ISINDEX(DOMNode): pass

class KBD(DOMNode): pass

class LABEL(DOMNode): pass

class LEGEND(DOMNode): pass

class LI(DOMNode): pass

class LINK(DOMNode): pass

class MAP(DOMNode): pass

class MENU(DOMNode): pass

class META(DOMNode): pass

class NOFRAMES(DOMNode): pass

class NOSCRIPT(DOMNode): pass

class OBJECT(DOMNode): pass

class OL(DOMNode): pass

class OPTGROUP(DOMNode): pass

class OPTION(DOMNode): pass

class P(DOMNode): pass

class PARAM(DOMNode): pass

class PRE(DOMNode): pass

class Q(DOMNode): pass

class S(DOMNode): pass

class SAMP(DOMNode): pass

class SCRIPT(DOMNode): pass

class SELECT(DOMNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = 0

class SMALL(DOMNode): pass

class SPAN(DOMNode): pass

class STRIKE(DOMNode): pass

class STRONG(DOMNode): pass

class STYLE(DOMNode): pass

class SUB(DOMNode): pass

class SUP(DOMNode): pass


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

class SVG(DOMNode):
    def getScreenCTM(self) -> DOMMatrix:
        # Return the default transformation matrix
        # No offset, rotation, scaling or skewing
        return DOMMatrix()

class TABLE(DOMNode): pass

class TBODY(DOMNode): pass

class TD(DOMNode): pass

class TEXTAREA(INPUT): pass

class TFOOT(DOMNode): pass

class TH(DOMNode): pass

class THEAD(DOMNode): pass

class TITLE(DOMNode): pass

class TR(DOMNode): pass

class TT(DOMNode): pass

class U(DOMNode): pass

class UL(DOMNode): pass

class VAR(DOMNode): pass

class ARTICLE(DOMNode): pass

class ASIDE(DOMNode): pass

class AUDIO(DOMNode): pass

class BDI(DOMNode): pass

class CANVAS(DOMNode): pass

class COMMAND(DOMNode): pass

class DATA(DOMNode): pass

class DATALIST(DOMNode): pass

class EMBED(DOMNode): pass

class FIGCAPTION(DOMNode): pass

class FIGURE(DOMNode): pass

class FOOTER(DOMNode): pass

class HEADER(DOMNode): pass

class KEYGEN(DOMNode): pass

class MAIN(DOMNode): pass

class MARK(DOMNode): pass

class MATH(DOMNode): pass

class METER(DOMNode): pass

class NAV(DOMNode): pass

class OUTPUT(DOMNode): pass

class PROGRESS(DOMNode): pass

class RB(DOMNode): pass

class RP(DOMNode): pass

class RT(DOMNode): pass

class RTC(DOMNode): pass

class RUBY(DOMNode): pass

class SECTION(DOMNode): pass

class SOURCE(DOMNode): pass

class SUMMARY(DOMNode): pass

class TEMPLATE(DOMNode): pass

class TIME(DOMNode): pass

class TRACK(DOMNode): pass

class VIDEO(DOMNode): pass

class WBR(DOMNode): pass

class DETAILS(DOMNode): pass

class DIALOG(DOMNode):
    def showModal(self):
        if not self.parent:
            document <= self

    def close(self):
        pass

class MENUITEM(DOMNode): pass

class PICTURE(DOMNode): pass


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
        assert parse_selector('.pietje, .puk, .keteldorp') == SelectorCombinator(
            a=ClassSelector(name='pietje'),
            b=SelectorCombinator(a=ClassSelector(name='puk'), b=ClassSelector(name='keteldorp'), t=Combinator.Either),
            t=Combinator.Either
        )
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
            LABEL(name="value3"),
            INPUT(name="value3", Class='outside')
        ]
    )
    @test
    def core_selectors():
        assert len(test_set.select('*')) == 13
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
        assert len(test_set.select('INPUT[name="value3"]')) == 1


if __name__ == '__main__':
    run_tests()