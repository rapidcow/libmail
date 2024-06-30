# -*- coding: us-ascii -*-
"""outlook - for when the special snowflake does not comply with RFC

for now it just parses the annoying Thread-Index thing

header is tried and tested, but response level (namely the first
reply with a crazy ass number) is a whole nother beast which i
cannot deal with

note: the protocol is technically called exchange, outlook
being the program (???), but i named this outlook.py so that
i am less confused

copyright (c) 2024  Ethan Meng (rapidcow)
outlook.py is part of rdks-mail, licensed under GPLv3+:
<https://git.rapidcow.org/rdks-mail/about/>

outlook.py is free software: you may redistribute it and/or
modify it under the terms of GNU GPL version 3 or above.
to get one such license for reference, see
<https://www.gnu.org/licenses/>.

compose.py is free software: you may redistribute it and/or
modify it under the terms of GNU GPL version 3 or above.
to get one such license for reference, see
<https://www.gnu.org/licenses/>.
"""

__all__ = [
    'ThreadIndex', 'FileTime', 'Header', 'Response',
]

import base64
import datetime
import itertools
import struct
import uuid


def grouper(iterable, n):
    iterator = iter(iterable)
    while True:
        group = tuple(itertools.islice(iterator, n))
        if not group:
            return
        yield group


# adapted from:
# https://forum.rebex.net/3841/how-to-interprete-thread-index-header/
#
# documentation:
# PidTagConversationIndex, from Exchange Server Protocol Documents [OXOMSG] 2.2.1.3
# https://learn.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxomsg/9e994fbb-b839-495f-84e3-2c8c02c7dd9b
#
# PtypTime, from Data Structures [MS-OXCDATA] 2.11.1
# https://learn.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxcdata/0c77892e-288e-435a-9c49-be1c20c7afdb
#
class ThreadIndex(object):
    """The Thread-Index header, as described by the Microsoft
    Exchange protocol.  It consists of two parts: the 22-byte
    Conversation Index Header (not to be confused with a MIME
    header), and zero or more 7-byte Response Levels.
    They are accessible through the header as a Header object
    and responses as a tuple of Response objects.
    """
    def __init__(self, header, responses):
        self._header = header
        self._responses = tuple(responses)

    # TODO documentation :c
    # but if you are here, it should be evident
    # where the keyword args go...
    @classmethod
    def from_mime(cls, value, **kwargs):
        rawr = base64.b64decode(value)
        return cls.from_bytes(rawr, **kwargs)

    @classmethod
    def from_bytes(cls, raw, *, old_filetime=False):
        if (len(raw) - 22) % 5:
            raise ValueError('Thread-Index byte length not '
                             'congruent to 22 modulo 5')
        head = Header.from_bytes(raw[:22], old_filetime=old_filetime)
        resp = map(Response.from_bytes, map(bytes, grouper(raw[22:], 5)))
        return cls(head, resp)

    def __bytes__(self):
        trainwreck = itertools.chain([self.header], self.responses)
        return b''.join(map(bytes, trainwreck))

    def __str__(self):
        return base64.b64encode(bytes(self)).decode('ascii')

    def __repr__(self):
        return '<%s %s>' % (type(self).__qualname__, self)

    @property
    def header(self):
        """Conversation Index Header as a Header object."""
        return self._header

    @property
    def responses(self):
        """Response Level as a tuple of Response objects."""
        return self._responses

    def __hash__(self):
        return hash((self.header, self.responses))

    # since ThreadIndex is now immutable,
    # use these to append your own thing :)
    def add_response(self, response):
        return self.add_responses([response])

    def add_responses(self, responses):
        combined = itertools.chain(self.responses, responses)
        return type(self)(self.header, combined)


