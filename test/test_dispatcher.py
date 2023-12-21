
from test_frame import prepare, test, run_tests
from dispatcher import EventDispatcher
from dataclasses import dataclass, field
from typing import List

@dataclass
class ASource:
    calls: List[str] = field(default_factory=list)

    def callback(self, path: str, **details):
        self.calls.append(path)


@prepare
def test_dispatcher():
    @test
    def test_matching():
        d = EventDispatcher()
        calls = []
        source = ASource()

        def cb(path, *args):
            nonlocal calls
            calls.append(path)

        # Test a double wildcard, for action and resource id
        d.subscribe('*/resource/*', source, cb)
        for name in ['add/resource/', 'update/resource/123', 'delete/resource/456', 'revive/resource/1',
                     'add/entity/', 'update/entity/123', 'delete/entity/456']:
            d.trigger_event(name, source)

        assert calls == ['add/resource/', 'update/resource/123', 'delete/resource/456', 'revive/resource/1']

    @test
    def test_unbinding():
        d = EventDispatcher()
        calls = []
        source = ASource()

        def cb(path, *args):
            nonlocal calls
            calls.append(path)

        # Test an explicit unbind works
        d.subscribe('*/resource/*', source, cb)
        d.trigger_event('add/resource/', source)
        d.unsubscribe(source)
        d.trigger_event('add/resource/', source)
        assert len(calls) == 1
        assert len(d.subscriptions) == 0


if __name__ == '__main__':
    run_tests()
