import rdks.mail.compose
import os
import tempfile
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

class TestInlineData(unittest.TestCase):
    def test_inline_toplevel(self):
        """make sure interpret_input is ON because
        for some reason it wasn't"""
        message = compose('message', 'output', message=(
            b"options\n"
            b"  linesep LF\n"
            b"headers << @\n"
            b"  @ From: Ethan Meng <ethan@yizz.me>\n"
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
            "From: Ethan Meng <ethan@yizz.me>\n"
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
class TestOutlineData(unittest.TestCase):
    def test_header_inputs(self):
        message = compose('message', 'output',
            now=b'Mon, 01 Jul 2024 12:55:37 +0800',
            real_recip=b'nick 2sbox.com <nick@2sbox.com>',
            test_recip=b'<eyzmeng@gmail.com>',
            body=b'yo are you frfr\n',
            message=(
                b"options\n"
                b"  linesep LF\n"
                b"headers\n"
                b"  Date: < now\n"
                b"  From: Ethan Meng <ethan@yizz.me>\n"
                b"  To: < test_recip\n"
                b"content\n"
                b"  text/plain < body\n"
                b"    with charset utf-8\n"
                b"    of encoding 7bit\n"
            ))

        self.assertEqual(message,
            b"Date: Mon, 01 Jul 2024 12:55:37 +0800\n"
            b"From: Ethan Meng <ethan@yizz.me>\n"
            b"To: <eyzmeng@gmail.com>\n"
            b"MIME-Version: 1.0\n"
            b'Content-Type: text/plain; charset="utf-8"\n'
            b"Content-Transfer-Encoding: 7bit\n"
            b"\n"
            b"yo are you frfr\n"
        )

if __name__ == '__main__':
    unittest.main()