# this is for the five (or six???) time bytes in the header
#
# based on the following two additional documentations:
# FILETIME: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/2c57429b-fdd4-488f-b5fc-9e4cf020fcdf
# PtypTime: https://learn.microsoft.com/en-us/openspecs/exchange_server_protocols/ms-oxcdata/0c77892e-288e-435a-9c49-be1c20c7afdb
#
# also based on get_time() from msg_parser (which implements PtypTime parsing):
# https://msg-parser.readthedocs.io/en/latest/_modules/msg_parser/data_models.html#get_time
#
# why does Microsoft document the same format under two names?
# i don't know, but either way i don't like it >:(
#
class FileTime(object):
    """Representation of PtypTime, aka [MS-DTYP] FILETIME."""

    # FILETIME counts from Jan 01 1601 (why...)
    BASE = datetime.datetime(1601, 1, 1)
    # ... in increments of 1/10^7 of a second (WHY??!?)
    PREC = 10000000

    # Unix epoch starts with a much more sensible time.
    # Keep this so we can discard the 3 centuries of difference.
    # (This difference in seconds, the obvious correct unit of time)
    UNIX = 11644473600

    # welp, i wrote so much not knowing what this is called
    # only to realize that the .NET code thingy called it "ticks"...
    # for interface consistency i guess we'll call it that too?
    def __init__(self, ticks):
        # do we even have to check if intervals is in bound?
        # chances are CPython can't store integers that large...
        self._intervals = ticks

    @property
    def ticks(self):
        """The internal representation of time, number of
        1/10^7 second (100 ns) intervals since 1601."""
        return self._intervals

    def __repr__(self):
        return '%s(%r)' % (type(self).__qualname__, self.ticks)

    def __hash__(self):
        return hash(self.ticks)

    # instead of signed long long like how msg_parser it
    # i think we should just use unsigned and forget about it...
    @classmethod
    def from_bytes(cls, data):
        (intervals,) = struct.unpack('>Q', data)
        return cls(intervals)

    def __bytes__(self):
        return struct.pack('>Q', self.ticks)

    def low_datetime(self):
        """Return dwLowDateTime as a DWORD (unsigned 32-bit int)."""
        return self.ticks & 0xfffffff

    def high_datetime(self):
        """Return dwHighDateTime as a DWORD (unsigned 32-bit int)."""
        return self.ticks >> 32

    def as_unix(self, scale=100 * PREC):
        """Convert to Unix epoch in nanoseconds, divided by 'scale'.
        By default the scale is 100*PREC so that the epoch is in seconds.
        If you want Microsoft's weird scale, pass in 100.

        P.S. try to make scale a multiple of 100, but if not possible,
        don't make the scale too big (> 1/100th of max int), or else
        multiplication might explode (?)
        """
        origin = self.UNIX * self.PREC
        epoch = self.ticks - origin
        s, t = divmod(scale, 100)
        if not t:
            # multiple of 100 - free win!
            return epoch // s
        # count on Python to handle floor(epoch * 100 / scale),
        # this division mitigates case where 100*epoch would be
        # too large, but we can only pray that r (bounded by scale)
        # is small enough....
        q, r = divmod(epoch, scale)
        return 100 * q + 100 * r // scale

    @classmethod
    def from_unix(cls, epoch, scale=100 * PREC):
        """Inverse of as_unix()."""
        s, t = divmod(scale, 100)
        if not t:
            scaled = epoch * s
        else:
            q, r = divmod(epoch, 100)
            scaled = q * scale + r * scale // 100

        origin = cls.UNIX * cls.PREC
        return cls(scaled + origin)

    def as_datetime(self):
        """Convert to a Python datetime.  Always returns a naive
        datetime object computed directly from the offset."""
        seconds, remainder = divmod(self.ticks, self.PREC)
        # discard that 1/10 of a microsecond we can't make use of
        remainder //= 10
        offset = datetime.timedelta(seconds=seconds, microseconds=remainder)
        return self.BASE + offset

    @classmethod
    def from_datetime(cls, dt):
        """Inverse of as_datetime().  Naive datetimes are parsed as-is,
        while aware datetimes are converted into UTC first and then
        processed identically."""
        if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
            utctime = dt.astimezone(datetime.timezone.utc)
            return cls.from_datetime(utctime.replace(tzinfo=None))
        offset = dt - cls.BASE
        seconds = offset.seconds + offset.days * 86400
        return cls(seconds * cls.PREC + offset.microseconds * 10)


class Header(object):
    """The Conversation Index Header."""
    def __init__(self, date: FileTime, guid: uuid.UUID,
                 *, old_filetime=False):
        self._date = date
        self._guid = guid
        self._use_old_time = old_filetime

    @classmethod
    def from_bytes(cls, header, *, old_filetime=False):
        if len(header) != 22:
            raise ValueError('Header should be exactly 22 bytes long')
        # reserved (8 bits): SHOULD always equal 0000 0001, though
        # we won't reinforce it unless it's the new filetime format
        if header[0] != 0x01 and not old_filetime:
            raise ValueError('reserved byte mismatch')
        # current FILETIME (40 bits): time of delivery, in UTC
        # the 64-bit int is chopped off at the 24th bit (3rd byte),
        # making this a measure of time marginally less precise
        # than a second (~ 1.677 s).  for the old format we just
        # start from the first byte instead of the second, and
        # we can do that since the most significant byte is 0000 0001
        # throughout 1820-ish and 2053, which is... so far the
        # entirety of time computers have existed for.
        #
        # nonetheless, we will pad it back & reconstruct the full
        # number because i am getting a headache staring at these
        # partial bytes of gibberish >:(
        start = 0 if old_filetime else 1
        date = FileTime.from_bytes(header[start:6].ljust(8, b'\0'))
        # the rest is just random gibberish (16 bytes of GUID,
        # but c'mon... we all know UUID is gibberish.... >_>)
        guid = uuid.UUID(bytes=header[6:22])
        return cls(date, guid, old_filetime=old_filetime)

    @property
    def date(self):
        return self._date

    @property
    def guid(self):
        return self._guid

    @property
    def uses_old_filetime(self):
        return self._use_old_time

    def __repr__(self):
        qname = type(self).__qualname__
        return '%s(%r, %r)' % (qname, self.date, self.guid)

    def __hash__(self):
        return hash((self.date, self.guid))

    def __bytes__(self):
        if self._use_old_time:
            # we count on the user setting date to something before
            # 2053 so that the leftmost byte is 0000 0001 and can be
            # compliant with microsoft's specs.
            #
            # but then if they don't... well i ain't complaining either :)
            return b''.join([bytes(self.date)[:6], self.guid.bytes])
        else:
            return b''.join([b'\x01', bytes(self.date)[:5], self.guid.bytes])


