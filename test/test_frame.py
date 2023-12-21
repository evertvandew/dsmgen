"""
Test framework
Inspired by some testing frameworks in Javascript. Very simple and extendible.
"""

import logging
import sys
from contextlib import contextmanager
from fnmatch import fnmatch

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

def run_tests(*filters):
    global all_tests, cleanups
    successes = []
    failures = []

    filters = [f.split('.') for f in filters]

    for p in preparations:
        path = p.__name__

        if filters:
            if not any(fnmatch(path, f[0]) for f in filters):
                continue

        print(f"Preparing: {p.__name__} in {p.__module__}")
        all_tests = []
        cleanups = []
        p()

        for t in all_tests:
            if filters:
                if not any(fnmatch(t.__name__, f[1]) for f in filters):
                    continue
            name = p.__module__ + '.' + p.__name__ + '.' + t.__name__
            print(f"Running test {name}")
            try:
                t()
                successes.append(t)
            except Exception as e:
                logging.exception(f'Test failed: {name}')
                failures.append(name)

            executed_tests.append(name)

        # Cleanup is in reversed order, hopefully keeping dependencies alive while needed.
        for c in reversed(cleanups):
            c()

    logging.error(f"Failures: {len(failures)} / {len(executed_tests)}")
    if failures:
        for failure in failures:
            logging.error(f"Test {failure} FAILED")
        sys.exit(1)
