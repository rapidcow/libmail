# wow i actually wrote test
"""test content transfer encodings"""

from rdks.mail.content import treol
from rdks.mail.content import encoders, EncodingError
from rdks.mail.content import decoders, DecodingError
import binascii
import unittest

class TestUtilities(unittest.TestCase):
    def test_treol(self):
        self.assertEqual(treol(b''), b'')
        self.assertEqual(treol(b'\n'), b'\r\n')
        self.assertEqual(treol(b'foo\nbar'), b'foo\r\nbar')
        self.assertEqual(treol(b'foo\nbar\n'), b'foo\r\nbar\r\n')
        self.assertEqual(treol(b'foo\nbar\r\n'), b'foo\r\nbar\r\n')
        self.assertEqual(treol(b'foo\nbar\n\r'), b'foo\r\nbar\r\n\r\n')

        # fixed
        self.assertEqual(treol(b'', fixeol=True), b'\r\n')
        self.assertEqual(treol(b'foo\nbar', fixeol=True), b'foo\r\nbar\r\n')
        # not fixed
        self.assertEqual(treol(b'\n', fixeol=True), b'\r\n')
        self.assertEqual(treol(b'foo\nbar\r\n', fixeol=True),
            b'foo\r\nbar\r\n')
        self.assertEqual(treol(b'foo\nbar\n\r', fixeol=True),
            b'foo\r\nbar\r\n\r\n')

