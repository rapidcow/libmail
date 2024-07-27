""" *noises of me being salty bc my issue not approved* """
from textwrap import dedent
import email.message
import unittest

from rdks.mail.contrib.policy import SMTP
from rdks.mail.content import treol

# subclass test imports
from rdks.mail.contrib.contentmanager import ContentManager
import binascii, re

def strictly_chomp(b):
    assert b.endswith('\r\n')
    return b[:-2]

def canonicalize(s):
    return treol(s.encode('utf-8')).decode('utf-8')


# i just realized we don't need to implement encoding if we
# never call set_content(cte=<name>)...
# that said, uuencode sounds like a weird breed :/
# https://groups.google.com/g/comp.answers/c/MREwyQLC4gg/m/eEPSsyH7trgJ
# https://retrocomputing.stackexchange.com/a/3027
class MyContentManager(ContentManager):
    def decode_x_uuencode(self, message, body, *, maxlinelen, linesep):
        # XXX: hack (obviously)
        return binascii.a2b_uu(
          re.sub(b'(?mi)^[ `]$', b'',
            re.sub(b'(?mi)^end$', b'',
              re.sub(b'(?mi)^begin [0-7]{3} .*$', b'',
                treol(body, b'\n')
              ),
            ),
          ).replace(b'\n', b'')
        )

class TestContentManager(unittest.TestCase):
    """subclassing test"""

    def test_new_decoder(self):
        # from: https://github.com/python/cpython/blob/v3.12.4/Lib/test/test_email/test_email.py#L752-L764
        # (P.S. do not touch this typo; i find this way too funny)
        my_police = SMTP.clone(content_manager=MyContentManager())
        msg = email.message.EmailMessage(policy=my_police)
        msg['content-type'] = 'text/plain; charset="latin-1"'
        msg['content-transfer-encoding'] = 'x-uuencode'
        msg.set_payload("begin 666 -\n)9F]OYI:'8F%R\n \nend\n")
        self.assertEqual(msg.get_content(), 'foo\xe6\x96\x87bar')


class TestSetContent(unittest.TestCase):
    def test_string_eol(self):
        # my dream :,)
        # from: https://github.com/python/cpython/blob/v3.12.4/Lib/test/test_email/test_contentmanager.py#L306-L317
        m = email.message.MIMEPart(policy=SMTP)
        m.set_content('', fixeol=False)
        self.assertEqual(str(m), canonicalize(dedent(
            """\
            Content-Type: text/plain; charset="utf-8"

            """)))
        self.assertEqual(m.get_payload(decode=True).decode('utf-8'), '')
        self.assertEqual(m.get_content(), '')

        # from: https://github.com/python/cpython/blob/v3.12.4/Lib/test/test_email/test_contentmanager.py#L499-L526
        m = email.message.EmailMessage(policy=SMTP)
        m['Subject'] = "Forwarded message"
        content = email.message.EmailMessage(policy=SMTP)
        content['To'] = 'python@vivarium.org'
        content['From'] = 'police@monty.org'
        content['Subject'] = "get back in your box"
        content.set_content("Or face the comfy chair.", fixeol=False)
        m.set_content(content)
        self.assertEqual(str(m), strictly_chomp(canonicalize(dedent(
            """\
            Subject: Forwarded message
            MIME-Version: 1.0
            Content-Type: message/rfc822

            To: python@vivarium.org
            From: police@monty.org
            Subject: get back in your box
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"

            Or face the comfy chair.
            """))))
        payload = m.get_payload(0)
        self.assertEqual(str(payload), str(content))
        self.assertEqual(str(m.get_content()), str(content))

    def test_filename(self):
        # from: https://github.com/python/cpython/blob/v3.12.4/Lib/test/test_email/test_contentmanager.py#L766-L777
        m = email.message.EmailMessage(policy=SMTP)
        m.set_content('foo', filename='ábárî.txt', cte='7bit')
        self.assertEqual(bytes(m).decode('ascii'),
            canonicalize(dedent(
            """\
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: 7bit
            Content-Disposition: attachment; filename*=utf-8''%C3%A1b%C3%A1r%C3%AE.txt

            foo
            """)))

    def test_even_crazier_disposition_parameters(self):
        m = email.message.EmailMessage(policy=SMTP)
        m.set_content('YIPPEE\n', size='6673', cte='7bit',
                      creation_date='Fri, 05 Jul 2024 02:42:56 +0800',
                      modification_date='Sun, 07 Jul 2024 11:09:50 +0800')
        self.assertEqual(str(m),
            canonicalize(dedent(
            """\
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: 7bit
            Content-Disposition: inline; creation-date="Fri, 05 Jul 2024 02:42:56 +0800";
             modification-date="Sun, 07 Jul 2024 11:09:50 +0800"; size="6673"

            YIPPEE
            """)))


class TestGetContent(unittest.TestCase):
    def test_get_base64(self):
        # from: https://github.com/python/cpython/blob/v3.12.4/Lib/test/test_email/test_contentmanager.py#L182-L189
        m = email.message_from_string(canonicalize(dedent(
            """\
            Content-Type: text/plain; charset="utf8"
            Content-Transfer-Encoding: base64

            QmFzw6xjIHTDq3h0Lgo=
            """)), policy=SMTP)
        self.assertEqual(m.policy.linesep, '\r\n')
        # augh this is tough .... feed parser seem to set
        # the payload without any EOL canonicalization :(
        # (feed parser does too little translation,
        #  while generator does too much, what.... X,c)
        # behold the most magical python code you will ever see:
        s = m.get_payload(decode=False).encode('ascii')
        m.set_payload(s.replace(b'\r\n', b'\n').decode('ascii'))
        self.assertEqual(m.get_content(), "Bas\xecc t\xebxt.\n")


if __name__ == '__main__':
    unittest.main()
