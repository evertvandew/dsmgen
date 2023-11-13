"""
Test framework
Inspired by some testing frameworks in Javascript. Very simple and extendible.
"""

import logging
import sys

all_tests = []
preparations = []
cleanups = []

def test(func):
    all_tests.append(func)
    return func

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
                logging.exception(f'Error failed: {str(e)}')
                failures.append(t)

        # Cleanup is in reversed order, hopefully keeping dependencies alive while needed.
        for p in reversed(cleanups):
            p()

    logging.info(f"Failures: {len(failures)} / {len(all_tests)}")
    if failures:
        sys.exit(1)