class TestEncoders(unittest.TestCase):
    def test_encode_qp(self):
        self.assertEqual(encoders.encode_qp(b'', protect=False), b'')
        self.assertEqual(encoders.encode_qp(b''), b'=\r\n')
        self.assertEqual(encoders.encode_qp(b'\n'), b'=0A=\r\n')
        self.assertEqual(encoders.encode_qp(b'\r\n'), b'\r\n')
        self.assertEqual(encoders.encode_qp(
            b'hello, w\r\norld', maxlinelen=7),
            b'hell=\r\no, w\r\norld=\r\n')
        self.assertEqual(encoders.encode_qp(
            b'hello, w\r\norld', maxlinelen=7, canonical_linesep=b'\n'),
            b'hell=\no, w\norld=\n')
        self.assertEqual(encoders.encode_qp(b'hello: ', protect=False),
                                                         b'hello:=20')
        self.assertEqual(encoders.encode_qp(b'hello:\t', protect=False),
                                                          b'hello:=09')

    def test_encode_qp_eol_handling(self):
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol'), b'espa=F1ol=\r\n')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n', protect=False),
                                                              b'espa=F1ol=0A')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n\r\n'),
                                                     b'espa=F1ol=0A=\r\n\r\n')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\r', protect=False,
                                                           ), b'espa=F1ol=0D')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n\r', protect=False),
                                                      b'espa=F1ol=0A=\r\n=0D')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n\r', wrap=False),
                                                      b'espa=F1ol=0A=0D=\r\n')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n\r\n', wrap=False),
                                                   b'espa=F1ol=0A=0D=0A=\r\n')
        # this makes sense now! yippee!!! XD
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n\r\n',
            wrap=False, embed=True), b'espa=F1ol=0A\r\n')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\r\n'),
            b'espa=F1ol\r\n')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\r\n',
            embed=False, protect=False), b'espa=F1ol=0D=0A')

    def test_encode_qp_line_wrapping(self):
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol', maxlinelen=8,
            protect=False), b'espa=\r\n=F1ol')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n', maxlinelen=8,
            protect=False), b'espa=\r\n=F1ol=\r\n=0A')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\r\n', maxlinelen=8,
            protect=False), b'espa=\r\n=F1ol\r\n')
        # test canonical linesep
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol', maxlinelen=8,
            protect=False, canonical_linesep=b'\n'), b'espa=\n=F1ol')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\n', maxlinelen=8,
            protect=False, canonical_linesep=b'\n'), b'espa=\n=F1ol=\n=0A')
        self.assertEqual(encoders.encode_qp(b'espa\xf1ol\r\n', maxlinelen=8,
            protect=False, canonical_linesep=b'\n'), b'espa=\n=F1ol\n')

    def test_encode_qp_with_terribly_narrow_maxlinelen(self):
        self.assertEqual(encoders.encode_qp(b'some str\xedng d\xf6th '
            b'ne\xe8d protec\xe7', maxlinelen=6),
            b'som=\r\n'
            b'e s=\r\n'
            b'tr=\r\n'
            b'=ED=\r\n'
            b'ng =\r\n'
            b'd=\r\n'
            b'=F6=\r\n'
            b'th =\r\n'
            b'ne=\r\n'
            b'=E8=\r\n'
            b'd p=\r\n'
            b'rot=\r\n'
            b'ec=\r\n'
            b'=E7=\r\n')
        with self.assertRaisesRegex(encoders.EncodingError,
                r'\Amaxlinelen is too small to encode the first byte '
                r'of a line \(at least 1 more byte is needed\)\Z'):
            encoders.encode_qp(b'some str\xedng', maxlinelen=5)
        self.assertEqual(encoders.encode_qp(b'some clich\xe9\r\n',
            maxlinelen=5),
            b'so=\r\n'
            b'me=\r\n'
            b' c=\r\n'
            b'li=\r\n'
            b'ch=\r\n'
            b'=E9\r\n')
        with self.assertRaisesRegex(encoders.EncodingError,
                r'\Amaxlinelen is too small to encode the first byte '
                r'of a line \(at least 1 more byte is needed\)\Z'):
            encoders.encode_qp(b'some clich\xe9\r\n', maxlinelen=4)
        self.assertEqual(encoders.encode_qp(b'\r\n'.join(bytes([i])
            for i in b'hi,bip') + b'\r\n', maxlinelen=3),
            b'\r\n'.join(bytes([i]) for i in b'hi,bip') + b'\r\n')
        self.assertEqual(encoders.encode_qp(b'\r\n'.join(bytes([i])
            for i in b'hi,bip'), maxlinelen=3, protect=False),
            b'\r\n'.join(bytes([i]) for i in b'hi,bip'))
        # the whitespace has to be encoded as =20, thus taking
        # up 5 characters on one line.  that's 2 too more.
        with self.assertRaisesRegex(encoders.EncodingError,
                r'\Amaxlinelen is too small to encode the first byte '
                r'of a line \(at least 2 more bytes are needed\)\Z'
            ):
            encoders.encode_qp(b'h\r\n \r\ni\r\n', maxlinelen=3)

    def test_encode_qp_embed(self):
        # "none" encodes every word
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  \r\n',
            embed='none', protect=False).decode('ascii'),
            '=45=09=68=61=6E=20=E8=92=99=20=20=0D=0A')
        # "printable" embeds line ends and tabs
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  \r\n',
            embed='printable', protect=False).decode('ascii'),
            'E=09han =E8=92=99  =0D=0A')
        # "visible" embeds line ends & white space
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  \r\n',
            embed='visible', protect=False).decode('ascii'),
            'E=09han=20=E8=92=99=20=20=0D=0A')
        # "line" embeds line ends & TRAILING white space
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  \r\n',
            embed='line', protect=False).decode('ascii'),
            'E\than =E8=92=99  =0D=0A')
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  ',
            embed='line', protect=False).decode('ascii'),
            'E\than =E8=92=99 =20')
        # "all" embeds everything: the default :)
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99  \r\n',
            embed='all', protect=False).decode('ascii'),
            'E\than =E8=92=99 =20\r\n')
        self.assertEqual(encoders.encode_qp(b'E\than \xe8\x92\x99',
            embed='all', protect=False).decode('ascii'),
            'E\than =E8=92=99')

    def test_encode_base64(self):
        s1 = b'\xe4\xbb\xa5\xe6\xad\xa3'
        s2 = b'\x45\x74\x68\x61\x6e\x21'
        self.assertEqual(encoders.encode_base64(s1), b'5Lul5q2j')
        self.assertEqual(encoders.encode_base64(s2), b'RXRoYW4h')
        self.assertEqual(encoders.encode_base64(s1, maxlinelen=6),
            b'5Lul\r\n5q2j')
        self.assertEqual(encoders.encode_base64(s2, maxlinelen=5),
            b'RXR\r\noYW\r\n4h')
        self.assertEqual(encoders.encode_base64(s1, maxlinelen=6,
            canonical_linesep=b'\n'), b'5Lul\n5q2j')
        self.assertEqual(encoders.encode_base64(s2, maxlinelen=5,
            canonical_linesep=b'\n'), b'RXR\noYW\n4h')

    def test_encode_verbatim(self):
        self.assertEqual(encoders.encode_verbatim(
            b'i know what you are'), b'i know what you are')
        with self.assertRaises(EncodingError):
            encoders.encode_verbatim(b'i know what you are', maxlinelen=20)
        self.assertEqual(encoders.encode_verbatim(
            b'i know what you ar\r\ne', maxlinelen=20),
            b'i know what you ar\r\ne')
        self.assertEqual(encoders.encode_verbatim(
            b'i know what you ar\r\ne',
                maxlinelen=20, canonical_linesep=b'\n'),
            b'i know what you ar\ne')
        with self.assertRaises(EncodingError):
            encoders.encode_verbatim(b'i know what you ar\ne')

