"""RFC 2047/2148/2231 EW encoder"""
import string
import base64

def encode_word(word, encoding='B', charset='ISO-8859-1', language=None):
    if isinstance(word, str):
        word = word.encode(charset)

    encode = encoding.upper()
    if encode == 'B':
        eword = encode_base64(word)
    elif encode == 'Q':
        eword = encode_qp(word)
    else:
        raise ValueError('invalid encoding: %r' % (encoding,))

    charlc = (charset.encode('ascii') if language is None else
        b'%b*%b' % (charset.encode('ascii'), language.encode('ascii')))
    return b'=?%b?%b?%b?=' % (charlc, encoding.encode('ascii'), eword)

# safe characters to use in an RFC822 phrase
# (RFC 2047 5.3)
RFC2047_SAFE_ASCII = set(
    string.ascii_letters.encode('ascii') +
    string.digits.encode('ascii') + b'!*+-/'
)
RFC2047_UNSAFE_ASCII = set(b'=_?')
def encode_qp(word):
    """RFC 2047 4.2."""
    b = bytearray()
    for c in word:
        if c in RFC2047_SAFE_ASCII:
            b.append(c)
        elif c == 0x20:
            b.extend(b'_')
        elif c in RFC2047_UNSAFE_ASCII or (c < 0x20) or (c >= 0x7f):
            b.extend(b'=%02X' % (c,))
    return bytes(b)

def encode_base64(word):
    return base64.b64encode(word)
