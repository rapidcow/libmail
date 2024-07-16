
:mod:`.headers.tokens` --- Parse tree representation
----------------------------------------------------

.. module:: rdks.mail.headers.tokens
   :synopsis: i think this is somewhat better than python's one-file monstrosity

This might be my least favorite or most favorite module depending on
how everything goes.... :,]


Base classes
^^^^^^^^^^^^

.. class:: Token

   Abstract base class of tokens.  Subclasses will have their
   names accessible through ``type_name``:

   .. testsetup::

      from rdks.mail.headers.tokens import Symbol, CRLF, Text

   .. doctest::

      >>> Symbol.type_name
      'Symbol'
      >>> CRLF.type_name
      'Symbol'

   I did this so that it'd feel less hacky than ``__name__``.... :)
   Good thing ``__init_subclass__`` makes it easy to set attributes
   this way!

   Many of these methods are, well, abstract.  But you always want
   to instantiate one of the two concrete subclasses first, so...
   might as well document them here.

   .. method:: __new__(value=None, *, name=None)

      Create an unnamed token, a named token, or retrieve an already
      created named token.  I'm a bit tired, so here is an example
      of the last one:

      .. doctest::

         >>> Symbol(name='CRLF') is CRLF
         True

      Each subclass would have its own registry, mapping names
      of named tokens to the :class:`Token` object.  In this case,
      :class:`Symbol`'s registry maps ``'CRLF'`` to :data:`CRLF`.


   .. property:: name

      The name of the token, if there is one.
      Otherwise an :exc:`AttributeError` is thrown.
      Only global constants should be declared as named tokens.

   .. property:: value

      The value of the token.  For :class:`Terminal`, this is a
      :class:`str`.  For :class:`Tokens`, this is a :class:`list`
      copy of the internal tokens.

   .. method:: __repr__()

      Return ``ClassName(name=name)`` if :attr:`name` exists, else
      ``ClassName(value)``.  For instance, the representation
      of :data:`CRLF` is, simply, CRLF, whereas most tokens simply have
      the latter representation:

      .. doctest::

         >>> CRLF.name
         'CRLF'
         >>> repr(CRLF)
         "Symbol(name='CRLF')"
         >>> hello = Text('hello')
         >>> hello.name
         Traceback (most recent call last):
           ...
         AttributeError: 'Text' object has no attribute '...'
         >>> repr(hello)
         "Text('hello')"

   .. method:: __str__()

      Return either just :attr:`value` if the token is a :class:`Terminal`
      or the string concatenation of all the child tokens, recursively,
      if it is :class:`Tokens`.  (Is? Are? Ehhh... I regret naming the
      class that way... =n=)

      This is probably the single coolest thing about parse trees,
      because ``str(tree)`` gives you the original string!

   .. method:: __eq__(other)

      Equality is tricky, but basically:

      *  Named tokens are only equal to named tokens of the same type
         **if their names match**.  (And since named tokens can only
         be created once, this is essentially ``is``.)
      *  Other tokens are only equal to tokens **if their types
         and values match**.

      Any other case is handled by the built-in :meth:`object.__eq__`.

   The point of defining :meth:`__eq__` this way is to make ``==``
   useful for checking parse tree equivalence.  (I need this for unit
   tests, so you don't get to talk over me :)

   .. method:: __add__(other)

      *  For :class:`Terminal`: join with the other's string value
         if *other* has the same type, *or* one of them is a :class:`str`.
         I don't have a good way of determining the type otherwise.

      *  For :class:`Tokens`: combine with the other's child tokens
         if *other* has same type.  There is no "or" this time because
         I think using ``+`` for any other case is too weird for me to
         imagine.

   .. method:: __iadd__(other)

      Just a note that if you write ``token += other``
      for :class:`Terminal`, it is quite literally
      ``token = token + other``.  :class:`Terminal` is not mutable
      (not hashable though cuz idk why would you, but anyway),
      and thus no in-place operation is done.

      :meth:`__iadd__` *is* an in-place operation though for
      :class:`Tokens`.  Namely, :meth:`__iadd__` works for any
      iterable of :class:`Token` instances.  Should you count on it?
      Maybe, maybe not.... (there's :meth:`Tokens.append` though!)

   .. method:: __bool__()

      Probably should be true all the time?  I'm not sure
      what you would use this for :/

   .. method:: __iter__()

      Okay.  This is where we usually call ``children()`` for
      uh... children nodes.  But well we have this instead, so
      that we can have the super confusing ``for token in self``
      syntax.

      Jokes aside though, whenever you see ``for ... in token``,
      it just means to loop over all child tokens, and this method
      is doing the work.  Note that :class:`Terminal` instances
      do not have any child node, so ``for ... in terminal``
      would never iterate.  This is one big difference from
      simply running ``for ... in token.value``, which would
      iterate over each character in any given :class:`Terminal`.

   .. method:: __len__()

      This goes with :meth:`__iter__`.  It tells you how many
      iterations you will get, i.e. number of child tokens.

   .. method:: __getitem__(index)
               __setitem__(index, value)
               __delitem__(index)

      Implement ``token[i]`` stuff.  This is always an
      :exc:`IndexError` when done on a :class:`Terminal`, though
      they should work like an ordinary list for :class:`Tokens`.

   .. method:: __contains__(value)

      ``value in token`` returns whether *value* is equal to or
      identical to (``is``) *token*.

   Here are some cool basic filtering methods!

   .. method:: select(criteria, index=0)
               filter(criteria)

      These kind of go hand in hand: :meth:`select` returns the
      first match (offset by *index*), :meth:`filter` returns
      a copy of the current token with containing solely of
      the matching tokens.

      *criteria* is the type name of the kind of token to filter.
      It is searched against each token's class's MRO, and
      any base class encountered along the way with a matching
      *type_name* is a match.  This means that, say,
      ``WhiteSpaceToken`` would select all instances of
      :class:`WhiteSpaceToken`, as well as those of any subclass.

      A "``not``" followed by a space is used to negate *criteria*,
      considering only the failed matches.

.. class:: Terminal(value=None, *, name=None)

   **Base class**: :class:`Token`

   An additional constraint to the base class is that
   *value* must be *str*.

.. class:: Tokens

   **Base class**: :class:`Token`

   .. method:: __new__(value)

      Similarly, due to most Python objects being iterables,
      this constructor requires that *value* be a :class:`list`.

   .. method:: append(other)
               prepend(other)

      Append or prepend a token --- prefer this to :meth:`Token.__iadd__`!

.. class:: Text

   **Base class**: :class:`Terminal`

   Base class for general terminals.

.. class:: Symbol

   **Base class**: :class:`Terminal`

   Base class for special terminals.


Constants
^^^^^^^^^

.. data:: CRLF

   Defined as ``Symbol("\r\n")``.  This special symbol may
   also be used to represent a line break in general.

.. data:: SPACE

   Defined as ``Symbol(" ")``.  This special symbol may
   also be used to represent a space character compressed
   from a :class:`WhiteSpaceToken`.

.. data:: HTAB

   Defined as ``Symbol("\t")``.

.. data:: COLON

   Defined as ``Symbol(":")``.

.. data:: SEMICOLON

   Defined as ``Symbol(";")``.

.. data:: ATSIGN

   Defined as ``Symbol("@")``.

.. data:: BSLASH

   Defined as ``Symbol("\\")``.  BSLASH is short for backslash.

.. data:: COMMA

   Defined as ``Symbol(",")``.

.. data:: DQUOTE

   Defined as ``Symbol('"')``.  DQUOTE is short for double quote.

.. data:: PERIOD

   Defined as ``Symbol(".")``.  This is also often called a dot.

.. data:: LPAREN

   Defined as ``Symbol("(")``.  LPAREN is short for left parenthesis.

.. data:: RPAREN

   Defined as ``Symbol(")")``.  RPAREN is short for right parenthesis.

.. data:: LANGLE

   Defined as ``Symbol("<")``.  LANGLE is short for left angle bracket.

.. data:: RANGLE

   Defined as ``Symbol(">")``.  RANGLE is short for right angle bracket.

.. data:: LBRACK

   Defined as ``Symbol("[")``.  LBRACK is short for left (square) bracket.

.. data:: RBRACK

   Defined as ``Symbol("]")``.  RBRACK is short for right (square) bracket.


Character sets
^^^^^^^^^^^^^^

Symbols *were* supposed to be substitutable for strings,
so some of these that were defined in terms of those were,
equivalently, sets of strings.  Eventually I decided that
inheriting from :class:`str` feels like to much work to
document what should and shouldn't be used, so whenever a
symbol is used, it's used to technically indicate its
string *value*, i.e. ``SPACE.value`` instead of ``SPACE``.

.. data:: WHITESPACE

   Defined as the set containing :data:`SPACE` and :data:`HTAB`.
   RFC refers to this as WSP.

.. data:: VISIBLE

   Defined as the set containing all visible ASCII characters
   excluding whitespace, i.e. ``!`` (0x21, the exclamation point)
   through ``~`` (0x7E, the tilde).  RFC refers to this as VCHAR
   for "visible character".

.. data:: SPECIALS

   Defined as the set containing:
   :data:`LPAREN`, :data:`RPAREN`,
   :data:`LANGLE`, :data:`RANGLE`,
   :data:`LBRACK`, :data:`RBRACK`,
   :data:`COLON`, :data:`SEMICOLON`,
   :data:`ATSIGN`, :data:`BSLASH`,
   :data:`COMMA`, :data:`DOT`, and
   :data:`DQUOTE`, according to the following rule in
   `RFC 5322, Section 3.2.3
   <https://datatracker.ietf.org/doc/html/rfc5322#section-3.2.3>`_:

   .. code-block:: text

      specials        =   "(" / ")" /        ; Special characters that do
                          "<" / ">" /        ;  not appear in atext
                          "[" / "]" /
                          ":" / ";" /
                          "@" / "\" /
                          "," / "." /
                          DQUOTE

.. data:: CTEXT

   Defined as :data:`VISIBLE` minus :data:`LPAREN`, :data:`RPAREN`,
   and :data:`BSLASH`.  Equivalent to the following rule in
   `RFC 5322, Section 3.2.2
   <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_
   (excluding obs-ctext):

   .. code-block:: text

      ctext           =   %d33-39 /          ; Printable US-ASCII
                          %d42-91 /          ;  characters not including
                          %d93-126 /         ;  "(", ")", or "\"
                          obs-ctext

.. data:: ATEXT

   Defined as :data:`VISIBLE` minus :data:`SPECIALS`.
   Equivalent to the following rule in
   `RFC 5322, Section 3.2.3
   <https://datatracker.ietf.org/doc/html/rfc5322#section-3.2.3>`_:

   .. code-block:: text

      atext           =   ALPHA / DIGIT /    ; Printable US-ASCII
                          "!" / "#" /        ;  characters not including
                          "$" / "%" /        ;  specials.  Used for atoms.
                          "&" / "'" /
                          "*" / "+" /
                          "-" / "/" /
                          "=" / "?" /
                          "^" / "_" /
                          "`" / "{" /
                          "|" / "}" /
                          "~"

.. data:: DTEXT

   Defined as :data:`VISIBLE` minus :data:`LBRACK`, :data:`RBRACK`,
   and :data:`BSLASH`.  Equivalent to the following rule in
   `RFC 5322, Section 3.4.1
   <https://datatracker.ietf.org/doc/html/rfc5322#section-3.4.1>`_
   (excluding obs-dtext):

   .. code-block:: text

      dtext           =   %d33-90 /          ; Printable US-ASCII
                          %d94-126 /         ;  characters not including
                          obs-dtext          ;  "[", "]", or "\"


Semantic tokens
^^^^^^^^^^^^^^^

This is the reason why I wrote this documentation to begin with :)


Basic tokens
""""""""""""

.. class:: QuotedPair

   | **Base class**: :class:`Token`
   | **Grammar**: ``"\" (VCHAR / WSP)`` (:data:`BSLASH` followed by
      :data:`VISIBLE` or :data:`WHITESPACE`)
   | **Defined in**: `RFC 5322, Section 3.2.1
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.2.1>`_,
      Quoted characters

   Represent quoted-pair as defined in RFC 5322.
   A :class:`QuotedPair` is always two characters long and
   consists of a :data:`BSLASH` followed by a :class:`Text`.

