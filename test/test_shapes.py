

from test_frame import prepare, test, run_tests, expect_exception

import shapes

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
    run_tests()
