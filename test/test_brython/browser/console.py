""" stub of the Brython console module. """
import sys

def alert(msg):
    print(msg, file=sys.stderr)

def log(msg):
    print(msg)