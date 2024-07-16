"""parse tree tokens"""

# in CS, parse trees = concrete representation
# so we're not quite there at AST's yet :D

# note abt this thingy:
# * tokens are either NonTerminal (Tokens) or Terminal
# * str(token) restores the parsed string, verbatim
#      no more methods are defined!
# * some tokens are well-defined & mono-morphic (if that is a word),
#   others are not (expect the most abstract ones 2be more adaptive or
#   in other words have very f**ked-up standards and inconsistency)
# * folding = done elsewhere

# all terminals/nonterminals/constants, ordered from
# most abstract to least
__all__ = [
    # base tokens
    'Token', 'Tokens', 'Terminal', 'Text', 'Symbol',
    # constants
    'CRLF', 'SPACE', 'HTAB', 'COLON', 'SEMICOLON', 'ATSIGN',
    'BSLASH', 'COMMA', 'PERIOD', 'DQUOTE',
    'LPAREN', 'RPAREN', 'LANGLE', 'RANGLE', 'LBRACK', 'RBRACK',
    # character sets
    'WHITESPACE', 'VISIBLE', 'SPECIALS', 'CTEXT', 'ATEXT', 'DTEXT',
    # base tokens
    'WhiteSpaceToken',
    # RFC 5322, 3.2.1. Quoted characters
    'QuotedPair',
    # RFC 5322, 3.2.2. Folding White Space and Comments
    'FoldingWhiteSpace', 'WhiteSpace',
    'CommentFoldingWhiteSpace', 'Comment', 'CommentText',
    # RFC 5322, 3.2.3. Atom
    'AtomText', 'DotAtomText',
    # ... sections skipped
    # RFC 5322, 3.4.1. Addr-Spec Specification
    'DomainText', 'DomainLiteral',
    # ... more sections skipped
    # RFC 5322, 3.6.4. Identification Fields
    'MsgId', 'IdLeft', 'IdRight',
]

from abc import ABC, abstractmethod
import collections, itertools

_Nil = object()

class Token(ABC):
    __slots__ = ('_token_name', '_token_value')

    #
    # abstract methods:
    # value (property), __str__, __add__,
    # __iter__, __len__, __(get|set|del)item__
    #
    # defined methods:
    # __repr__, __eq__, select, __contains__
    #
    def __new__(cls, value=None, *, name=None):
        if name in cls._registry:
            if value is not None:
                raise ValueError(
                    'cannot re-create named token %s' % (name,)
                )
            return cls._registry[name]
        if value is None:
            raise ValueError('missing value') from None
        self = super().__new__(cls)
        self._token_value = value
        if name is not None:
            self._token_name = name
            cls._registry[name] = self
        return self

    def __init_subclass__(cls, name=None):
        cls.type_name = name or cls.__name__
        cls._registry = {}

    @property
    def name(self):
        return self._token_name

    # value is used for reconstruction / repr only
    @property
    @abstractmethod
    def value(self):
        pass

    def __repr__(self):
        try:
            return '%s(name=%r)' % (self.type_name, self.name)
        except AttributeError:
            return '%s(%r)' % (self.type_name, self.value)

    @abstractmethod
    def __str__(self):
        pass

    # NOTE: __add__ syntax is symmetric, while __iadd__ syntax is not
    # this can get confusing, so we will deny all other classes for now
    @abstractmethod
    def __add__(self, others):
        pass

    def __eq__(self, other):
        if type(self) is type(other):
            if hasattr(self, 'name') or hasattr(other, 'name'):
                try:
                    return self.name == other.name
                except AttributeError:
                    return False
            return self.value == other.value
        return super().__eq__(other)

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def __getitem__(self):
        pass

    @abstractmethod
    def __setitem__(self):
        pass

    @abstractmethod
    def __delitem__(self):
        pass

    # how do we tell terminals from nonterminals?
    # ... we don't ^v^
    def _filter(self, criteria):
        if criteria.startswith('not '):
            inverted = True
            criteria = criteria[4:]
        else:
            inverted = False
        for token in self:
            bases = type(token).mro()
            anymatch = False
            for base in bases:
                if base is Token:
                    break
                if base.type_name == criteria:
                    anymatch = True
                    break
            if inverted and not anymatch or anymatch and not inverted:
                yield token

    def filter(self, criteria):
        return type(self)(list(self._filter(criteria)))

    def select(self, criteria, index=0):
        gen = self._filter(criteria)
        next(itertools.islice(gen, index), None)
        try:
            return next(gen)
        except StopIteration:
            if default is not _Nil:
                return default
            raise IndexError('could not find match #%d '
                'under criteria %r' % (index, criteria)) from None

    def __contains__(self, value):
        return any(token is value and token == value for token in self)

