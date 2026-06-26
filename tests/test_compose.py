try:
    import rdks.list
    has_rplist = True
except ImportError:
    has_rplist = False

if has_rplist:
    import rdks.mail.compose as compose
import os
import tempfile
from textwrap import dedent
import unittest

def compose(i, o, **files):
    with tempfile.TemporaryDirectory() as r:
        for k, v in files.items():
            with open(os.path.join(r, k), 'wb') as fp:
                fp.write(v)
        cmd = ['-C', r,
               '-o', os.path.join(r, o),
               '--', os.path.join(r, i)]
        rdks.mail.compose.main(cmd)
        with open(os.path.join(r, o), 'rb') as fp:
            return fp.read()

@unittest.skipIf(not has_rplist, 'missing rdks.list')
class TestInlineData(unittest.TestCase):
    def test_inline_toplevel(self):
        """make sure interpret_input is ON because
        for some reason it wasn't"""
        message = compose('message', 'output', message=(
            b"options\n"
            b"  linesep LF\n"
            b"headers << @\n"
            b"  @ From: Ethan Meng <ethan69@copium.edu>\n"
            b"  @ To: nick 2sbox.com <nick@2sbox.com>\n"
            b"content\n"
            b"  text/plain << |\n"
            b"    | Yo get dunked on\n"
            b"    | lolol\n"
            b"    |\n"
            b"    with charset us-ascii\n"
            b"    of encoding 7bit\n"
            b"    of description Sorry Nick. I was bored. :)))\n"
        )).decode('ascii')

        self.assertEqual(message,
            "From: Ethan Meng <ethan69@copium.edu>\n"
            "To: nick 2sbox.com <nick@2sbox.com>\n"
            "MIME-Version: 1.0\n"
            'Content-Type: text/plain; charset="us-ascii"\n'
            "Content-Transfer-Encoding: 7bit\n"
            "Content-Description: Sorry Nick. I was bored. :)))\n"
            "\n"
            "Yo get dunked on\n"
            "lolol\n"
        )

    def test_bare_inline_marker(self):
        """a bare "<<" should be tokenized as [b'<<']."""
        reed = rdks.mail.compose.ConfigReader('<memory>', 'where-ever', [
            b"this <<\n",
            b"  is something\n",
            b"that << \n",
            b"  too is something\n",
            b"  \n",
        ])
        pear_one = next(reed)
        self.assertEqual(pear_one.input_root, 'where-ever')
        self.assertEqual(pear_one.input_file, '<memory>')
        self.assertEqual(pear_one.data, b"is something")

        pear_two = next(reed)
        self.assertEqual(pear_two.input_root, 'where-ever')
        self.assertEqual(pear_two.input_file, '<memory>')
        self.assertEqual(pear_two.data, b"too is something\n")

        with self.assertRaises(StopIteration):
            next(reed)

    def test_inline_termination(self):
        """test that "<<" actually ends. this is only a problem
        when we have a prefix."""
        reed = rdks.mail.compose.ConfigReader('<memory>', 'where-ever', [
            b"niche-list << foo bar\n",
            b"  foo bar this is\n",
            b"  foo bar  a list\n",
            b"  foo bar that i\n",
            b"  foo baractually\n",
            b"  foo bar like\n",
            b"  foo bar-unlike\n",
            b"  foo baz.\n",
            b"  or rainbows.\n",
            b"weird-list << foo bar\n",
            b"foo bar every line\n",
            b"foo bar must be\n",
            b"foo barexactly\n",
            b'foo bar    "FOOBAR"\n',
            b"foo bar-and not\n",
            b"foo bar \n",
            b"foo baz.\n",
            b"(though foo baz should probably not be eaten)\n",
        ])

        pair_niche = next(reed)
        self.assertEqual(pair_niche.key, b'niche-list')
        self.assertEqual(pair_niche.data.decode('ascii'),
            "this is\n"
            " a list\n"
            "that i\n"
            "actually\n"
            "like\n"
            "-unlike"
        )
        self.assertEqual(pair_niche.rest, [b'foo baz.\n', b'or rainbows.'])

        pair_weird = next(reed)
        self.assertEqual(pair_weird.key, b'weird-list')
        self.assertEqual(pair_weird.data.decode('ascii'),
            "every line\n"
            "must be\n"
            "exactly\n"
            '   "FOOBAR"\n'
            "-and not\n"
        )

        self.assertEqual(next(reed), tuple(b'foo baz.'.split(b' ', 1)))
        self.assertEqual(next(reed), tuple(
            b'(though foo baz should probably not be eaten)'
            .split(b' ', 1)))

        with self.assertRaises(StopIteration):
            next(reed)