class TimeDiff(object):
    """Representation of the 4-byte TimeDiff at the beginning of
    each response level.  (I really don't have a good name for this.)

    This works in the dumbest way possible: it looks at the first bit,
    sig, and shifts value by 18 bits if it's 0, or 23 bits if it's 1.
    This obtained value is then the measure of time difference in
    tenths of a microsecond (a "tick" in Microsoft terminology?)

    If you come across some weird b1cx value, well this isn't smart enough
    to handle that, because its programmer (me, Ethan) isn't smart enough
    to figure out how the heck that works :(
    """

    # maximum timedelta representable by sig=0 and sig=1 respectively.
    # it is a ValueError to try to set a timedelta outside of this range.
    MAX_SMALL_TICKS = 0x7fffffff << 18
    MAX_LARGE_TICKS = 0x7fffffff << 23

    def __init__(self, sig, value):
        if sig == 0 and value > self.MAX_SMALL_TICKS:
            raise ValueError('number of ticks %d (hex %#x) '
                             'out of range for sig=0' % (value, value))
        if sig == 1 and value > self.MAX_LARGE_TICKS:
            raise ValueError('number of ticks %d (hex %#x) '
                             'out of range for sig=1' % (value, value))
        self._sig = sig
        self._value = value

    @classmethod
    def from_bytes(cls, diff):
        (packet,) = struct.unpack('>I', diff)
        sig = packet >> 31
        value = packet & 0x7fffffff # -~(1 << 31)
        return cls(sig, value)

    @property
    def sig(self):
        """The signal bit.  This is 0 for 18 bit shift
        or 1 for 23 bit shift."""
        return self._sig

    @property
    def value(self):
        """The magnitude to be shifted as per sig."""
        return self._value

    def __repr__(self):
        return '%s(%r, %r)' % (type(self).__qualname__, self.sig, self.value)

    def __hash__(self):
        return hash((self.sig, self.value))

    def __bytes__(self):
        return struct.pack('>I', self.sig << 31 | self.value)

    def ticks(self):
        if self.sig:
            return self.value << 23
        return self.value << 18

    @classmethod
    def from_ticks(cls, ticks):
        if ticks < 0:
            raise ValueError('cannot represent negative ticks')
        if ticks > cls.MAX_SMALL_TICKS:
            sig = 1
            value = ticks >> 23
        else:
            sig = 0
            value = ticks >> 18
        return cls(sig, value)

    def as_timedelta(self):
        return datetime.timedelta(microseconds=self.ticks() // 10)

    @classmethod
    def from_timedelta(cls, delta):
        seconds = delta.days * 86400 + delta.seconds
        ticks = seconds * 10000000 + delta.microseconds * 10
        return cls.from_ticks(ticks)

    # as for arithmetic / comparison, stick to ticks or timedelta
    # i don't think i care enough to do add/subtract here given its
    # hideously lossy representation ;)


class Response(object):
    """A Response Level."""
    def __init__(self, delta: TimeDiff, random: int):
        self._delta = delta
        self._random = random

    @classmethod
    def from_bytes(cls, value):
        delta = TimeDiff.from_bytes(value[:4])
        (random,) = struct.unpack('>B', value[4:])
        return cls(delta, random)

    @property
    def delta(self):
        return self._delta

    @property
    def random(self):
        return self._random

    def __repr__(self):
        qname = type(self).__qualname__
        return '%s(%r, %r)' % (qname, self.delta, self.random)

    def __hash__(self):
        return hash((self.delta, self.random))

    def __bytes__(self):
        return bytes(self.delta) + struct.pack('>B', self.random)
