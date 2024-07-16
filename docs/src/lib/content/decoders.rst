
:mod:`.content.decoders` --- Content transfer decoders
------------------------------------------------------

.. module:: rdks.mail.content.decoders
   :synopsis: RFC 2045 decoders

Inverse functions of the sibling :mod:`.content.encoders` module.
The original body should be recoverable provided that the *linesep*
and *canonical_linesep* parameters are the same.

(i think i already said that.... *somewhere*)

These decoders are much stricter than
:meth:`~email.message.Message.get_payload` with ``decode=True``:
namely that no EOL translation is done, and each line is expected
to be delimited by *canonical_linesep*.
**Sanitization is expected.**

.. exception:: DecodingError

   Usually this doesn't mean your input is bad (unless it is
   :func:`decode_base64` and there is a :exc:`binascii.Error`
   at the top of your traceback); it's just picky for reasons
   I explained above.

   Also a subclass of :class:`ValueError`.

and FYI *maxlinelen* doesn't do anything in these methods.
They are just there so that a future implementation that needs to
know how much memory to allocate can benefit from a known upper-limit?
I have no idea. They are not used to invalidate anything, simply
because it makes no sense to.

.. function:: decode_qp(body, *, maxlinelen=80, linesep=CRLF, canonical_linesep=None)

   Decode the encoded *body* with the quoted-printable encoding,
   again according to `RFC 2045, Section 6.7`_.

.. _RFC 2045, Section 6.7: https://datatracker.ietf.org/doc/html/rfc2045#section-6.7

   .. note::

      :meth:`decode_qp` does not strip any padded whitespace following
      a trailing equal sign.  I'm not sure how to handle that, and
      I imagine doing that here would be counterproductive.

.. function:: decode_base64(body, *, maxlinelen=None, linesep=CRLF, canonical_linesep=None)

   Decode the encoded *body* with the base64 encoding using
   :func:`binascii.a2b_base64`.

   *linesep* together with *maxlinelen* are not used.

.. function:: decode_verbatim(body, maxlinelen=80, linesep=CRLF, canonical_linesep=None, ascii=False)

   Equivalent to :func:`~rdks.mail.encoders.encode_verbatim`, except *linesep*
   and *canonical_linesep* are switched and *maxlinelen* is ignored.