.. class:: CommentText

   | **Base class**: :class:`Text`
   | **Grammar**: one or more :data:`CTEXT`

   Represent ctext as defined in RFC 5322.

.. class:: AtomText

   | **Base class**: :class:`Text`
   | **Grammar**: one or more :data:`ATEXT`

   Represent atext as defined in RFC 5322.

.. class:: DotAtomText

   | **Base class**: :class:`Token`
   | **Grammar**: ``1*atext *("." 1*atext)`` (chunks of :data:`ATEXT`
      joined by :data:`PERIOD`)
   | **Defined in**: `RFC 5322, Section 3.2.3
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.2.3>`_,
      Addr-Spec Specification

   Represent dot-atom-text as defined in RFC 5322.
   Note that, despite what the name implies, :class:`DotAtomText`
   is actually a token.  (The choice was made to consistently
   separate the special characters from text, so... yeah :c)

.. class:: DomainText

   | **Base class**: :class:`Text`
   | **Grammar**: one or more :data:`DTEXT`

   Represent dtext as defined in RFC 5322.

.. class:: DomainLiteral

   | **Base class**: :class:`Token`
   | **Grammar**: ``"[" *dtext "]"``
   | **Defined in**: `RFC 5322, Section 3.6.4
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4>`_,
      Identification Fields as "no-fold-literal"
   | **Related**: "domain-literal" in `RFC 5322, Section 3.4.1
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.4.1>`_
      Addr-Spec Specification

   Represent domain-literal in RFC 5322 without CFWS, or just
   a no-fold-literal.


