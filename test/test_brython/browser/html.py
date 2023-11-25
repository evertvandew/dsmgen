""" Stub of the Brython HTML interface """

from typing import Self, Iterable
from enum import Enum
import re
from dataclasses import dataclass
from test_frame import prepare, test, run_tests


def flatten(data):
    if isinstance(data, Iterable) and not isinstance(data, str) and not isinstance(data, bytes):
        for d in data:
            yield from flatten(d)
    else:
        yield data
        if children := getattr(data, 'children', False):
            yield from flatten(children)

class AttributeOperator(Enum):
    has = ""
    equals = '='
    contains_word = '~='
    equals_upto_hyphen = r'[|]='
    startswith = '\^='
    endswith = '[$]='
    contains = '[*]='


class PsuedoClass:
    name: str
class PsuedoElement:
    name: str
class Selector:
    pc: PsuedoClass
    pe: PsuedoElement
class UniversalSelector(Selector):
    pass
@dataclass
class TypeSelector(Selector):
    name: str
    def test(self, node):
        return node.tagname() == self.name

@dataclass
class ClassSelector(Selector):
    name: str
    def test(self, node):
        return self.name in node.classList

@dataclass
class IdSelector(Selector):
    name: str
    def test(self, node):
        return getattr(node, 'id', '0') == self.name

@dataclass
class AttributeSelector(Selector):
    name: str
    value: str|None
    operator: AttributeOperator
    flag: ''
    def __post_init__(self):
        ivalue = self.value.lower()
        if self.operator == AttributeOperator.has:
            self.test = lambda node: hasattr(node, self.name)
        elif self.operator == AttributeOperator.equals:
            if self.flag == 'i':
                self.test = lambda node: getattr(node, self.name, '').lower() == ivalue
            else:
                self.test = lambda node: getattr(node, self.name, '') == self.value
        elif self.operator == AttributeOperator.contains_word:
            if self.flag == 'i':
                self.test = lambda node: ivalue in getattr(node, self.name, '').lower().split()
            else:
                self.test = lambda node: self.value in getattr(node, self.name, '').split()
        elif self.operator == AttributeOperator.equals_upto_hyphen:
            if self.flag == 'i':
                def tester(node):
                    attr = getattr(node, self.name, '').lower()
                    return attr == ivalue or attr.startswith(ivalue + '-')
            else:
                def tester(node):
                    attr = getattr(node, self.name, '')
                    return attr == self.value or attr.startswith(self.value+'-')
            self.test = tester
        elif self.operator == AttributeOperator.startswith:
            if self.flag == 'i':
                self.test = lambda node: getattr(node, self.name, '').lower().startswith(ivalue)
            else:
                self.test = lambda node: getattr(node, self.name, '').startswith(self.value)
        elif self.operator == AttributeOperator.endswith:
            if self.flag == 'i':
                self.test = lambda node: getattr(node, self.name, '').lower().endswith(ivalue)
            else:
                self.test = lambda node: getattr(node, self.name, '').endswith(self.value)
        elif self.operator == AttributeOperator.contains:
            if self.flag == 'i':
                self.test = lambda node: ivalue in getattr(node, self.name, '').lower()
            else:
                self.test = lambda node: self.value in getattr(node, self.name, '')
class Combinator(Enum):
    NextSibling = '[+]'
    SubsequentSibling = '~'
    Child = '>'
    Column = '\|\|'
    Descendant = ' '

@dataclass
class SelectorList:
    selectors: Selector

@dataclass
class SelectorCombinator:
    a: Selector
    b: Selector
    t: Combinator


def parse_attribute_selector(s):
    for attr in AttributeOperator:
        if attr.value == '':
            if m := re.fullmatch(r'(\w*)(\s*([iIsS]))?', s):
                return AttributeSelector(m.group(1), '', attr, (m.group(3) or 's').lower())
        elif m := re.fullmatch(r'(\w*)'+attr.value+r'"([^"]*)"(\s*([iIsS]))?', s):
            return AttributeSelector(m.group(1), m.group(2), attr, (m.group(4) or 's').lower())
    raise RuntimeError(f'Could not parse attribute selector {s}')


