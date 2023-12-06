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
            print(f"Running test {t.__name__}")
            try:
                t()
                successes.append(t)
            except Exception as e:
                logging.exception('Test failed:')
                failures.append(t)

            executed_tests.append(t)

        # Cleanup is in reversed order, hopefully keeping dependencies alive while needed.
        for p in reversed(cleanups):
            p()

    logging.error(f"Failures: {len(failures)} / {len(executed_tests)}")
    if failures:
        sys.exit(1)
