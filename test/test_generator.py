
import os.path
import sys

from test_frame import prepare, test, run_tests, cleanup
import diagram_tool_generator.generate_tool as gen

@prepare
def generator_tests():
    """ Unit tests for the generator tool """
    TEST_SPEC = os.path.normpath('sysml_spec.py')

    @test
    def test_get_diagram_attributes():
        generator, module_name = gen.Generator.load_from_config(gen.Configuration(TEST_SPEC))
        sysml_spec = sys.modules[module_name]
        attrs = generator.get_diagram_attributes(sysml_spec.Block)
        assert len(attrs) == 3
        names = [f.name for f in attrs]
        assert 'name' in names
        assert 'description' in names
        assert 'parameters' in names


if __name__ == '__main__':
    run_tests()
