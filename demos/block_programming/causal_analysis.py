





from test_frame import run_tests, test, prepare

@prepare
def init():
    from difflib import unified_diff
    def load_test_database():
        pass

    load_test_database()

    test_data = get_program_data('blinky')
