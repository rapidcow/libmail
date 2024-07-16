
:mod:`.headers.format` --- presentation and folding of parse trees
------------------------------------------------------------------

.. module:: rdks.mail.headers.format
   :synopsis: dump wrap (will NOT be documented) and pretty printing

.. function:: dump(tree, indent=2, **kwds)

   Print a parse tree (a :class:`list` of tokens) or
   a lone :class:`Token` in beautiful indented form.

   Okay I am exaggerating but uhhh here's an example:

   .. testsetup::

      from rdks.mail.headers.format import dump

   .. doctest::

      >>> from rdks.mail.headers.parser import parse_message_id
      >>> tokens = parse_message_id(
      ...   '\t\r\n  <do-not-call@'
      ...   'amo.gus.example.com> '
      ...   '(at 3am !!! (O_O))')
      >>> dump(tokens)
      [
        CommentFoldingWhiteSpace([
          FoldingWhiteSpace([
            WhiteSpace('\t'),
            CRLF,
            WhiteSpace('  ')
          ])
        ]),
        MsgId([
          LANGLE,
          IdLeft([
            DotAtomText([
              AtomText('do-not-call')
            ])
          ]),
          ATSIGN,
          IdRight([
            DotAtomText([
              AtomText('amo'),
              PERIOD,
              AtomText('gus'),
              PERIOD,
              AtomText('example'),
              PERIOD,
              AtomText('com')
            ])
          ]),
          RANGLE
        ]),
        CommentFoldingWhiteSpace([
          FoldingWhiteSpace([
            WhiteSpace(' ')
          ]),
          Comment([
            LPAREN,
            CommentText('at'),
            FoldingWhiteSpace([
              WhiteSpace(' ')
            ]),
            CommentText('3am'),
            FoldingWhiteSpace([
              WhiteSpace(' ')
            ]),
            CommentText('!!!'),
            FoldingWhiteSpace([
              WhiteSpace(' ')
            ]),
            Comment([
              LPAREN,
              CommentText('O_O'),
              RPAREN
            ]),
            RPAREN
          ])
        ])
      ]

   (*kwds* are passed to :func:`print` but you shouldn't really need that)

If you want the string version :meth:`dumps` helps

.. function:: dumps(tree, indent=2)

   Why does this look so much like :func:`ast.dump`????
   don't ask me :/
