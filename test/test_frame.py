"""
Test framework
Inspired by some testing frameworks in Javascript. Very simple and extendible.
"""

import logging
import sys
from contextlib import contextmanager

all_tests = []
executed_tests = []
preparations = []
cleanups = []

def test(func):
    all_tests.append(func)
    return func

@contextmanager
def expect_exception(e):
    success = False
    try:
        yield None
    except e:
        success = True
    assert success, f"Code did not raise an exception of type {e.__name__}"

def prepare(func):
    preparations.append(func)
    return func

def cleanup(func):
    cleanups.append(func)

def run_tests():
    global all_tests, cleanups
    successes = []
    failures = []

    for p in preparations:
        all_tests = []
        cleanups = []
        p()

        for t in all_tests:
            try:
                t()
                successes.append(t)
            except Exception as e:
                logging.exception('Test failed:')
                failures.append(t)

        executed_tests.extend(all_tests)

        # Cleanup is in reversed order, hopefully keeping dependencies alive while needed.
        for p in reversed(cleanups):
            p()

    logging.error(f"Failures: {len(failures)} / {len(executed_tests)}")
    if failures:
        sys.exit(1)