class Terminal(Token):
    __slots__ = ()

    def __new__(cls, value=None, *, name=None):
        if not isinstance(value, str) and value is not None:
            raise TypeError('Terminal should be constructed with a str')
        return super().__new__(cls, value, name=name)

    @property
    def value(self):
        return self._token_value

    def __str__(self):
        return self.value

    def copy(self):
        return type(self)(self.value)

    def __add__(self, other):
        if type(self) is type(other):
            other = other.value
        if isinstance(other, str):
            return type(self)(''.join([self.value, other]))
        return NotImplemented

    def __iadd__(self, other):
        if type(self) is type(other):
            other = other.value
        return type(self)(''.join([self.value, other]))

    # this might seem weird, but isn't really once you
    # think about it.... these tell you about CHILD tokens,
    # which Terminals do not have any.
    def __iter__(self):
        return iter(())

    def __len__(self):
        return 0

    def __getitem__(self, index):
        raise IndexError('Terminal is not indexable')

    def __setitem__(self, index, value):
        raise IndexError('Terminal is not indexable')

    def __delitem__(self, index):
        raise IndexError('Terminal is not indexable')

class Tokens(Token):
    __slots__ = ()

    def __new__(cls, value=None):
        if value is None:
            value = collections.deque()
        elif isinstance(value, list):
            if all(isinstance(token, Token) for token in value):
                value = collections.deque(value)
            else:
                raise TypeError('some items are not Token')
        else:
            raise TypeError('Tokens should be constructed with '
                            'a list of Token instances')
        return super().__new__(cls, value)

    @property
    def value(self):
        return list(self._token_value)

    def __str__(self):
        return ''.join(map(str, self))

    def copy(self):
        return type(self)(self.value.copy())

    def __add__(self, others):
        if type(self) is type(others):
            clone = self.copy()
            clone += others
            return clone
        return NotImplemented

    def __iadd__(self, others):
        for other in others:
            self.append(other)
        return self

    def append(self, token):
        if not isinstance(token, Token):
            raise TypeError('cannot append non-Token item')
        if self and type(self[-1]) is type(token) \
                and not hasattr(token, 'name'):
            self[-1] += token
        else:
            self._token_value.append(token)

    def prepend(self, token):
        if not isinstance(token, Token):
            raise TypeError('cannot prepend non-Token item')
        if self and type(self[0]) is type(token) \
                and not hasattr(token, 'name'):
            self[0] += token
        else:
            self._token_value.appendleft(token)

    def __bool__(self):
        return not not self._token_value

    def __iter__(self):
        return iter(self._token_value)

    def __len__(self):
        return len(self._token_value)

    # sequence operations!
    def __getitem__(self, index):
        return self._token_value[index]

    def __setitem__(self, index, value):
        self._token_value[index] = value

    def __delitem__(self, index):
        del self._token_value[index]

class Text(Terminal):
    __slots__ = ()

class Symbol(Terminal):
    __slots__ = ()

CRLF      = Symbol("\r\n", name='CRLF')
# whitespace
SPACE     = Symbol(" ", name='SPACE')
HTAB      = Symbol("\t", name='HTAB')
# specials
COLON     = Symbol(":", name='COLON')
SEMICOLON = Symbol(";", name='SEMICOLON')
ATSIGN    = Symbol("@", name='ATSIGN')
BSLASH    = Symbol("\\", name='BSLASH')
COMMA     = Symbol(",", name='COMMA')
DQUOTE    = Symbol('"', name='DQUOTE')
# RFC 5322 does not call this a dot (despite the name "dot-atom-text")
# I guess it's only fair we do the same here...
PERIOD    = Symbol(".", name='PERIOD')
LPAREN    = Symbol("(", name='LPAREN')
RPAREN    = Symbol(")", name='RPAREN')
LANGLE    = Symbol("<", name='LANGLE')
RANGLE    = Symbol(">", name='RANGLE')
LBRACK    = Symbol("[", name='LBRACK')
RBRACK    = Symbol("]", name='RBRACK')

