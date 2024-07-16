"""rfc msg-id parser!

based loosely on get_msg_id in python's
email/_header_value_parser.py, though far more "lenient"
as it only scans for CFWS and the angled brackets
"""

__all__ = ['get_msg_id', 'get_msg_id_list']
__author__ = 'Ethan Meng'

import re

class ParseError(ValueError):
    def __init__(self, index, reason, token_at_fault=None):
        self.i = index
        self.s = reason
        self.x = token_at_fault

    def __str__(self):
        if self.x is not None:
            return 'char %s: %s: %r' % (self.i, self.s, self.x)
        return 'char %s: %s' % (self.i, self.s)

def parse_msg_id(index, value):
    """Parse msg-id as per RFC 5322, skipping the first comment folding
    whitespace (CFWS) if one exists, and terminating at the first closing
    angled bracket (">").

    Each line in 'value' is assumed to be delimited by CRLF.
    """
    # msg-id was first defined in RFC 822 as simply
    #
    #    msg-id      =  "<" addr-spec ">"
    #    addr-spec   =  local-part "@" domain
    #
    # RFC 2822 lifted this constraint and allowed for
    # optional CFWS before and after msg-id:
    #
    #    msg-id      =  [CFWS] "<" id-left "@" id-right ">" [CFWS]
    #    id-left     =  dot-atom-text
    #    id-right    =  dot-atom-text / no-fold-literal
    #
    # (omitting the obsolete syntax specified in RFC 822)
    #
    # our job here is to simply identify the leading CFWS and skip it.
    # we assume (for the sake of our own sanity) that the <left@right>
    # address enveloped inside is sound.
    orig = value
    try:
        if value[:1] in CFWS_LEADER:
            index, value = skip_cfws(index, value)
        close = value.find('>') + 1
        return index + close, value[:close], value[close:]
    except ValueError as e:
        raise ValueError('bad msg-id: %r' % (orig,)) from e

def get_msg_id(value):
    index, value, remain = parse_msg_id(0, value)
    if not (value.startswith('<') and value.endswith('>')):
        raise ValueError('msg-id is not enclosed in angled '
                         'brackets: %r' % (value,))
    return value

def get_msg_id_list(value):
    """Extract zero or more msg-id as per RFC 5322.
    This is just get_msg_id() but with multiple hops.
    """
    index = 0
    result = []
    while True:
        index, value, remain = parse_msg_id(index, value)
        if not value:
            index, remain = skip_cfws(index, remain)
            if remain:
                raise ParseError(
                    index, 'extraneous data while '
                    'parsing list of msg-id', remain)
            break
        if not (value.startswith('<') and value.endswith('>')):
            raise ValueError('msg-id is not enclosed in angled '
                             'brackets: %r' % (value,))
        result.append(value)
        value = remain
    return result


# RFC 2822, when CFWS was first introduced, defines it as follows:
#
#    NO-WS-CTL       =   %d1-8 /         ; US-ASCII control characters
#                        %d11 /          ;  that do not include the
#                        %d12 /          ;  carriage return, line feed,
#                        %d14-31 /       ;  and white space characters
#                        %d127
#    ctext           =   NO-WS-CTL /     ; Non white space controls
#                        %d33-39 /       ; The rest of the US-ASCII
#                        %d42-91 /       ;  characters not including
#                        %d93-126        ;  "(", ")", or "\"
#    quoted-pair     =   ("\" text) / obs-qp
#    obs-qp          =   "\" (%d0-127)
#    ccontent        =   ctext / quoted-pair / comment
#    comment         =   "(" *([FWS] ccontent) [FWS] ")"
#    CFWS            =   (1*([FWS] comment) [FWS]) / FWS
#    FWS             =   ([*WSP CRLF] 1*WSP) / obs-FWS
#    obs-FWS         =   1*WSP *(CRLF 1*WSP)
#
# where text is defined with
#
#    text            =   %d1-9 /         ; Characters excluding CR and LF
#                        %d11 /
#                        %d12 /
#                        %d14-127 /
#                        obs-text
#    obs-text        =   *LF *CR *(obs-char *LF *CR)
#    obs-char        =   %d0-9 / %d11 /          ; %d0-127 except CR and
#                        %d12 / %d14-127         ;  LF
#
# RFC 5322 uses the same definition except that it obsoletes the
# inclusion of NO-WS-CTL in ctext.
#
# Note the obs-char permits the null byte, and on top of that obs-text
# allows "bare CR and bare LF" with this quirky backward-CRLF construct.
# (This seems to have been defined retroactively given RFC 822's
#  loose verbal definition, so it's probably safe to say this has
#  never been employed for CFWS.)
#
# obs-FWS is probably irrelevant given how CFWS did not exist at
# the time of RFC 822's definition of FWS.
# (NOTE: FWS was called linear-white-space in RFC 822.)
#
# In both RFC's that WSP appears in, it is defined simply as the
# union of the space and the horizontal tab characters:
#
# RFC 2822, 2.2.2. Structured Header Field Bodies
#    Structured field bodies are sequences of specific lexical tokens
#    [...]  Many of these tokens are allowed to be introduced or end
#    with comments [...] as well as the space (SP, ASCII value 32) and
#    horizontal tab (HTAB, ASCII value 9) characters (together known as
#    the white space characters, WSP) [...]
#
# RFC 5322, 2.2. Header Fields
#    A field body may be composed of printable US-ASCII characters
#    as well as the space (SP, ASCII value 32) and horizontal tab
#    (HTAB, ASCII value 9) characters (together known as the white
#    space characters, WSP).

WSP = set(' \t')
RE_FWS = re.compile(r'^([ \t]*\r\n)?[ \t]+')
FWS_LEADER = WSP | set('\r')
CFWS_LEADER = FWS_LEADER | set('(')

def skip_cfws(index, value):
    while value:
        if value[0] in FWS_LEADER:
            index, value = skip_fws(index, value)
        if value[:1] == '(':
            index, value = skip_comment(index, value)
        else:
            break
    return index, value

def skip_fws(index, value):
    result = RE_FWS.sub('', value)
    return index + (len(value) - len(result)), result

def is_text(c):
    cp = ord(c)
    return 0 < cp < 128 and c not in '\r\n'

def is_ctext(c):
    cp = ord(c)
    return 32 < cp < 128 and c not in '()\\'

def skip_comment(index, value):
    assert value[0] == '(', 'comment does not begin with "("'
    value = value[1:]
    index += 1
    while value:
        if value[0] in FWS_LEADER:
            index, value = skip_fws(index, value)
        token = value[:1]
        if token == ')':
            break
        if token == '(':
            index, value = skip_comment(index, value)
            continue
        if token == '\\':
            pair = value[:2]
            if len(pair) != 2:
                raise ParseError(index, 'fragmented quoted-pair', pair)
            if not is_text(pair[1]):
                raise ParseError(index, 'invalid quoted-pair', pair)
            value = value[2:]
            index += 2
            continue
        if not (token and is_ctext(token)):
            raise ParseError(index, 'bad ctext', token)
        value = value[1:]
        index += 1
    if value[:1] != ')':
        raise ParseError(index, 'unterminated comment')
    return index + 1, value[1:]
