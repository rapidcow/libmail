"""converts parse tree -> sensible strings"""

import itertools
from . import tokens
from .tokens import *

# this stupid function does not deserve to see the
# light of the day yet :)
__all__ = []

def simple_fold(header, toks, *, policy):
    linelen = policy.max_line_length
    LINE = policy.linesep
    LINE_SPACE = LINE + SPACE.value
    currlen = 0
    buffer = []

    buffer.append(header + COLON.value)
    currlen += len(header) + 1
    buffer.append(SPACE.value)
    inspace = True
    for tik in toks:
        isspace = isinstance(tik, WhiteSpaceToken)
        if isspace:
            if inspace:
                continue
            space = SPACE.value if CRLF not in tik else tik[-1].value
            if currlen + len(space) > linelen:
                buffer.append(LINE_SPACE)
                currlen = 1
            else:
                buffer.append(space)
                currlen += len(space)
        elif isinstance(tik, MsgId):
            # walk the tree & strip all whitespace
            flattire = str(tik.filter('not WhiteSpaceToken'))
            if inspace:
                if currlen + len(flattire) > linelen:
                    buffer[-1] = LINE_SPACE
            else:
                if currlen + 1 + len(flattire) > linelen:
                    buffer.append(LINE_SPACE)
                else:
                    buffer.append(SPACE.value)
            buffer.append(flattire)
            currlen += len(flattire)
        else:
            raise ValueError('not implemented for token type %s'
                             % (type(tik).__name__,))
        inspace = isspace
    if inspace:
        buffer.pop()
    return ''.join(buffer) + LINE

# mandatory debug functions
def dump(tree, indent=2, **kwargs):
    return print(dumps(tree, indent=indent), **kwargs)

def dumps(tree, indent=2):
    # cursed python code
    if isinstance(indent, int):
        indent *= ' '
    if isinstance(tree, Terminal):
        # display say CRLF that would otherwise have a repr
        # of WhiteSpaceTerminal('\r\n') as simply 'CRLF'
        if isinstance(tree, Symbol):
            try:
                return tree.name
            except AttributeError:
                pass
        return repr(tree)
    if isinstance(tree, (list, Tokens)):
        inner = '\n'.join(
            '\n'.join(
                indent + line for line in dumps(token).splitlines()
            ) + ',' for token in tree
        )
        if inner:
            inner = inner[:-1]
        if isinstance(tree, Token) and type(tree) is not Token:
            return '%s([\n%s\n])' % (type(tree).__name__, inner)
        return '[\n%s\n]' % (inner,)
    return repr(tree)
