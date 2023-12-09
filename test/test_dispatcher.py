
from test_frame import prepare, test, run_tests
from dispatcher import EventDispatcher
from dataclasses import dataclass

@dataclass
class ASource:
    a: str = "This is a string"


@prepare
def test_dispatcher():
    @test
    def test_matching():
        d = EventDispatcher()
        calls = []
        source = ASource()

        def cb(path, **details):
            nonlocal calls
            calls.append(path)

        # Test a double wildcard, for action and resource id
        d.bind('*/resource/*', source, cb)
        for name in ['add/resource/', 'update/resource/123', 'delete/resource/456', 'revive/resource/1',
                     'add/entity/', 'update/entity/123', 'delete/entity/456']:
            d.trigger_event(name, source)

        assert calls == ['add/resource/', 'update/resource/123', 'delete/resource/456', 'revive/resource/1']

    @test
    def test_unbinding():
        d = EventDispatcher()
        calls = []
        source = ASource()

        def cb(path, **details):
            nonlocal calls
            calls.append(path)

        # Test an explicit unbind works
        d.bind('*/resource/*', source, cb)
        d.trigger_event('add/resource/', source)
        d.unbind(source)
        d.trigger_event('add/resource/', source)
        assert len(calls) == 1
        assert len(d.subscriptions) == 0

        # Test a source is unsubscribed when it is deleted
        calls = []
        d.bind('*/resource/*', source, cb)
        d.trigger_event('add/resource/', source)
        source = ASource()  # A different instance
        d.trigger_event('add/resource/', source)
        assert len(calls) == 1
        assert len(d.subscriptions) == 0

if __name__ == '__main__':
    run_tests()
