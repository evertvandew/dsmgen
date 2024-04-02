

from test_frame import prepare, test, run_tests, expect_exception

import shapes
from svg_shapes import wrapText, getTextWidth

@prepare
def test_text_rendering():
    @test
    def wrapping():
        # Check splitting a text into parts
        txts = ["Dit is een testtekst", 'Dit is een test-', 'Dit is een', 'Dit is een', 'Dit is', 'Dit']
        print('Full size:', [f"{txt}: {getTextWidth(txt)}" for txt in txts])
        widths = [110, 84, 50, 20, 10]
        expected = ['Dit is een testtekst', 'Dit is een\ntesttekst', 'Dit is\neen\ntesttekst', 'Dit\nis\neen\ntesttekst', 'Dit\nis\neen\ntesttekst']
        for w, e in zip(widths, expected):
            result = wrapText(txts[0], w)
            assert '\n'.join(result) == e, f"Not the same for width {w}: {repr(chr(10).join(result))}, {e}"

@prepare
def test_styling():

    class TestShape(shapes.Shape):
        default_style = {'color': 'white', 'stroke': 'black'}

        def __init__(self):
            super().__init__(x=100, y=100, width=120, height=64)

    @test
    def shape_styling():
        item = TestShape()
        item.shape = item.getShape()
        assert item.getDefaultStyle() == {'color': 'white', 'stroke': 'black'}
        assert item.getStyleKeys() == ['color', 'stroke']

        # Updating the styling through the API should work.
        item.updateStyle(color='black')
        assert item.getStyle('color') == 'black'
        assert item.getAllStyle() == {'color': 'black', 'stroke': 'black'}
        assert item.dumpStyle() == '{"color": "black"}'

        item.loadStyle('{"color": "yellow"}')
        assert item.getStyle('color') == 'yellow'
        assert item.getStyle('stroke') == 'black'

if __name__ == '__main__':
    run_tests('*.wrapping')