def parse_selector(s):
    # Check for the Universal selector
    liststack = []
    selector = None
    while s:
        # Parse the various selectors
        if s[0] == '*':
            selector = UniversalSelector()
            s = s[1:]
        elif m := re.match(r'::(\w+)', s):
            selector.pe = m.group(1)
            s = s[m.span()[1]:]
        elif m := re.match(r':(\w+)', s):
            selector.pc = m.group(1)
            s = s[m.span()[1]:]
        elif m := re.match(r'(\w+)', s):
            selector = TypeSelector(m.group(1))
            s = s[m.span()[1]:]
        elif m := re.match(r'[.](\w+)', s):
            selector = ClassSelector(m.group(1))
            s = s[m.span()[1]:]
        elif m := re.match(r'#(\w+)', s):
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
                if m := re.match(r'\s*'+comb.value+r'\s*', s):
                    s = s[m.span()[1]:]
                    part2 = parse_selector(s)
                    s = ''
                    selector = SelectorCombinator(selector, part2, comb)
                    break
    if liststack:
        liststack.append(selector)
        return SelectorList(liststack)
    return selector


def create_filter(selector):
    if isinstance(selector, UniversalSelector):
        def filter(node):
            yield from flatten(node)
        return filter
    if type(selector) in [TypeSelector, ClassSelector, IdSelector, AttributeSelector]:
        def filter(node):
            for item in flatten(node):
                if selector.test(item):
                    yield item
        return filter
    if isinstance(selector, SelectorList):
        filters = [create_filter(s) for s in selector.selectors]
        def filter(node):
            all_nodes = {n for f in filters for n in f(node)}
            for item in all_nodes:
                yield item
        return filter

class tag:
    def __init__(self, *args, **kwargs):
        self.id = ''
        self.style = {}
        self.Class = ''
        self.text = ''
        self.children = []
        for a in args:
            if isinstance(a, str):
                self.text = a
            elif isinstance(a, list):
                self.children.append(a)
        self.__dict__.update(kwargs)
        self.classList = self.Class.split()

    def __le__(self, other: Self|str):
        self.children.append(other)

    def __getitem__(self, key):
        return self.get(id=key)

    def get(self, **kwargs):
        if 'selector' in kwargs:
            selector = parse_selector(kwargs['selector'])
            filter = create_filter(selector)
            return list(filter(self))
        items = list(flatten(self.children))
        for key, value in kwargs.items():
            items = [c for c in items if getattr(c, key, '') == value]
        return items

    def select(self, key):
        return self.get(selector=key)

    def tagname(self):
        return type(self).__name__


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

class BODY(tag): pass

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

class INPUT(tag): pass

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

class SELECT(tag): pass

class SMALL(tag): pass

class SPAN(tag): pass

class STRIKE(tag): pass

class STRONG(tag): pass

class STYLE(tag): pass

class SUB(tag): pass

class SUP(tag): pass

class SVG(tag): pass

class TABLE(tag): pass

class TBODY(tag): pass

class TD(tag): pass

class TEXTAREA(tag): pass

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

class DIALOG(tag): pass

class MENUITEM(tag): pass

class PICTURE(tag): pass



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
                SPAN("Dit is een test", Class="chapter text"),
                INPUT(id='myvalue', name="value1", Class='edit'),
                A("Klik mij", href="http://pietje.puk")
            ], id="1", Class='pietje puk'),
            DIV([
                INPUT(name="value2", Class='edit', flag='btn-primary'),
                BUTTON("Click Me", onclick="onBtnClick()", Class='edit btn')
            ], id="2", Class="olivier bommel")
        ]
    )
    @test
    def core_selectors():
        assert len(test_set.select('*')) == 8
        assert len(test_set.select('INPUT')) == 2
        assert len(test_set.select('.edit')) == 3
        assert len(test_set.select('#myvalue')) == 1
        assert len(test_set.select('[onclick]')) == 1
        assert len(test_set.select('[href*=".puk"]')) == 1
        assert len(test_set.select('[Class*="ie"]')) == 2
        assert len(test_set.select('[flag|="btn"]')) == 1
        assert len(test_set.select('[Class~="btn"]')) == 1
        assert len(test_set.select('[text^="click" i]')) == 1
        assert len(test_set.select('[text$="me" i]')) == 1


if __name__ == '__main__':
    run_tests()