"""patch for msg-id line wrapping"""

from email.errors import HeaderDefect
import email.headerregistry
import re

from rdks.mail.headers.parser import parse_message_id
from rdks.mail.headers.parser import parse_references
from rdks.mail.headers.parser import ParserError
from rdks.mail.headers.tokens import MsgId, IdLeft, IdRight
from rdks.mail.headers.tokens import Text, Tokens, WhiteSpaceToken
from rdks.mail.headers.tokens import LANGLE, ATSIGN, RANGLE
from rdks.mail.headers.format import simple_fold

# XXX: all variables are implementation details for now
# just know that they probably work with policy.fold()
# and HeaderRegistry.__call__() i guess
#
# also the d in Id is lowercase for some reason :/
# idk, my choice

class InvalidHeaderDefect(HeaderDefect):
    """invalid rfc 5322 header"""

# overrides some very weird (and undocumented) BaseHeader mechanics
# the parse() method was a class method, but i decided to change it
# because typing @classmethod all the time hurts my fingers :)
# (also this could really use a factory pattern.... but but well
#  eh, for now we'll just pretend that parse_*() methods don't exist
#  after initialization =v=)
class ParsedHeader(str):
    # just create the object, thank you.....
    def __new__(cls, name, value):
        # our direct parent will be BaseHeader, so we can't use super here.
        return str.__new__(cls, value)

    # and let's use __init__ instead of init for this???
    # seriously, who wrote the new email library code....
    def __init__(self, name, value):
        self._name = name
        self._tokens, self._defects = self.parse(value)

    @property
    def name(self):
        return self._name

    @property
    def tokens(self):
        return Tokens(self._tokens)

    #
    # and there is this effectively unusable 'decoded' property
    # you cannot access (not a public API that is, TECHNICALLY
    # you can but that's not what i mean :c)?
    #
    # overriding __str__() would be a bit too evil, and
    # naming this with decode() would mess up polymorphism
    # (some guys would believe this is a bytes-like object)
    #
    # so maybe instead i will use this....:
    #
    def normalize(self):
        return str(self)
    #
    # (though more useful properties exist for specific RFC headers)

    def parse(self, value):
        try:
            return (self.parse_strict(value), [])
        except ParserError as e:
            retreat = self.parse_sloppy(value)
            exc_msg = '[%s] %s' % (type(e).__qualname__, e)
            return (retreat, [InvalidHeaderDefect(exc_msg)])

    def parse_strict(self, value):
        raise NotImplementedError

    def parse_sloppy(self, value):
        raise NotImplementedError

    def fold(self, *, policy):
        return simple_fold(self.name, self.tokens, policy=policy)


class MessageId(ParsedHeader):
    @staticmethod
    def parse_strict(value):
        return parse_message_id(value)

    @staticmethod
    def parse_sloppy(value):
        # make out something from that thing inside <...>?
        count, tokens = _xxx_sloppily_parse_msg_id_list_xxx_(value)
        if count != 1:
            # that's it, i give up.
            return [WhiteSpaceToken([Text(value)])]
        return tokens

class UniqueMessageId(MessageId):
    max_count = 1


class MessageIdList(ParsedHeader):
    @staticmethod
    def parse_strict(value):
        return parse_references(value)

    @staticmethod
    def parse_sloppy(value):
        count, tokens = _xxx_sloppily_parse_msg_id_list_xxx_(value)
        return tokens

    def idlist(self):
        return self.token

class UniqueMessageIdList(MessageIdList):
    max_count = 1


# the name should tell you how fucking dirty this function is
def _xxx_sloppily_parse_msg_id_list_xxx_(value):
    from rdks.mail.headers.tokens import WhiteSpaceToken
    bogus = []
    msg_id_count = 0
    current = []
    chunks = value.split(LANGLE.value)
    first = True
    for part in chunks:
        close = part.find(RANGLE.value)
        if close != -1:
            current.append(part[:close])
            maybe_a_msgid = ''.join(current)
            node = MsgId()
            if first:
                if part:
                    bogus.append(WhiteSpaceToken([Text(part)]))
                continue
            node.append(LANGLE)
            # is there an at sign?
            left, at, right = maybe_a_msgid.partition(ATSIGN.value)
            if at:
                node.append(IdLeft([Text(left)]))
                node.append(ATSIGN)
                node.append(IdRight([Text(right)]))
            else:
                # no??? good cuz i'm going insane too
                node.append(Text(maybe_a_msgid))
            node.append(RANGLE)
            bogus.append(node)
            msg_id_count += 1
            if part[close + 1:]:
                bogus.append(WhiteSpaceToken([Text(part[close + 1:])]))
        else:
            if part or not first:
                if not bogus or not isinstance(bogus[-1], WhiteSpaceToken):
                    bogus.append(WhiteSpaceToken())
                bogus[-1].append(Text(part if first else LANGLE.value + part))
        first = False
    return msg_id_count, bogus


class HeaderRegistry(email.headerregistry.HeaderRegistry):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        # the fact that the user is using this class means that
        # they want default handlers.... right
        self.map_to_type('Message-ID', UniqueMessageId)
        self.map_to_type('Resent-Message-ID', MessageId)
        self.map_to_type('In-Reply-To', UniqueMessageIdList)
        self.map_to_type('References', UniqueMessageIdList)
