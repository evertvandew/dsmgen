from behave import *
import yaml
import generate_rust_embedded as gen
from difflib import unified_diff


def eq_(a, b):
    # Special handling for large strings.
    if isinstance(a, str) and '\n' in a:
        delta = ''.join(unified_diff(a, str(b), 'result', 'expected'))
        if delta:
            print(f"Result:\n{a}\n\nExpected:\n{b}\n\nDiff:\n{delta}")
            assert False
    else:
        assert a == b, f"{repr(a)} is not equal to {repr(b)}"


@given('the Blinky network')
def load_blinky(context):
    context.test_data = yaml.full_load(open('features/steps/blinky.yml'))
    context.code_generator = gen.code_generator('blinky', context.test_data, 1)

@then('the program name is "{name}"')
def check_program_name(context, name):
    eq_(context.code_generator.program_name, name)

@then('the generated preamble equals')
def step_impl(context):
    eq_(context.code_generator.get_preamble(), context.text)


@when('generating the main program')
def step_impl(context):
    context.program_generator = context.code_generator.get_program_generator(None)

@then('there is {count:d} parameters')
def step_impl(context, count):
    eq_(len(context.program_generator.parameters), count)

@then('the type of parameter {index:d} is {type}')
def step_impl(context, index, type):
    eq_(context.program_generator.parameters[index][2], type)

@then('the recipient of parameter {index:d} is block {block_id:d}')
def step_impl(context, index, block_id):
    block_order = [b['Id'] for b in context.program_generator.inner_blocks]
    eq_(context.program_generator.parameters[index][1], block_order[block_id])

@then('the number of blocks to be instantiated equals {count:d}')
def step_impl(context, count):
    eq_(len(context.program_generator.inner_blocks), count)

@then('the generated instantiation for block {block:d} equals "{code}"')
def step_impl(context, block, code):
    block = context.program_generator.inner_blocks[block]
    eq_(context.program_generator.block_constructor(block), code)

@then('the constructor for connection {conn:d} equals "{code}"')
def step_impl(context, conn, code):
    eq_(context.program_generator.connection_constructor(conn), code)


@then('the number of connections to be instantiated equals {count:d}')
def step_impl(context, count):
    eq_(len(context.program_generator.connections), count)

@then('the program name is TheProgram')
def step_impl(context):
    eq_(context.program_generator.get_program_name(), 'TheProgram')

@then('the program parameter string is "{code}"')
def step_impl(context, code):
    eq_(context.program_generator.get_param_decl(), code)

@then('the declaration for block {block:d} equals "{code}"')
def step_impl(context, block, code):
    eq_(context.program_generator.get_block_decl(block), code)

@then('the constructor for the program equals')
def step_impl(context):
    eq_(context.program_generator.get_my_implementation(), context.text)

@then('the program instantiation parameters equals "{code}"')
def step_impl(context, code):
    eq_(context.program_generator.get_program_instance_args(), code)