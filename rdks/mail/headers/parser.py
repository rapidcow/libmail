"""converts string -> parse tree as per RFC5322"""

# XXX: no obsolete or invalid syntax is considered
# XXX XXX: WE USE CRLF!

from .tokens import *
import re

__all__ = [
    'ParserError',
    # partial parsers (return a token)
    'get_quoted_pair',      # -> QuotedPair
    'get_fws',    # -> FoldingWhiteSpace
    'get_cfws',   # -> CommentFoldingWhiteSpace
    'get_domain_literal',   # -> DomainLiteral
    'get_msg_id',           # -> MsgId
    # header parser (returns list of tokens)
    'parse_message_id', 'parse_references',
]

class ParserError(ValueError):
    def __init__(self, msg, value=None):
        if value:
            super().__init__(msg + ': ' + repr(value))
        else:
            super().__init__(msg)

RE_CONST = dict(
    CRLF=re.escape(CRLF.value), DOT=re.escape(PERIOD.value),
    WSP=re.escape(''.join(WHITESPACE)),
)

#
# FWS             =   ([*WSP CRLF] 1*WSP)
#
# ctext           =   ;; PRINTABLE minus "(" ")" "\"
#
# ccontent        =   ctext / quoted-pair / comment
# quoted-pair     =   "\" (VCHAR / WSP)
# comment         =   "(" *([FWS] ccontent) [FWS] ")"
#
# CFWS            =   (1*([FWS] comment) [FWS]) / FWS
#
def get_quoted_pair(value) -> QuotedPair:
    if len(value) < 2:
        raise ParserError('quoted-pair requires at least 2 characters')
    escape, char = value[:2]
    if escape != BSLASH:
        raise ParserError('quoted-pair must begin with a backslash')
    if char not in PRINTABLE | WHITESPACE:
        raise ParserError('invalid quoted-pair character', char)
    return QuotedPair([BSLASH, Text(char)]), value[2:]

RE_FWS = re.compile(r'(?:([%(WSP)s])*(%(CRLF)s))?([%(WSP)s]+)' % RE_CONST)
def get_fws(value) -> FoldingWhiteSpace:
    match = RE_FWS.match(value)
    if not match:
        raise ParserError('no FWS found')
    leading, crlf, hanging = match.groups()
    fws = FoldingWhiteSpace()
    if leading:
        fws.append(WhiteSpace(leading))
    if crlf:
        fws.append(CRLF)
    assert hanging
    fws.append(WhiteSpace(hanging))
    return fws, value[match.end():]

RE_CONST['ctext'] = ''.join(re.escape(''.join(CTEXT)))
RE_CTEXT = re.compile(r'[%(ctext)s]+' % RE_CONST)
def get_comment(value) -> Comment:
    if not value.startswith(LPAREN.value):
        raise ParserError('comment must begin with "("')
    comment = Comment()
    comment.append(LPAREN)
    value = value[1:]
    while value:
        if RE_FWS.match(value):
            token, value = get_fws(value)
            comment.append(token)
        # the following looks for ccontent
        # ... or terminates prematurely
        if not value or value[0] == RPAREN.value:
            break
        match = RE_CTEXT.match(value)
        if match:
            comment.append(CommentText(match.group()))
            value = value[match.end():]
        elif value[0] == BSLASH.value:
            token, value = get_quoted_pair(value)
            comment.append(token)
        elif value[0] == LPAREN.value:
            token, value = get_comment(value)
            comment.append(token)
        else:
            raise ParserError('invalid comment', value[0])
    # XXX: the != case prolly doesn't happen
    if not value or value[0] != RPAREN.value:
        raise ParserError('unterminated comment', value)
    comment.append(RPAREN)
    return comment, value[1:]

#
# to clarify, the rule
#
# CFWS            =   (1*([FWS] comment) [FWS]) / FWS
#
# is effectively saying that
#
#    (a) consecutive comments are separated by at most one FWS
#    (b) either a comment or a FWS must be present
#
# so this is how i implement it (: it's slightly different
# from Python's _header_value_parse.py logic, but i am hoping
# this is more painstakingly correct than that....
#
def get_cfws(value) -> CommentFoldingWhiteSpace:
    cfws = CommentFoldingWhiteSpace()
    while value:
        if RE_FWS.match(value):
            token, value = get_fws(value)
            cfws.append(token)
        if value and value[0] == "(":
            token, value = get_comment(value)
            cfws.append(token)
        else:
            break
    if not cfws: # check (b)
        raise ParserError('no CFWS to parse')
    return cfws, value