# character sets
# --------------
# known as WSP in RFC5234 Appendix B.1
WHITESPACE = set(map(str, [ SPACE, HTAB ]))
# known as VCHAR, for "visible characters"
# includes everything from ! up to ~
# NOTE: not quite the same as printable;
# whitespace characters are excluded
VISIBLE = set(map(chr, range(0x21, 0x7F)))
# this just has the same name as RFC5322
SPECIALS = set(map(str, [
    LPAREN, RPAREN,   # "(" ")"
    LANGLE, RANGLE,   # "<" ">"
    LBRACK, RBRACK,   # "[" "]"
    COLON, SEMICOLON, # ":" ";"
    ATSIGN, BSLASH,   # "@" "\"
    COMMA, PERIOD,    # "," "."
    DQUOTE,           # " itself
]))
# ctext           =   ;; VISIBLE minus "(" ")" "\"
CTEXT = VISIBLE - set(map(str, [ LPAREN, RPAREN, BSLASH ]))
# atext           =   ;; VISIBLE minus SPECIALS
ATEXT = VISIBLE - SPECIALS
# dtext           =   ;; VISIBLE minus "[" "]" "\"
DTEXT = VISIBLE - set(map(str, [ LBRACK, RBRACK, BSLASH ]))

# class Token(list):
#     # just in case i accidentally write Foo(Bar) instead of Foo([Bar])
#     def __new__(cls, *args, **kwds):
#         if args and not isinstance(args[0], list):
#             raise TypeError('lists only. sorry :(')
#         return super().__new__(cls, *args, **kwds)

#     def __repr__(self):
#         return '%s(%s)' % (type(self).__name__, super().__repr__())

#     def __str__(self):
#         return ''.join(map(str, self))

#     def __add__(self, other):
#         if type(self) is type(other) and type(self) is not Symbol:
#             base = []
#             base.extend(self)
#             base.extend(other)
#             return type(self)(base)
#         if isinstance(other, Token):
#             return NotImplemented
#         return super().__add__(other)

#     def append(self, token):
#         if isinstance(token, Terminal):
#             if self and type(self[-1]) is type(token) \
#                     and type(token) is not Symbol:
#                 self[-1] += token
#                 return
#         super().append(token)

#     # usage: select('MsgId') (the class __name__, no MRO) or
#     #        select( MsgId ) (the class itself, checks MRO ???)
#     def select(self, name):
#         for child in self:
#             if isinstance(name, str) and type(child).__name__ == name:
#                 yield child
#             elif isinstance(name, type) and isinstance(child, name):
#                 yield child
#             if isinstance(child, Token):
#                 yield from child.select(name)

# represents quoted-pair (RFC 5322, 3.2.1)
# NOTE: construct with just the unescaped string
class QuotedPair(Tokens):
    __slots__ = ()

# runs of FWS... semantically interpreted as a single space character.
class WhiteSpaceToken(Tokens):
    __slots__ = ()
# WSP guys (1+ htab or space)
class WhiteSpace(Text):
    __slots__ = ()
# represents FWS (RFC 5322, 3.2.2)
class FoldingWhiteSpace(WhiteSpaceToken):
    __slots__ = ()
# represents ctext
class CommentText(Text):
    __slots__ = ()
# represents comment (RFC 5322, 3.2.2)
# NOTE: do not construct me with LPAREN / RPAREN !!!!
class Comment(WhiteSpaceToken):
    __slots__ = ()
# represents CFWS (RFC 5322, 3.2.2)
class CommentFoldingWhiteSpace(WhiteSpaceToken):
    __slots__ = ()

# represents atext (RFC 5322, 3.2.3)
class AtomText(Text):
    __slots__ = ()
# represets dot-atom-text (RFC 5322, 3.2.3)
# NOTE: in spite of the name, DotAtomText is a token
# because it contains specials :(
class DotAtomText(Tokens):
    __slots__ = ()

# represents dtext (RFC 5322, 3.4.1)
class DomainText(Text):
    __slots__ = ()
# represents domain-literal (RFC 5322, 3.4.1)
#       and no-fold-literal (RFC 5322, 3.6.4)
# (NOTE: without CFWS)
class DomainLiteral(Tokens):
    __slots__ = ()

# represents id-left (RFC 5322, 3.6.4)
class IdLeft(Tokens):
    __slots__ = ()
# represents id-right (RFC 5322, 3.6.4)
class IdRight(Tokens):
    __slots__ = ()
#
# represents msg-id (RFC 5322, 3.6.4)
# note that this version is without CFWS bc it just
# doesn't feel right to say which CFWS belongs to which
# Comment .... at least to me.
#
# also, we are not implying the validity of
# two consecutive CFWS's, right?
#
class MsgId(Tokens):
    __slots__ = ()
