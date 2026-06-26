"""oh yeah i have to do this now too"""

import binascii
import io
import itertools

from .encoders import _iter_lines
from .encoders import MTSTR

__all__ = [
    'DecodingError', 'decode_qp', 'decode_base64', 'decode_verbatim',
]

class DecodingError(ValueError):
    pass

QP_TABLE = {b'%02X' % i: bytes([i]) for i in range(1<<8)}

def bytes_ishex(b):
    return all(0x30 <= c <= 0x39 or 0x41 <= c <= 0x46 for c in b)

def decode_qp(body, *, maxlinelen=80, linesep=b'\r\n',
              canonical_linesep=None):
    if canonical_linesep is None:
        canonical_linesep = linesep
    softsep = b'=' + linesep
    softlen = 1 + len(linesep)
    buffer = io.BytesIO()
    for lineno, (line, eol) in enumerate(_iter_lines(body)):
        if eol and eol != canonical_linesep:
            raise DecodingError('bad EOL marker on line %d: %r'
                                % (lineno + 1, eol))
        i = 0
        while i < len(line):
            c = line[i:i+1]
            if c != b'=':
                # just write verbatim. i'm not in the mood of
                # being so pedantic as to check if this is 7bit
                buffer.write(c)
                i += 1
            else:
                # soft break
                if i + 1 == len(line):
                    break
                # otherwise it must be two hex digits
                #
                # note that to support bytearray as body, type
                # conversion is needed because we need to look up
                # hexval in QP_TABLE and it needs to be bytes
                hexval = bytes(line[i+1:i+3])
                if len(hexval) != 2 or not bytes_ishex(hexval):
                    raise DecodingError('malformed QP escape: %r'
                                        % (hexval,))
                buffer.write(QP_TABLE[hexval])
                i += 3
        else:
            if eol:
                buffer.write(linesep)
    return buffer.getvalue()

def decode_base64(body, *, maxlinelen=None, linesep=b'\r\n',
                  canonical_linesep=None):
    # NOTE: maxlinelen doesn't really matter much?
    # we'd just be able to handle long lines anyways...
    # (not so much if we are writing in, say, C though.
    #  so we'd still take in the argument.)
    if canonical_linesep is None:
        canonical_linesep = linesep
    buffer = io.BytesIO()
    remains = bytearray()
    for lineno, (line, eol) in enumerate(_iter_lines(body)):
        # EOL doesn't really affect base64. we're just
        # overly picky about what gets passed around...
        if eol and eol != canonical_linesep:
            raise DecodingError('bad EOL marker on line %d: %r'
                                % (lineno + 1, eol))
        # Write 4q digits at a time, and leave the rightmost r
        # unaligned bytes to the next line (if there is any, well X)
        # For aligned base64 data, r must be 0 on the final line, so
        # we only have to worry about throwing an ugly error then.
        # (Should we be more generous in the future, we can pad
        #  remains just outside the loop & still do stuff with
        #  what's left... but I'm curious what would happen. :)
        q, r = divmod(len(remains) + len(line), 4)
        if q > 0:
            # zero ain't signed :(
            remains.extend(line[:-r] if r else line)
            try:
                # XXX: strict_mode????
                buffer.write(binascii.a2b_base64(remains))
            except binascii.Error as e:
                raise DecodingError(
                    'cannot decode chunk of length %d up to line %d'
                    % (len(remains), lineno + 1)) from e
            remains[:] = line[-r:] if r else MTSTR
        else:
            remains.extend(line)
    if remains:
        raise DecodingError('trailing chunk of length %d' % (len(remains),))
    return buffer.getvalue()

def decode_verbatim(body, maxlinelen=80, linesep=b'\r\n',
                    canonical_linesep=None, ascii=False):
    if canonical_linesep is None:
        canonical_linesep = linesep
    for lineno, (line, eol) in enumerate(_iter_lines(body)):
        if eol and eol != canonical_linesep:
            raise DecodingError('bad EOL marker on line %d: %r'
                                % (lineno + 1, eol))
    if canonical_linesep != linesep:
        body = body.replace(canonical_linesep, linesep)
    if ascii:
        try:
            body.decode('us-ascii')
        except UnicodeDecodeError as e:
            raise EncodingError('body is not ascii') from e
    return body
