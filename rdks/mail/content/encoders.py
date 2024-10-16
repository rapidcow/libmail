"""pedantic mime transfer encoders"""

import binascii
import io
import itertools

__all__ = [
    'EncodingError', 'treol',
    'encode_qp', 'encode_base64', 'encode_verbatim',
]

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
    if not body:
        yield b'', b''
        return
    lines = body.splitlines(keepends=True)
    for line in lines:
        yield _split_eol(line)

def _split_eol(line):
    for off, eol in EOL_MARKERS:
        if line.endswith(eol):
            return line[:-off], eol
            break
    else:
        return line, b''


class EncodingError(ValueError):
    pass

def treol(body, linesep=b'\r\n', fixeol=False):
    """translate EOL uniformly to linesep"""
    lines = []
    for line, eol in _iter_lines(body):
        lines.append(line)
        if fixeol or eol:
            lines.append(linesep)
    return MTSTR.join(lines)

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
def encode_qp(body, *, maxlinelen=80, linesep=b'\r\n',
              canonical_linesep=None, wrap=True, embed=None, protect=True):
    """do quoted-printable encoding as per RFC 2045 6.7.

    maxlinelen - line limit INCLUDING linesep (EOL)
                 (defaults to 78+2 = 80 as per RFC recommendation)
    linesep - end-of-line marker (EOL), can be any one of CR/LF/CRLF
              (defaults to CRLF)

    QP specific options:

    wrap - (True/False) treat CR/LF/CRLF as semantic line breaks
           and open a newline after each (defaults to True)
    embed - True ('all') for line and EOLs, False ('line') for line
            only (EOLs are encoded), 'printable' for non-control
            characters only (tabs always encoded), 'visible' for
            visible characters only (spaces also always encoded),
            and 'none' for nothing (everything is encoded)
            (defaults to whatever wrap is)
    protect - (True/False) ensure that the encoded string always
              ends with linesep.  This is probably important due to
              SMTP relying on that last CRLF to terminate the body.

    one more out-of-place kwarg to cater to python's email package's quirks:

    canonical_linesep - if specified, output the equivalence of
        encode_qp(*args, *kwds).replace(linesep, canonical_linesep)
    """
    if canonical_linesep is None:
        canonical_linesep = linesep
    if embed is None:
        embed = bool(wrap)
    if isinstance(embed, bool):
        embed = ('line', 'all')[embed]
    if embed not in {'all', 'line', 'printable', 'visible', 'none'}:
        raise ValueError("embed should be one of 'all', 'line', "
                         "'printable', 'visible', and 'none', "
                         "not %r" % (embed,))
    buffer = io.BytesIO()
    maxbearlen = maxlinelen - len(linesep)
    softsep = b'=' + canonical_linesep
    # less than 1; probably not positive
    if maxbearlen < 1:
        raise EncodingError('maxlinelen not longer than than len(linesep)')
    if not wrap:
        bigline, bigeol = _split_eol(body)
        if bigeol == linesep and embed == 'all':
            _encode_qp_line(buffer, bigline, False, maxbearlen,
                            canonical_linesep, 'line')
            buffer.write(canonical_linesep)
        else:
            _encode_qp_line(buffer, bigline + bigeol, protect, maxbearlen,
                            canonical_linesep, embed)
            if protect:
                buffer.write(softsep)
    else:
        nextsep = MTSTR
        lastsep = MTSTR
        lines = peeker(_iter_lines(body))
        for line, eol in lines:
            buffer.write(nextsep)
            if eol == linesep and embed == 'all':
                _encode_qp_line(buffer, line, False,
                                maxbearlen, canonical_linesep,
                                'line')
                nextsep = canonical_linesep
                lastsep = canonical_linesep
            else:
                _encode_qp_line(buffer, line + eol,
                                protect or lines.has_next(),
                                maxbearlen, canonical_linesep,
                                embed)
                nextsep = softsep
                lastsep = softsep if protect else MTSTR
        buffer.write(lastsep)
    return buffer.getvalue()

def _encode_qp_line(fp, line, pad, maxbearlen, linesep, embed):
    spaceleft = maxbearlen
    sentinel = MTSTR # suffices.
    lastbyte = None
    _encode = (_encode_every_qp_byte if embed == 'none' else
               _encode_nvis_qp_bytes if embed == 'visible' else
               _encode_ctrl_qp_bytes if embed == 'printable' else
               _encode_some_qp_bytes) # embed == 'line'
    for thisbyte, nextbyte in pairwise(_encode(line, sentinel)):
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
        more = len(thisbyte) - reserved
        s = ' is' if more == 1 else 's are'
        # ... unless we don't, in which case we are just f**ked
        raise EncodingError('maxlinelen is too small to encode the '
                            'first byte of a line (at least %d more '
                            'byte%s needed)' % (more, s))

