import importlib
import io
import subprocess
import sys
from enum import IntEnum, auto
from dataclasses import dataclass
from typing import Dict, List

class States(IntEnum):
    INIT = auto()
    TESTCASE = auto()
    FILE = auto()
    EXPECT = auto()
    COMMAND = auto()

@dataclass
class TestCase:
    name: str
    command: str
    command_language: str
    files: Dict[str, str]
    expects: Dict[str, str]

def parse_tests(lines) -> List[TestCase]:
    state = States.INIT
    test_cases = []
    files = {}
    expects = {}
    contents = []
    command = None
    cmnd_language = None

    for line in lines:
        match state:
            case States.INIT:
                if line.startswith('@testcase'):
                    state = States.TESTCASE
                    case_name = ' '.join(line.split()[1:])
                    files = {}
            case States.TESTCASE:
                if line.startswith('@file'):
                    state = States.FILE
                    file_name = ' '.join(line.split()[1:])
                    contents = []
                elif line.startswith('@expect'):
                    state = States.EXPECT
                    file_name = ' '.join(line.split()[1:])
                    contents = []
                elif line.startswith('@command'):
                    state = States.COMMAND
                    cmnd_language = ' '.join(line.split()[1:])
                elif line.startswith('@endtest'):
                    state = States.INIT
                    test_cases.append(TestCase(case_name, command, cmnd_language, files, expects))
            case States.FILE:
                if line.startswith('@endfile'):
                    state = States.TESTCASE
                    files[file_name] = ''.join(contents)
                else:
                    contents.append(line)
            case States.EXPECT:
                if line.startswith('@endexpect'):
                    state = States.TESTCASE
                    expects[file_name] = ''.join(contents)
                else:
                    contents.append(line)
            case States.COMMAND:
                if line.startswith('@endcommand'):
                    state = States.TESTCASE
                    command = ''.join(contents)
                else:
                    contents.append(line)
    return test_cases


def compare_output(output, expected) -> str:
    # For now, use the diff utility.
    open('test_output', 'w').write(output)
    open('test_expected', 'w').write(expected)
    result = subprocess.run('diff -tywB test_expected test_output', shell=True, capture_output=True)
    if result.returncode == 0:
        return ''
    return result.stdout

def run_tests(tests: List[TestCase]) -> Dict[str, bool]:
    results = {}
    real_stdout = sys.stdout
    real_stderr = sys.stderr
    for test in tests:
        # Prepare the files
        for name, contents in test.files.items():
            if name == 'stdin':
                sys.stdin = io.StringIO(contents)
            else:
                with open(name, 'w') as output:
                    output.write(contents)

        # Run the command
        if test.command and test.command_language in [None, 'python']:
            open(f'test_{test.name}.py', 'w').write(test.command)
            success = False
            try:
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                importlib.import_module(f'test_{test.name}')
                success = True
            finally:
                buffered_stdout = sys.stdout
                buffered_stderr = sys.stderr
                sys.stdout = real_stdout
                sys.stderr = real_stderr
                print(buffered_stderr.getvalue(), file=sys.stderr)

        # Check the output
        result = []
        for name, expected in test.expects.items():
            if name == 'stdout':
                output = buffered_stdout.getvalue()
            elif name == 'stderr':
                output = buffered_stderr.getvalue()
            else:
                output = open(name).read()

            result.append(compare_output(output, expected))
        # Report the result
        results[test.name] = '\n'.join(b if isinstance(b, str) else b.decode('utf8') for b in result)
    return results

def analyse(results: Dict[str, str]) -> str:
    result = []
    for key, msg in results.items():
        if msg:
            result.append(f'ERROR in test {key}:\n{msg}')
    result.insert(0, f'Test stats (success, failed, total): {len(results)-len(result)}, {len(result)}, {len(results)}')
    return '\n'.join(result)


def main():
    lines = list(open('test_cases.txt').readlines())
    tests = parse_tests(lines)
    results = run_tests(tests)
    print(analyse(results))





if __name__ == '__main__':
    main()
