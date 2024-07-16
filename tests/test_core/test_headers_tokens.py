"""sanity tests - prevents most illegal things from happening"""

# even more test O_O
"""test rfc heder parser"""

from rdks.mail.headers.tokens import (
    Tokens, CRLF, Symbol, AtomText, CommentText,
)
import unittest

class TestBaseClasses(unittest.TestCase):
    def test_closure(self):
        """closure, i.e. conatenation of terminals remain terminals,
        and concatenation of tokens remain tokens.
        """
        # incompatible types may not be joined.
        with self.assertRaises(TypeError):
            AtomText('wah') + CommentText('bwa')

    def test_symbols(self):
        # uh, but what are these?
        self.assertEqual(CRLF.value, '\r\n')
        # why is it okay to join symbols??? uhh...
        # i forgot :D
        self.assertEqual(CRLF + Symbol(''), Symbol('\r\n'))
        self.assertNotEqual(CRLF, Symbol('\r\n'))
        self.assertNotEqual(CRLF, CRLF + Symbol(''))
        self.assertEqual(CRLF, Symbol(name='CRLF'))
        self.assertIs(CRLF, Symbol(name='CRLF'))

    def test_append(self):
        toke = Tokens()
        toke.append(AtomText('wah'))
        toke.append(AtomText('wah'))
        toke.append(CommentText('wah'))
        toke.prepend(CommentText('bwa'))
        toke.prepend(CommentText('bwa'))
        self.assertEqual(toke.value,
            [CommentText('bwabwa'), AtomText('wahwah'), CommentText('wah')])

if __name__ == '__main__':
    unittest.main()
