"""pedantic mime transfer encoders"""

import binascii
import io
import itertools

__all__ = ['encode_qp', 'encode_base64']

try:
    # added in python 3.10!!! :o
    pairwise = itertools.pairwise
except AttributeError:
    def pairwise(iterable):
        iterator = iter(iterable)
        a = next(iterator, None)
        for b in iterator:
            yield a, b
            a = b

try:
    # added in python 3.12
    grouper = itertools.batched
except AttributeError:
    def grouper(iterable, n):
        iterator = iter(iterable)
        while True:
            group = tuple(itertools.islice(iterator, n))
            if group:
                yield group
            else:
                break

class peeker:
    __slots__ = ('iterator', 'peekaboo')

    def __init__(self, iterable):
        self.iterator = iter(iterable)

    def __iter__(self):
        return self

    def __next__(self):
        try:
            item = self.peekaboo
            del self.peekaboo
        except AttributeError:
            item = next(self.iterator)
        return item

    def has_next(self):
        try:
            item = next(self)
        except StopIteration:
            return False
        self.peekaboo = item
        return True

# empty string. yeah - and this is the obvious correct spelling of empty.
MTSTR = b''
EOL_MARKERS = [
    (2, b'\r\n'),
    (1, b'\n'),
    (1, b'\r'),
]

def _iter_lines(body):
    lines = body.splitlines(keepends=True)
    for line in lines:
        for off, eol in EOL_MARKERS:
            if line.endswith(eol):
                yield line[:-off], eol
                break
        else:
            yield line, b''

class EncodingError(ValueError):
    pass

# characters always allowed by RFC 2045 6.7.2
QP_INNER = tuple(
    bytes([i])            # use literal when...
    if (0x20 <= i < 0x7f  # space thru tilde "~"
        and i != 0x3d     # minus equal sign "="
        or i == 0x09)     # ... plus horizontal tab
    else b'=%02X' % i     # otherwise quote the guy
    for i in range(1<<8)  # (w/ UPPERCASE digits)
)
# spaces and tabs are allowed to be literal anywhere except the end
QP_FINAL = tuple(
    b'=20' if i == 0x20 else
    b'=09' if i == 0x09 else s
    for i, s in enumerate(QP_INNER)
)

# stolen from quopri.encode (native impl)
def encode_qp(body, maxlinelen=78, linesep=b'\r\n', embed=True, wrap=True):
    buffer = io.BytesIO()
    maxbearlen = maxlinelen - len(linesep)
    softsep = b'=' + linesep
    # less than 1; probably not positive
    if maxbearlen < 1:
        raise EncodingError('quoted-printable encoding needs at least '
                            '1 character per line minus linesep')
    if not embed:
        _encode_qp_line(buffer, body, False, maxbearlen, linesep)
    else:
        nextsep = MTSTR
        lastsep = MTSTR
        lines = peeker(_iter_lines(body))
        for line, eol in lines:
            buffer.write(nextsep)
            if eol == linesep and wrap:
                _encode_qp_line(buffer, line, False,
                                maxbearlen, linesep)
                nextsep = linesep
                lastsep = linesep
            else:
                _encode_qp_line(buffer, line + eol, lines.has_next(),
                                maxbearlen, linesep)
                nextsep = softsep
                lastsep = MTSTR
        buffer.write(lastsep)
    return buffer.getvalue()

def _encode_qp_line(fp, line, pad, maxbearlen, linesep):
    spaceleft = maxbearlen
    sentinel = MTSTR # suffices.
    lastbyte = None
    for thisbyte, nextbyte in pairwise(_encode_qp_bytes(line, sentinel)):
        # reserve one byte for soft wrap if we're not at the end
        # OR we're at the end but a padding is demanded
        reserved = spaceleft - (nextbyte is not sentinel or pad)
        # wrap immediately if no space
        if len(thisbyte) > reserved:
            # ... given we don't get ourselves stuck in a loop.
            if lastbyte is not None:
                fp.write(b'=')
                fp.write(linesep)
                reserved += maxbearlen - spaceleft
                spaceleft = maxbearlen
                lastbyte = None
        # now we're all "freed" up, we should have space to write
        if len(thisbyte) <= reserved:
            spaceleft -= fp.write(thisbyte)
            lastbyte = thisbyte
            continue
        # ... unless we don't, in which case we are just f**ked
        raise EncodingError('maxlinelen is too small to encode the '
                            'first byte of a line (at least %d bytes '
                            'are needed minus linesep)' % reserved)

def _encode_qp_bytes(line, sentinel):
    lastbyte = None
    for byte in line:
        if lastbyte is not None:
            yield QP_INNER[lastbyte]
        lastbyte = byte
    if lastbyte is not None:
        yield QP_FINAL[lastbyte]
    yield sentinel

# the thing about base64 (though not mentioned in RFC?)
# is that every line is expected to be a decodable "chunk",
# so we can't wrap at arbitrary digits
def encode_base64(body, maxlinelen=78, linesep=b'\r\n'):
    maxbearlen = maxlinelen - len(linesep)
    if maxbearlen < 1:
        raise EncodingError('base64 encoding needs at least '
                            '1 character per line minus linesep')
    itsy = binascii.b2a_base64(body, newline=False)
    bitsy = linesep.join(map(bytes, grouper(itsy, maxbearlen)))
    return bitsy