class TestDecoders(unittest.TestCase):
    def test_decode_qp(self):
        self.assertEqual(decoders.decode_qp(b''), b'')
        self.assertEqual(decoders.decode_qp(b'=\r\n'), b'')
        self.assertEqual(decoders.decode_qp(b'=0A'), b'\n')
        self.assertEqual(decoders.decode_qp(b'=0A=\r\n'), b'\n')
        with self.assertRaises(DecodingError):
            decoders.decode_qp(b'\n')
        self.assertEqual(decoders.decode_qp(b'\r\n'), b'\r\n')
        self.assertEqual(decoders.decode_qp(b'espa=F1ol'), b'espa\xf1ol')
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0A'), b'espa\xf1ol\n')
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0D=0A'),
                                                            b'espa\xf1ol\r\n')
        # XXX: see comment above; this output is currently not producible
        # by encode_qp(), but so are many other kinds of QP-encoded text :)
        #
        # in general, the QP-encoded text we produce is a very narrow
        # subset of all valid QP-encoded text.  what makes QP encoding
        # readable to us is, ironically, what prevents it from being a
        # well-defined mapping between the 7bit world and the 8bit world.
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0A\r\n'),
                                                          b'espa\xf1ol\n\r\n')
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0D'), b'espa\xf1ol\r')
        # okay, this is definitely not producible XD
        # (it's just the ^^ tbh)
        self.assertEqual(decoders.decode_qp(b'hell=\r\no, w\r\norld ^^'),
            b'hello, w\r\norld ^^')

        # do not translate us!
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0A',
            canonical_linesep=b'\n'), b'espa\xf1ol\n')
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0D=0A',
            canonical_linesep=b'\n'), b'espa\xf1ol\r\n')
        # but do translate us...
        self.assertEqual(decoders.decode_qp(b'espa=F1ol=0A\n',
            canonical_linesep=b'\n'), b'espa\xf1ol\n\r\n')
        self.assertEqual(decoders.decode_qp(b'hell=\no, w\norld ^^',
            canonical_linesep=b'\n'), b'hello, w\r\norld ^^')

        # be rude to bad input
        with self.assertRaises(DecodingError):
            decoders.decode_qp(b'espa=F1ol=0D\n')

    def test_decode_base64(self):
        s1 = b'\x45\x74\x68\x61\x6e\x21'
        s2 = b'\xe4\xbb\xa5\xe6\xad\xa3'
        self.assertEqual(decoders.decode_base64(b'RXR\r\noYW\r\n4h'), s1)
        self.assertEqual(decoders.decode_base64(b'5Lul\r\n5q2j\r\n'), s2)
        # ths is insanity jus ignore tihs test
        self.assertEqual(decoders.decode_base64(
            b'R\r\nX\r\nR\r\no\r\nY\r\nW\r\n4\r\nh'), s1)
        # invalid base64 alphabet
        with self.assertRaisesRegex(
                decoders.DecodingError,
                r'\Acannot decode chunk of length 4 up to line 3\Z'):
            decoders.decode_base64(b'RXR\r\noYW4\r\n***')
        # misalignment
        with self.assertRaisesRegex(
                DecodingError,
                r'\Atrailing chunk of length 3\Z'):
            decoders.decode_base64(b'RXR\r\noY\r\nW4\r\n\r\n')
        # other EOL in the wild
        with self.assertRaisesRegex(
                DecodingError,
                r"\Abad EOL marker on line 2: b'\\n'\Z"):
            decoders.decode_base64(b'RX\r\nR\noYW4h')
        with self.assertRaisesRegex(
                DecodingError,
                r"\Abad EOL marker on line 2: b'\\n'\Z"):
            decoders.decode_base64(b'RX\r\nR\noYW4h')

    def test_decode_verbatim(self):
        self.assertEqual(decoders.decode_verbatim(
            b'i know what you are'), b'i know what you are')
        self.assertEqual(decoders.decode_verbatim(
            b'i know what you ar\r\ne', maxlinelen=20),
            b'i know what you ar\r\ne')
        self.assertEqual(decoders.decode_verbatim(
            b'i know what you ar\ne',
                maxlinelen=20, canonical_linesep=b'\n'),
            b'i know what you ar\r\ne')
        with self.assertRaises(DecodingError):
            decoders.decode_verbatim(b'i know what you ar\ne')

if __name__ == '__main__':
    unittest.main()
