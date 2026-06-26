"""RFC2047 (MIME III) encoded words tests"""

import unittest

from rdks.mail.headers.words import encode_word

class TestEncodeWord(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            encode_word('this is some text', 'Q').decode('iso-8859-1'),
            '=?ISO-8859-1?Q?this_is_some_text?=')
        self.assertEqual(
            encode_word('If you can read this yo', 'B',
                        'US-ASCII').decode('iso-8859-1'),
            '=?US-ASCII?B?SWYgeW91IGNhbiByZWFkIHRoaXMgeW8=?=')
        self.assertEqual(
            encode_word('u understand the example.', 'B',
                        'UTF-8', 'EN').decode('iso-8859-1'),
            '=?UTF-8*EN?B?dSB1bmRlcnN0YW5kIHRoZSBleGFtcGxlLg==?=')