#
# atext           =   ;; PRINTABLE minus SPECIALS
# dot-atom-text   =   1*atext *("." 1*atext)
#
RE_CONST['atext'] = re.escape(''.join(ATEXT))
RE_DOT_ATOM_TEXT = re.compile(
    r'[%(atext)s]+(?:[%(DOT)s][%(atext)s]+)*' % RE_CONST)

def get_dot_atom_text(value) -> DotAtomText:
    match = RE_DOT_ATOM_TEXT.match(value)
    if not match:
        raise ParserError('invalid dot-atom-text', value)
    return DotAtomText([
        PERIOD if chk == PERIOD.value else AtomText(chk)
        for chk in re.split('(%(DOT)s)' % RE_CONST, match.group())
    ]), value[match.end():]

#
# dtext           =   ;; PRINTABLE minus "[" "]" "\"
#   (N.B. from a different section)
# no-fold-literal =   "[" *dtext "]"
#
RE_CONST['dtext'] = re.escape(''.join(DTEXT))
RE_DTEXT = re.compile('[%(dtext)s]*' % RE_CONST)
def get_domain_literal(value) -> DomainLiteral:
    if not value.startswith(LBRACK.value):
        raise ParserError('domain literal must begin with "["')
    literal = DomainLiteral()
    literal.append(LBRACK)
    value = value[1:]

    match = RE_DTEXT.match(value)
    if match.end():
        literal.append(DomainText(match.group()))
        value = value[match.end():]

    if not value.startswith(RBRACK.value):
        if not value:
            raise ParserError('unterminated domain literal')
        else:
            raise ParserError('invalid dtext', value[0])
    literal.append(RBRACK)
    return literal, value[1:]

#
# WE ARE FINALLY HERE
# AAAAHHHHHHHHH
#
# msg-id          =   [CFWS] "<" id-left "@" id-right ">" [CFWS]
# id-left         =   dot-atom-text
# id-right        =   dot-atom-text / no-fold-literal
#
def get_msg_id(value) -> MsgId:
    msg_id = MsgId()
    if not value.startswith(LANGLE.value):
        raise ParserError('msg-id must begin with "<"', value[:1])
    msg_id.append(LANGLE)
    value = value[1:]

    try:
        token, value = get_dot_atom_text(value)
    except ParserError:
        raise ParserError('invalid id-left: expected dot-atom-text')
    msg_id.append(IdLeft([token]))

    if not value.startswith(ATSIGN.value):
        raise ParserError('id-left must be followed by "@"', value[:1])
    msg_id.append(ATSIGN)
    value = value[1:]

    try:
        token, value = get_dot_atom_text(value)
    except ParserError:
        try:
            token, value = get_domain_literal(value)
        except ParserError:
            raise ParserError('invalid id-right: expected '
                'dot-atom-text or domain-literal')
    msg_id.append(IdRight([token]))

    if not value.startswith(RANGLE.value):
        raise ParserError('id-right must be followed by ">"', value[:1])
    msg_id.append(RANGLE)
    return msg_id, value[1:]

#
# [CFWS] msg-id [CFWS] msg-id ... [CFWS]
# good for one msg-id for (Resent-)Message-ID and
# one or more msg-ids for In-Reply-To / References!!!
# just need to check with:
#
#    toks = parse_message_id('<a@foo.bar> <b@spam.baz>')
#    sum(isinstance(tik, MsgId) for tik in toks) or somethin...
#
def parse_message_ids(value, minimum=0, maximum=0):
    tokens = []
    count = 0
    while value:
        if RE_FWS.match(value) or value.startswith(LPAREN.value):
            token, value = get_cfws(value)
            tokens.append(token)
        if value.startswith(LANGLE.value):
            token, value = get_msg_id(value)
            tokens.append(token)
            count += 1
        else:
            break
    if value:
        raise ParserError('trailing data', value)
    if minimum and count < minimum:
        raise ParserError('expected a minimum of %d msg-id token%s, '
            'parsed %d' % (minimum, 's' * (minimum != 1), count))
    if maximum and count > maximum:
        raise ParserError('expected a maximum of %d msg-id token%s, '
            'parsed %d' % (maximum, 's' * (maximum != 1), count))
    return tokens

def parse_message_id(value):
    """Parse the Message-ID / Resent-Message-ID header as per RFC 5322."""
    return parse_message_ids(value, minimum=1, maximum=1)

def parse_references(value):
    """Parse the In-Reply-To / References header as per RFC 5322."""
    return parse_message_ids(value, minimum=1)
