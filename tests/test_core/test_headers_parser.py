# even more test O_O
"""test rfc heder parser"""

import rdks.mail.headers.parser as parser
import rdks.mail.headers.tokens as tokens
from rdks.mail.headers.tokens import (
    MsgId, IdLeft, IdRight,
    DotAtomText as DotAText, AtomText as AText,
    DomainText as DText, DomainLiteral,
    LANGLE as LESS, RANGLE as MORE, PERIOD as DOT,
    LBRACK as LSQ, RBRACK as RSQ, ATSIGN as AT,
)
import unittest

class TestPartials(unittest.TestCase):
    def test_domain_literal(self):
        token, value = parser.get_domain_literal('[] rems')
        self.assertEqual(token, DomainLiteral([LSQ, RSQ]))
        self.assertEqual(str(token), "[]")
        self.assertEqual(value, " rems")
        token, value = parser.get_domain_literal('[rapidcow.org]')
        self.assertEqual(token, DomainLiteral(
            [LSQ, DText('rapidcow.org'), RSQ]))
        self.assertEqual(str(token), "[rapidcow.org]")
        self.assertEqual(value, "")

class TestParser(unittest.TestCase):
    def test_message_id(self):
        self.maxDiff = 1000
        self.assertEqual(
            parser.parse_message_id('<pawm.knee@yes.example.com>'),
            [
              MsgId([
                LESS,
                  IdLeft([
                    DotAText([
                      AText('pawm'), DOT, AText('knee')
                    ])
                  ]),
                AT,
                  IdRight([
                    DotAText([
                      AText('yes'), DOT, AText('example'), DOT, AText('com')
                    ])
                  ]),
                MORE
              ])
            ]
        )

if __name__ == '__main__':
    unittest.main()
