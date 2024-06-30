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
            "Content-Type: text/plain\n"
            "Content-Transfer-Encoding: 7bit\n"
            "Content-Description: Sorry Nick. I was bored. :)))\n"
            "\n"
            "Yo get dunked on\n"
            "lolol\n"
        )


if __name__ == '__main__':
    unittest.main()
