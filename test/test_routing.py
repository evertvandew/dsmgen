

from square_routing import *
from test_frame import prepare, test, run_tests

@prepare
def routing_tests():
    @test
    def testSquareRouter():
        def mkPoints(*args):
            return [Point(x=x, y=y) for x, y in args]

        # Straight horizontal center2center line
        e = mkPoints((200,60), (300,60))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), [])
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # Straight vertical center2center line
        e = mkPoints((150,80), (150,150))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), [])
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # Straight horizontal off-center line
        e = mkPoints((200, 65), (300, 65))
        r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((300, 50), (100, 40)), [])
        assert e == r, f"Asser error: {r} is not as expected {e}"

        # Straight vertical off-center line
        e = mkPoints((160, 80), (160, 150))
        r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((120, 150), (100, 40)), [])
        assert e == r, f"Asser error: {r} is not as expected {e}"

        # Horizontal stepped line
        e = mkPoints((200, 60), (350,60), (350,120), (500,120))
        r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((500, 100), (100, 40)), [])
        assert e == r, f"Asser error: {r} is not as expected {e}"

        # Vertical stepped line
        e = mkPoints((150,80), (150,210), (270,210), (270,340))
        r = routeSquare(mkPoints((100, 40), (100, 40)), mkPoints((220, 340), (100, 40)), [])
        assert e == r, f"Asser error: {r} is not as expected {e}"

        # Horizontal by single waypoint above
        e = mkPoints((150,80), (150,100), (350,100), (350,80))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), mkPoints((inf,100)))
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # Horizontal by single waypoint below
        e = mkPoints((150,40), (150,20), (350,20), (350,40))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((300,40),(100,40)), mkPoints((inf,20)))
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # Vertical by single waypoint to left
        e = mkPoints((200,60), (250,60), (250,170), (200,170))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), mkPoints((250, inf)))
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # Vertical by single waypoint to right
        e = mkPoints((100,60), (50,60), (50,170), (100,170))
        r = routeSquare(mkPoints((100,40), (100,40)), mkPoints((100,150),(100,40)), mkPoints((50, inf)))
        assert e==r, f"Asser error: {r} is not as expected {e}"

        # A route with two waypoints
        e = mkPoints((200,420), (570,420), (570,100), (350,100), (350,80))
        r = routeSquare(mkPoints((100,400), (100,40)), mkPoints((300,40),(100,40)), mkPoints((570, inf), (inf,100)))
        assert e==r, f"Asser error: {r} is not as expected {e}"

if __name__ == '__main__':
    run_tests()