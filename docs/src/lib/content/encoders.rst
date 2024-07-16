
:mod:`.content.encoders` --- Content transfer encoders
------------------------------------------------------

.. module:: rdks.mail.content.encoders
   :synopsis: RFC 2045 encoders

All encoders take in :class:`bytes` or :class:`bytearray` as input
unless otherwise noted.  Encoding should be reversible, provided that
the same *linesep* and *canonical_linesep* are given.

And don't worry about *canonical_linesep*; that's for Python's
representation of RFC 822 messages in the :mod:`email` library.

.. exception:: EncodingError

   Means what the class name says.
   All functions in this module throw this error.
   Subclass of :class:`ValueError`.

.. function:: encode_qp(body, *, maxlinelen=80, linesep=CRLF, canonical_linesep=None, wrap=True, embed=None, protect=False)

   Encode *body* with quoted-printable encoding according to
   `RFC 2045, Section 6.7`_.  This is IMO a very cool function, heavily
   inspired by `qprint(1) <https://www.fourmilab.ch/webtools/qprint/>`_
   by John Walker.

   *wrap* is a boolean indicating whether CR, LF, and CRLF should
   start a newline.  This is to make embedded Unix files look
   not so painful in quote printed form.  (Tarballs look pretty
   rad this way, by the way. ;)

   *embed* used to be a boolean too, but for more aggressive quoting
   I added a third option.  As such, each option now has a canonical
   string name:

   *  ``"all"``: all characters are embedded whenever possible.
      That means if a line ends with *linesep*, it is written as-is
      in place of a soft line break.  You may also pass :data:`True`
      for this.

   *  ``"line"``: characters in a line are embedded whenever possible,
      while line endings are *never* embedded.  The boolean
      :data:`False` corresponds to this, since this should usually
      be enough for a byte-for-byte representation.

   *  ``"none"``: there is a reason why I mentioned this was inspired
      by qprint(1)... the "paranoid".  Obviously I am paranoid all
      the time, so I implemented this without a millisecond of doubt.
      Performance-wise though, expect this to be slightly slower
      since I don't think enough sane people would use this in place
      of base64 exist to make creating a separate lookup table worth it.

.. _RFC 2045, Section 6.7: https://datatracker.ietf.org/doc/html/rfc2045#section-6.7

.. function:: encode_base64(body, *, maxlinelen=None, linesep=CRLF, canonical_linesep=None)

   Encode *body* with base64 encoding using :func:`binascii.b2a_base64`,
   wrapping each line to the greatest multiple of 4 less than
   ``80 - len(linesep)`` characters.  (That would be 76 for LF and CRLF.)
   *linesep* is not appended to the last line.

.. function:: encode_verbatim(body, *, maxlinelen=80, linesep=CRLF, canonical_linesep=None, ascii=False)

   Encode *body* with... nothing.  That's right, 7bit and 8bit aren't
   really "encodings", so *body* is just returned verbatim (well, at
   most a replace-all if *canonical_linesep* is different).  This function
   only exists to check if lines in *body* delimited by *linesep* have no
   CR or LF in them.  Setting *ascii* to True will also ensure that *body*
   is 8bit-clean.

