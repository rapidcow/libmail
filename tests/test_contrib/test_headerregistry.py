from textwrap import dedent
import email.message
import unittest

from rdks.mail.contrib.policy import SMTP
from rdks.mail.content import treol
from rdks.mail.headers.format import dumps


class TestMessageIdFields(unittest.TestCase):
    def test_message_id(self):
        e1 = email.message.EmailMessage(SMTP)
        e1['Message-ID'] = '<AHHH.1am.turning@[into-pomni.tADc]>'
        self.assertEqual(e1['Message-ID'],
                         '<AHHH.1am.turning@[into-pomni.tADc]>')
        self.assertEqual(str(e1),
            'Message-ID: <AHHH.1am.turning@[into-pomni.tADc]>\r\n\r\n')

    def test_invalid_message_id(self):
        # this microsoft bullcrap makes me want to commit die :))))
        badid = ('<[629adcc586b744468a408af8a5f94923-JFBVALKQOJXWILKCJQZFA7C'
                 'NNFRXE33TN5THIQLDMNXXK3TUKJSWG33WMVZHSU3FOJ3GSY3FPRGWC4TTJ'
                 'VQWS3DFOJ6EK6DPKNWXI4A=@microsoft.com]>')
        e2 = email.message_from_string('Message-ID: %s\n' % badid,
                                       policy=SMTP)
        self.assertEqual(str(e2['Message-ID'].tokens), badid)
        msgid = e2['Message-ID'].tokens.select('MsgId')
        self.assertEqual(str(msgid.select('IdLeft')),
            badid[badid.index('<') + 1 : badid.index('@')])
        self.assertEqual(str(msgid.select('IdRight')),
            badid[badid.index('@') + 1 : badid.index('>')])

        # note that feed parser would drop leading space,
        # so the first test would fail
        for badid in ['  (um...) <no.at.sign.to.be.found>',
                      '<too <many <langles']:
            e3 = email.message.EmailMessage(policy=SMTP)
            e3['Message-ID'] = badid
            self.assertEqual(str(e3['Message-ID'].tokens), badid)


if __name__ == '__main__':
    unittest.main()
