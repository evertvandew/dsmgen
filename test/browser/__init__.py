
import sys
from .html import BODY, DOMNode

document = BODY()

def alert(msg):
    print(msg, file=sys.stderr)


def bind(node, event):
    def decorate(func):
        if isinstance(node, list):
            for n in node:
                n.bind(event, func)
        else:
            node.bind(event, func)
        return func
    return decorate