def _encode_some_qp_bytes(line, sentinel):
    lastbyte = None
    for byte in line:
        if lastbyte is not None:
            yield QP_INNER[lastbyte]
        lastbyte = byte
    if lastbyte is not None:
        yield QP_FINAL[lastbyte]
    yield sentinel

def _encode_ctrl_qp_bytes(line, sentinel):
    for byte, encoded in zip(line, _encode_some_qp_bytes(line, sentinel)):
        yield b'=09' if byte == 0x09 else encoded
    yield sentinel

def _encode_nvis_qp_bytes(line, sentinel):
    for byte in line:
        yield QP_FINAL[byte]
    yield sentinel

def _encode_every_qp_byte(line, sentinel):
    for byte in line:
        yield b'=%02X' % byte
    yield sentinel

# the thing about base64 (though not mentioned in RFC?)
# is that every line is expected to be a decodable "chunk",
# so we can't wrap at arbitrary digits (XXX: probably...?)
def encode_base64(body, *, maxlinelen=None, linesep=b'\r\n',
                  canonical_linesep=None):
    """do base64 encoding.  this is just a pretty wrapper of
    binascii.b2a_base64().  should be RFC 2045 6.8 compliant :/

    maxlinelen - line length limit INCLUDING linesep
                 (default 19x4 = 76 plus len(linesep), consistent with
                  the width that python's stdlib seems to use.

                  if len(linesep) for some unholy reason exceeds 4,
                  this decreases correspondingly by multiples of 4
                  so that the total line length doesn't exceed 80.)

                 if this is 0, no line wrapping is done.

                 note that if you pass a maxlinelen that is not a
                 multiple of 4 IT WOULD FILL UP THE WHOLE SPACE.
                 round it to the nearest multiple of 4 if you want
                 each line to be decodable on their own.
    linesep - line separator, appended to the very end.

    canonical_linesep - see encode_qp().
    """
    itsy = binascii.b2a_base64(body, newline=False)
    if canonical_linesep is None:
        canonical_linesep = linesep
    if maxlinelen is None:
        permitted = 80 - len(linesep)
        maxbearlen = permitted // 4 * 4 or permitted
    elif maxlinelen:
        maxbearlen = maxlinelen - len(linesep)
    else:
        return itsy
    if maxbearlen < 1:
        raise EncodingError('base64 encoding needs at least '
                            '1 character per line minus linesep')
    bitsy = canonical_linesep.join(map(bytes, grouper(itsy, maxbearlen)))
    return bitsy

# 7bit and 8bit content are transferred as-is so this isn't
# really encoding anything thing. HOWEVER, we still need to
# make sure check for lone CR/LF and raise an error for any
#
# this is due to RFC 5322 2.3 and 3.5, which explicitly forbids
# CR and LF appearing in the message body. the rationale, i recall,
# is something along the lines of 7bit / 8bit encoding representing
# text content, so CRLF represents the canonical end-of-line marker.
# (CRLF isn't meant to be taken more literally than that, since in text
#  there are... lines. and CR/LF/CRLF all simply serve to separate them)
#
# this process is generalized to any linesep, though the default
# should be RFC compliant... i hope.
#
def encode_verbatim(body, *, maxlinelen=80, linesep=b'\r\n',
                    canonical_linesep=None, ascii=False):
    """Encode 7bit / 8bit content.

    This function only checks if everything is sanitized
    (i.e. each line is ONLY delimited by linesep and not any
    other CRLF sequence).  For EOL translation which most programs
    perform implicitly, see treol().

    Optionally canonicalize linesep (?) please pretend this is
    implementaion detail or interface consistency, this isn't
    much different than just str.replace() swear....
    """
    if canonical_linesep is None:
        canonical_linesep = linesep
    maxbearlen = maxlinelen - len(linesep)
    if maxbearlen < 1:
        raise EncodingError('maxlinelen not longer than than len(linesep)')
    # since python always splits on occurrences of CR/LF, we
    # just check if EOL ever mismatches the given linesep :D
    #
    # note that since we are bailing out of the function on
    # the first error, i is always going to count the number
    # of linesep
    for lineno, (line, eol) in enumerate(_iter_lines(body)):
        if eol and eol != linesep:
            raise EncodingError('misplaced CRLF sequence %r '
                                'found on line %d' % (eol, lineno + 1))
        if maxlinelen and len(line) > maxbearlen:
            raise EncodingError('line limit exceeded (%d > %d)'
                                % (len(line), maxbearlen))
    if canonical_linesep != linesep:
        body = body.replace(linesep, canonical_linesep)
    if ascii:
        try:
            body.decode('us-ascii')
        except UnicodeDecodeError as e:
            raise EncodingError('body is not ascii') from e
    return body