# we've seen IN-line data...
# why not add some OUT-line data? ;)
@unittest.skipIf(not has_rplist, 'missing rdks.list')
class TestOutlineData(unittest.TestCase):
    def test_header_inputs(self):
        message = compose('message', 'output',
            now=b'Mon, 01 Jul 2024 12:55:37 +0800',
            real_recip=b'nick 2sbox.com <nick@2sbox.com>',
            test_recip=b'<test@rapidcow.org>',
            body=b'yo are you frfr\n',
            message=(
                b"options\n"
                b"  linesep LF\n"
                b"headers\n"
                b"  Date: < now\n"
                b"  From: Ethan Meng <ethan69@copium.edu>\n"
                b"  To: < test_recip\n"
                b"content\n"
                b"  text/plain < body\n"
                b"    with charset utf-8\n"
                b"    of encoding 7bit\n"
            ))

        self.assertEqual(message,
            b"Date: Mon, 01 Jul 2024 12:55:37 +0800\n"
            b"From: Ethan Meng <ethan69@copium.edu>\n"
            b"To: <test@rapidcow.org>\n"
            b"MIME-Version: 1.0\n"
            b'Content-Type: text/plain; charset="utf-8"\n'
            b"Content-Transfer-Encoding: 7bit\n"
            b"\n"
            b"yo are you frfr\n"
        )

@unittest.skipIf(not has_rplist, 'missing rdks.list')
class TestHeaders(unittest.TestCase):
    # for simplicity, we just ask for each msg-id to appear on
    # a line of its own. no MIME encoded words or any of that...
    #
    # these RFC822 headers use msg-id:
    #   * Message-ID, In-Reply-To, References
    #   * Resent-Message-ID (not testing this yet)
    #
    # see:
    #   * https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4
    #   * https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.6
    #
    # XXX: skipped because we are not re-folding anything
    #      as a quick-and-dirty temporary fix
    #      (i hope it is just temporary, even though knowing
    #       that it will not be....)
    @unittest.skip
    def test_rfc_msg_id_headers(self):
        message = compose('message', 'output',
            message=dedent(
            """\
            headers
              From: Ethan Meng <ethan69@copium.edu>
              To: My teacher <my.teacher@copium.edu>
              Message-ID:
                <172060623043.631.12133522306633788928.copium.edu@RCs-MacBook-Pro.local>
              In-Reply-To:
                <372301fd64f34cbe875a37822aa9c05b@MN2PR06MB6734.namprd06.prod.outlook.com>
              References:
                <LV3PR06MB9453D0126104E98512B96FAEA0DD2@LV3PR06MB9453.namprd06.prod.outlook.com>
                <372301fd64f34cbe875a37822aa9c05b@MN2PR06MB6734.namprd06.prod.outlook.com>
            content
              text/plain << |
                | poison
                of encoding 7bit
            """).encode('ascii'))

        # note the lack of spaces after colons: this is possible
        # thanks to the new header re-folder! :D
        self.maxDiff = None
        self.assertEqual(message.decode('ascii'), dedent(
            """\
            From: Ethan Meng <ethan69@copium.edu>
            To: My teacher <my.teacher@copium.edu>
            Message-ID:
             <172060623043.631.12133522306633788928.copium.edu@RCs-MacBook-Pro.local>
            In-Reply-To:
             <372301fd64f34cbe875a37822aa9c05b@MN2PR06MB6734.namprd06.prod.outlook.com>
            References:
             <LV3PR06MB9453D0126104E98512B96FAEA0DD2@LV3PR06MB9453.namprd06.prod.outlook.com>
             <372301fd64f34cbe875a37822aa9c05b@MN2PR06MB6734.namprd06.prod.outlook.com>
            MIME-Version: 1.0
            Content-Type: text/plain
            Content-Transfer-Encoding: 7bit

            poison""").replace('\n', '\r\n'))