White space
"""""""""""

.. line blokies :D
     - https://rest-sphinx-memo.readthedocs.io/en/latest/ReST.html#line-blocks
     - https://stackoverflow.com/questions/54001054/force-a-new-line-in-sphinx-text

.. class:: WhiteSpace

   | **Base class**: :class:`Text`
   | **Grammar**: ``1*WSP`` (one or more :data:`WHITESPACE`)
   | **Defined in**: `RFC 5234, Section B.1
      <https://datatracker.ietf.org/doc/html/rfc5234#appendix-B.1>`_,
      Core Rules; reiterated in `RFC 5322, Section 2.2
      <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_,
      Header Fields

   Represent at least one space and/or horizontal tab.
   In places where the whitespace is omittable, a
   :class:`WhiteSpace` token is simply not created.

.. class:: WhiteSpaceToken

   | **Base class**: :class:`Token`
   | **Described in**: `RFC 5322, Section 3.2.2
      <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_,
      Folding White Space and Comments

   A category of tokens that should be normalized to a single space.
   To quote from the last paragraph of 3.2.2, these include:

      Runs of FWS, comment, or CFWS that occur between lexical tokens
      in a structured header field are semantically interpreted as a
      single space character.

.. class:: FoldingWhiteSpace

   | **Base class**: :class:`WhiteSpaceToken`
   | **Grammar**: ``[*WSP CRLF] 1*WSP``
   | **Defined in**: `RFC 5322, Section 3.2.2
      <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_,
      Folding White Space and Comments

   Represent FWS as defined in RFC 5322.

   A :class:`FoldingWhiteSpace` token should always contain a
   :class:`WhiteSpace`, optionally preceded by :data:`CRLF`,
   optionally preceded by another :class:`WhiteSpace`
   (that is, the "trailing whitespace", if there is any).

.. class:: Comment

   | **Base class**: :class:`WhiteSpaceToken`
   | **Grammar**: see below
   | **Defined in**: `RFC 5322, Section 3.2.2
      <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_,
      Folding White Space and Comments

   Represent comment as defined in RFC 5322 with the following grammar:

   .. code-block:: text

      ccontent        =   ctext / quoted-pair / comment
      comment         =   "(" *([FWS] ccontent) [FWS] ")"

   That is, a :class:`Comment` token should contain exactly
   one :data:`LPAREN`, a run of :class:`CommentText`,
   :class:`QuotedPair`, or nested :class:`Comment`, with
   at most one :class:`FoldingWhiteSpace` appearing before or after
   each such token, closing with exactly one :data:`RPAREN`.

.. class:: CommentFoldingWhiteSpace

   | **Base class**: :class:`WhiteSpaceToken`
   | **Grammar**: ``(1*([FWS] comment) [FWS]) / FWS``
   | **Defined in**: `RFC 5322, Section 3.2.2
      <https://datatracker.ietf.org/doc/html/rfc5322#section-2.2>`_,
      Folding White Space and Comments

   Represent CFWS as defined in RFC 5322.
   A :class:`CommentFoldingWhiteSpace` should be:

   *  A run of at least one :class:`Comment`, with at most one
      :class:`FoldingWhiteSpace` appearing before or after each
      :class:`Comment`.  Or...
   *  The :class:`FoldingWhiteSpace` itself.


Headers: message identifiers
""""""""""""""""""""""""""""

Currently, folding within Message ID is considered invalid.
I might implement a more liberal grammar in the future, but
this is it for now...

.. class:: IdLeft

   | **Base class**: :class:`Tokens`
   | **Grammar**: ``dot-atom-text``
   | **Defined in**: `RFC 5322, Section 3.6.4
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4>`_,
      Identification Fields

   Represent id-left as defined in RFC 5322.
   Note that no folding is allowed.

.. class:: IdRight

   | **Base class**: :class:`Tokens`
   | **Grammar**: ``dot-atom-text / no-fold-literal``
   | **Defined in**: `RFC 5322, Section 3.6.4
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4>`_,
      Identification Fields

   Represent id-right as defined in RFC 5322.
   Note that no folding is allowed either.

.. class:: MsgId(Tokens)

   | **Base class**: :class:`Tokens`
   | **Grammar**: ``"<" id-left "@" id-right ">"``
   | **Defined in**: `RFC 5322, Section 3.6.4
      <https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4>`_,
      Identification Fields

   Represent msg-id as defined in RFC 5322.
   Note that CFWS is excluded on either sides to allow for
   the ability to "share" CFWS between two Message IDs.
