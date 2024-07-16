
:mod:`.headers.parser` --- RFC 5322 compliant parser
----------------------------------------------------

.. module:: rdks.mail.headers.parser
   :synopsis: just a message id parser now lol

Exception
^^^^^^^^^

.. exception:: ParserError

   For when any one of the following fellas goes wrong.
   Subclass of :exc:`ValueError`.

Header parsers
^^^^^^^^^^^^^^

These are special in that they return a list of tokens
instead of a single token.

.. function:: parse_message_id(value)

   Parse an RFC 5322 compliant Message-ID / Resent-Message-ID field.
   This ensures one and exactly one :class:`.MsgId` token is present.

.. function:: parse_references(value)

   Parse an RFC 5322 compliant In-Reply-To / References field.
   This ensures one and exactly one :class:`.MsgId` token is present.

.. function:: parse_message_ids(value, minimum=0, maximum=0)

   General form of the above two parsers, where a *minimum* and/or
   a *maximum* number of :class:`.MsgId` tokens may be imposed.
   Either parameter is unlimited by default.


Token parsers
^^^^^^^^^^^^^

All token parsers greedily parse what they can, then spits out a
token and a value where the next token parser can pick up from.
Refer to each individual token's documentation for the formal
grammar.

.. function:: get_fws(value)

   Parse a :class:`.FoldingWhiteSpace` token.

.. function:: get_comment(value)

   Parse a :class:`.Comment` token.

.. function:: get_cfws(value)

   Parse a :class:`.CommentFoldingWhiteSpace` token.

.. function:: get_domain_literal(value)

   Parse a :class:`.DomainLiteral` token.  Note that this does not take
   care of any surrounding CFWS.

.. function:: get_msg_id(value)

   Parse a :class:`.MsgId` token.  Note that this does not take care of
   any surrounding CFWS.