# TODO:
@unittest.skipIf(not has_rplist, 'missing rdks.list')
class TestContentBody(unittest.TestCase):
    def test_verbatim_encoding(self):
        """maxlinelen (7bit)"""

    def test_qp_encoding(self):
        """maxlinelen, wrap, embed, protect"""
        message = compose('message', 'output',
            message=(
                b"options\n"
                b"  linesep CRLF\n"
                b"headers\n"
                b"content\n"
                b"  text/plain << |\n"
                b"    | hello\n"
                b"    with charset us-ascii\n"
                b"    of encoding quoted-printable\n"
            ))
        self.assertEqual(message.decode('ascii'),
            'MIME-Version: 1.0\r\n'
            'Content-Type: text/plain; charset="us-ascii"\r\n'
            'Content-Transfer-Encoding: quoted-printable\r\n'
            '\r\n'
            'hello=\r\n')

        self.maxDiff = 800
        message = compose('message', 'output',
            message=(
                b"options\n"
                b"  linesep CRLF\n"
                b"headers\n"
                b"content\n"
                b"  multipart/alternative\n"
                # i cant spel my name :c
                b"    with boundary --EtahN==mmovo\n"
                b"    including\n"
                b"      text/plain << |\n"
                b"        | hello\n"
                b"        with charset us-ascii\n"
                b"        of encoding quoted-printable\n"
                b"      text/html << |\n"
                b"        | <p>hello</p>\n"
                b"        |\n"
                b"        with charset iso-8859-1\n"
                b"        of encoding quoted-printable\n"
            ))
        self.assertEqual(message.decode('ascii'),
            'MIME-Version: 1.0\r\n'
            'Content-Type: multipart/alternative; boundary="--EtahN==mmovo"'
            '\r\n\r\n'
            '----EtahN==mmovo\r\n'
            'Content-Type: text/plain; charset="us-ascii"\r\n'
            'Content-Transfer-Encoding: quoted-printable\r\n\r\n'
            'hello'
            '\r\n----EtahN==mmovo\r\n'
            'Content-Type: text/html; charset="iso-8859-1"\r\n'
            'Content-Transfer-Encoding: quoted-printable\r\n\r\n'
            '<p>hello</p>=0A'
            '\r\n----EtahN==mmovo--\r\n')

    def test_base64_encoding(self):
        """maxlinelen, and idk"""
        s1 = b'\x45\x74\x68\x61\x6e\x21'
        s2 = b'\xe4\xbb\xa5\xe6\xad\xa3'
        message = compose('message', 'output',
            ethan=s1,
            message=(
                b"options\n"
                b"  linesep CRLF\n"
                b"headers\n"
                b"content\n"
                b"  text/plain < ethan\n"
                b"    with charset us-ascii\n"
                b"    of encoding base64\n"
            ))

        self.assertEqual(message.decode('ascii'),
            'MIME-Version: 1.0\r\n'
            'Content-Type: text/plain; charset="us-ascii"\r\n'
            'Content-Transfer-Encoding: base64\r\n\r\n'
            'RXRoYW4h'
            '\r\n')

        message = compose('message', 'output',
            ethan=s2,
            message=(
                b"options\n"
                b"  linesep CRLF\n"
                b"headers\n"
                b"content\n"
                b"  multipart/related\n"
                b"    with boundary ==yiPPEEThan==\n"
                b"    including\n"
                b"      text/plain < ethan\n"
                b"        with charset utf-8\n"
                b"        of encoding base64\n"
                b"          where chomp = no\n"
                b"      application/octet-stream < ethan\n"
                b"        of encoding base64\n"
            ))

        self.assertEqual(message.decode('ascii'),
            'MIME-Version: 1.0\r\n'
            'Content-Type: multipart/related; boundary="==yiPPEEThan=="'
            '\r\n\r\n'
            '--==yiPPEEThan==\r\n'
            'Content-Type: text/plain; charset="utf-8"\r\n'
            'Content-Transfer-Encoding: base64\r\n\r\n'
            '5Lul5q2j\r\n'
            '\r\n--==yiPPEEThan==\r\n'
            'Content-Type: application/octet-stream\r\n'
            'Content-Transfer-Encoding: base64\r\n\r\n'
            '5Lul5q2j'
            '\r\n--==yiPPEEThan==--\r\n')

if __name__ == '__main__':
    unittest.main()
