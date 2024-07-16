
:mod:`.contrib.contentmanager` --- re-implementation of :mod:`email.contentmanager`
-----------------------------------------------------------------------------------

.. module:: rdks.mail.contrib.contentmanager
   :synopsis: the objectively better content manager /j

ethan's objectively superior contentmanager !!! 😤😤😤

features include:

1. only sets what is necessary (Content-Transfer-Encoding and the
   charset parameter are the only things set as a side effect;
   the rest are all )
2. actually an attempt at a replacement and not just yelling
   ":meth:`~email.message.Message.get_payload` is deprecated
   go use this new method which lacks documentation and
   clarification in every possible way!"
   (even though i don't really see the point of "replacing" tbh)
3. lets you add the three other date params + the size_ param from
   RFC 2183 (not_ just_ filename_ !!)
4. PRECISE QUOTED-PRINTABLE ENCODING WITHOUT LOOKING LIKE JUMBLED CRAP!!!
   (IT IS REAL NOW! see the protecc argument! >:3)
5. and last but not least..... **you get to explicitly keep that trailing
   newline purged for whatever reason !!!** (it's weird if anyone actually
   wants to, but it is important that you *can*. i hate it when something
   f**ks up my input because it thinks trailing newline is always right
   and many people don't care enough to tell ``"foo"`` and ``"foo\n"``
   apart anyways (say that to hashing algorithms, hmph...))

ok that was very much a joke i'm sorry - i do not mean anything bad
about the python contributors. i like the *idea* of a new interface bc
the original email code is riddled with very dated bugs.....
but i just find the actual thing unbearable. it might just be me
though, so i'm not opening another python issue ever again and
am doing this instead :)

(oh yeah and you can directly use
:mod:`.content.encoders` and :mod:`.content.decoders`
so the use of this module is merely a convenient hack, and to some
extent even redundant!)

.. _size: https://datatracker.ietf.org/doc/html/rfc2183#section-2.7
.. _not: https://datatracker.ietf.org/doc/html/rfc2183#section-2.4
.. _just: https://datatracker.ietf.org/doc/html/rfc2183#section-2.5
.. _filename: https://datatracker.ietf.org/doc/html/rfc2183#section-2.6

.. class:: ContentManager

   A somewhat drop-in replacement of
   :class:`~email.contentmanager.ContentManager`.
   They are naturally bloated, due to the ambition of setting
   everything Content-related in on go, but I hope the way I
   organized it is more sensible and flexible :)

   To use this, replace the default content manager in your
   policy of choice::

      from rdks.mail.contrib.contentmanager import ContentManager
      cm = ContentManager()
      message = EmailMessage(policy=existing_policy.clone(cm))

   or use one of the equivalent default policies
   to replace
   :data:`~email.policy.default`,
   :data:`~email.policy.SMTP`,
   :data:`~email.policy.SMTPUTF8`,
   :data:`~email.policy.HTTP`, or
   :data:`~email.policy.strict`
   (note that this also patches
   the header factory)::

      from rdks.mail.contrib.policy import default
      message = EmailMessage(policy=default)

   Note that you have to construct :class:`ContentManager` yourself.
   There is no global instances like
   :data:`~email.contentmanager.raw_data_manager`
   since there aren't any instance-specfic hooks:
   everything I have to offer comes by default, not
   through a bunch of undocumented hooks I don't even
   know how to override >_>

   .. method:: get_content(message, *, decode=True, decode_content=True)

      Fancy version of :meth:`~email.message.Message.get_payload` that
      returns a bunch of stuff.  This method, minus *message*, is your
      function signature for :meth:`~email.message.EmailMessage.get_content`
      provided that you did the step above and didn't override anything.
      ``*args`` and ``**kwds`` are used in the code only if you want
      :meth:`get_content` to accept more arguments than it already does.

      The task that :meth:`get_content` performs differs depending on
      whether your message is multipart and its charset parameter:

      *  If *message* returns true for
         :meth:`~email.message.EmailMessage.is_multipart`,
         the *decode* parameter is used to determine whether
         any logic will be used to return a more sensible (?)
         representation of the message.  At the moment, that
         means to:

         -  Return a single :class:`~email.message.Message` object
            for messages of type ``message/rfc822``;
         -  Return the raw :class:`bytes` for messages of type
            ``message/delivery-status``;

         and to return :meth:`~email.message.Message.get_payload`
         in every other case.  Specify ``decode=False`` to simply
         return :meth:`~email.message.Message.get_payload`.
         *decode_content* is unused.

         **Hook**: :meth:`get_multipart_content`, where *decode* is
         normalized to a :class:`bool`.

      *  Otherwise, if *message* returns false for
         :meth:`~email.message.EmailMessage.is_multipart`,
         the *decode* parameter doubles as the *errors*
         parameter of :meth:`bytes.decode`, which is used
         to decode the Content-Transfer-Encoding decoded payload
         with the message's charset.  If *decode* is the
         singleton :data:`True`, *errors* will be passed as
         ``'strict'``; otherwise it is assumed that *decode*
         is a valid error handler name and passed exactly.
         This means that both charset and ``decode_content=True``
         need to be present for string decoding to take place.
         The return value, in this case, is a :class:`str` instance.

         **Hook**: :meth:`get_text_content`, where *decode* is
         renamed to *errors* and *decode_content* is renamed to *decode*.

         In any other case, the return value is a :class:`bytes` instance.

         If *decode* is set to False while *decode_content* is
         untouched, Content-Transfer-Encoding is still used to
         decode the payload with the appropriate content decoder.
         Set *decode_content* to False to retrieve the raw payload.

         **Hook**: :meth:`get_raw_content`, where *decode_content* is
         renamed to *decode*.

         Decoding is done in the strictest manner possible
         (e.g. a :class:`TypeError` to be raised for payload
         of any type other than :class:`str` and :class:`bytes`)
         until I figure out reasonable cases to make exceptions
         for.  For now, you may simply use
         :meth:`~email.message.Message.get_payload` in conjunction
         with a MIME content decoder, or override specific content
         decoder hooks (see ...)

   .. method:: get_multipart_content(message, decode=True)

      Implements the multipart case in :meth:`get_content`.

   .. method:: get_text_content(message, errors='strict'[, decode])

      Implements the non-multipart case where a truthy *decode* value
      is passed to :meth:`get_content` and *message* defines a charset.
      Note that the *decode* keyword argument (renamed from *decode_content*)
      assumes the same default as :meth:`get_raw_content`.

   .. method:: get_raw_content(message, decode=True)

      Implements the base non-multipart case, which simply returns
      the content-decoded bytes.
      This ultimately calls :meth:`decode_body` with the corresponding CTE.

   .. method:: set_content(message, content, mimetype, *, boundary)
               set_content(message, content, mimetype, charset, *, errors, cte, treol, fixeol, linesep, **enc_params)

      (Every parameter except *content* is optional.  I just got a bit
      tired of writing "``=None``" everywhere.)

      This is *the* most horrendous function signature I have ever written.

      Oh wait, there is more!  The common options are even *worse*!

      .. method:: set_content(*, description, disposition, filename, creation_date, modification_date, read_date, size, cid, language)
         :no-index:

      (hahaha.... i want to die staring at this)

      Anyhow, it should still be clear what the common options do:
      *description*, *disposition*, *cid* and *language* are all
      MIME headers of essentially the same name (Content-Description,
      Content-Disposition, Content-ID, and Language).  *filename*, *creation_date*,
      *modification_date*, *read_date*, and *size* are paramaters
      of the Content-Disposition, as defined in `RFC 2183, Section 2`_.
      Note that they should be converted to :class:`str` beforehand,
      because I do not perform any validation before passing onto
      :meth:`~email.message.EmailMessage.__setitem__`,
      :meth:`~email.message.EmailMessage.replace_header`, or
      :meth:`~email.message.EmailMessage.set_param`.
      Anything more than this is going to drive everyone insane.

      .. _RFC 2183, Section 2: https://datatracker.ietf.org/doc/html/rfc2183#section-2

      One tiny rule though: if *disposition* is not provided and any
      other Content-Disposition parameter is provided,
      it is taken to be *inline* unless a filename is provided,
      in which case it is taken to be an *attachment*.
      This is necessary as setting parameters without a base value
      is kind of weird (I mean what else should we write,
      "``Content-Disposition: ; filename=foo.png``"?)

      .. note::

         though... ``MIME-Version: 1.0`` is always added to *message*
         if it is an :class:`~email.message.EmailMessage`!
         And I like MIME-Version declared at the top, so sorry
         Python :) (I can see why they did that later though)

      The rest of the madness unfolds, depending on the type of *content*:

      *  The first signature is used when *content* is either a
         :class:`~email.message.Message` object or a :class:`list`.
         If it is a :class:`~email.message.Message` instance,
         payload is set to a list containing *content* as the sole item,
         and Content-Type is set to ``message/rfc822`` unless *mimetype*
         says otherwise (which it probably shouldn't?)  You should not set
         the boundary though as that kind of makes no sense (and is...
         not RFC-compliant?), but I care too little to check.

         TL;DR though, if you want to use :meth:`set_content` in
         this form, just pass the message and you should be good::

            # either this...
            message.set_content(attached_msg)
            # or this...
            message.add_attachment(attached_msg)

         If *content* is a :class:`list`, what happens is pretty
         straightforward: the payload is set to just that (though
         a soft copy is created to not mess things up).  Content-Type
         is set to *mimetype* if it is provided, but otherwise defaults
         to ``multipart/mixed``, defined in `RFC 2046, Section 5.1.3`_.

         .. _RFC 2046, Section 5.1.3: https://datatracker.ietf.org/doc/html/rfc2046#section-5.1.3

         **Hook**: :meth:`set_multipart_content`, where *parts* is
         always a list.  *enc_params* are not used.

      *  The second signature is used when *content* is a :class:`str`
         or :class:`bytes`.  For :class:`str`, the call::

            cm.set_content(msg, string,
                           mimetype, charset,
                           errors=errors, **kwds)

         is nothing but a shorthand for::

            content = string.decode(charset, errors)
            cm.set_content(msg, content,
                           mimetype, charset, **kwds)

         as :meth:`set_content` does not differentiate between binary
         and text data based on the type.

         **Hook** for the :class:`str` case: :meth:`set_text_content`,
         where all arguments except the common options are passed
         (including *enc_params*).

         **Hook** for the :class:`bytes` case: :meth:`set_raw_content`,
         where the aforementioned arguments except *errors* are passed
         (including *enc_params* --- still!)

         Unlike the first case, leaving out *mimetype* would leave
         Content-Type unset or untouched; the presence of *charset*
         would set a content type of ``text/plain`` in that case,
         but only if there wasn't already a Content-Type.  Likewise,
         if *charset* is omitted, it is effectively deleted.
         Users should bear in mind the defaults for a Content-Type
         as defined in `RFC 2045, Section 5.2`_ if they do not set one.
         The **only** exception is when *message* was a
         multi-part message, in which case any already present
         Content-Type value is considered undesirable and is thus purged.

         This lets you separate concerns and use :meth:`set_content`
         to set only what it must set and what you tell it to set:

         .. testsetup::

            from email.message import EmailMessage
            from rdks.mail.contrib.policy import default

         .. doctest::

            >>> msg = EmailMessage(policy=default)
            >>> msg['MIME-Version'] = '1.0'
            >>> msg['Content-Type'] = 'text/html'
            >>> msg.set_param('charset', 'utf-8')
            >>> msg.set_content(b'<p>\xc3\xb6uie</p>\n', cte='8bit')
            >>> print(bytes(msg).decode('utf-8'), end='')
            MIME-Version: 1.0
            Content-Type: text/html; charset="utf-8"
            Content-Transfer-Encoding: 8bit
            <BLANKLINE>
            <p>öuie</p>

         Content-Transfer-Encoding, in general, must be explicitly
         passed using the *cte* parameter.  In the case where *cte*
         is not specified, any existing Content-Transfer-Encoding is
         deleted, and the encoding proceeds as if *cte* were 7bit,
         the default encoding defined in `RFC 2045, Section 6.1`_.
         Notice that in the above example I had to include ``cte='8bit'``
         because ``\xc3\xb6`` is a non-ASCII character encoded in UTF-8.
         If I choose to leave it out, well....

         .. doctest::

            >>> msg.set_content(b'<p>\xc3\xb6uie</p>\n')
            Traceback (most recent call last):
              ...
            rdks.mail.content.encoders.EncodingError: body is not ascii

         Things won't look pretty, let's just say.

         The options *treol* and *fixeol* specify whether
         :meth:`set_content` should use :func:`~rdks.mail.content.treol`
         to translate EOL markers in *content* to *linesep* and append
         *linesep* if *content* didn't end with an EOL.
         *fixeol* is true by default whenever *treol* is true and
         ignored whenever *treol* is false.  *linesep* is the policy's
         *linesep* by default (which makes it possible for, say,
         quoted-printable encoded text to be embedded.)

         By default, *treol* is true unless the main type is not
         "text" or *cte* is base64.
         In any case, however, you may explicitly set *treol* to True
         so that EOL is always translated to *linesep*, or set it to False
         so that the raw bytes are preserved verbatim.

         The remaining arguments are passed to the content encoders.
         In particular, *maxlinelen* is derived from the policy's
         :attr:`~email.policy.Policy.max_line_length` plus the length of
         the policy's :attr:`~email.policy.Policy.linesep` if one isn't
         specified.

         .. _RFC 2045, Section 5.2: https://datatracker.ietf.org/doc/html/rfc2045#section-5.2
         .. _RFC 2045, Section 6.1: https://datatracker.ietf.org/doc/html/rfc2045#section-6.1

   .. method:: set_multipart_content(message, parts, mimetype=None, *, boundary=None)

      Implements the multipart case of :meth:`set_content`.
      This is a trivial wrapper of
      :meth:`~email.message.Message.set_payload`.
      A boundary is optionally set with
      :meth:`~email.message.EmailMessage.set_boundary`.

   .. method:: set_text_content(message, content, mimetype=None, charset='utf-8', *, errors='strict', **kwds)

      Implements the non-multipart case of :meth:`set_content`
      when *content* is a :class:`str`.
      *mimetype*, *charset* and *kwds* are passed to
      :meth:`set_raw_content`.  Note that *charset* has a default,
      ``'utf-8'``, which is consistent with Python's
      :meth:`email.contentmanager.raw_data_manager.set_content`
      handler for :class:`str`.

   .. method:: set_raw_content(message, content, mimetype, charset, *, cte, treol, fixeol, linesep, **enc_params)

      Implements the base non-multipart case for when *content*
      is a bytes-like object.  Everything except *message* and *content*
      is, again, optional.
      This ultimately calls :meth:`encode_body` with the corresponding CTE.


Content encoders & decoders
^^^^^^^^^^^^^^^^^^^^^^^^^^^

this part describes something that i think is very cool

i will start with describing the encoders (setters) first, though

.. class:: ContentManager
   :noindex:

   .. method:: encode_body(message, body, cte, *, maxlinelen, linesep, **kwds)

      Encode *body* as :class:`bytes` to the MIME payload as
      :class:`bytes`.  The produced representation should be
      completely reversible by :meth:`decode_body` with the
      same parameters.

   .. method:: decode_body(message, body, cte, *, maxlinelen, linesep, **kwds)

      Decode the MIME-encoded *body* as :class:`bytes` to the
      original :class:`bytes`.  This function is, again, too strict
      to handle :class:`~email.message.Message` objects found in the
      wild (namely, those that Python's feed parser generates), so
      you may alleviate that by subclassing :class:`ContentManager`
      and using a more permissive decoding mechanism here.
      For now it solely serves to invert :meth:`encode_body`.

   Each of these methods dispatches its arguments to another method
   of the name ``encode_NAME`` or ``decode_NAME``, where ``NAME``
   is created by normalizing *cte* to all lowercase letters and
   replacing hyphens (``-``) with underscores (``_``).
   All options are passed except the *cte* option.
   The default encoder and decoder implementations are simple wrappers
   of methods corresponding to functions in the :mod:`.content.encoders`
   and :mod:`.content.decoders` modules respectively, and anything
   undefined will result in... this:

   .. this is covered in the unittest, but just for funsies
      we will do it again here :)

   .. doctest::

      >>> msg = EmailMessage(policy=default)
      >>> msg.set_content(b'hello world\n', cte='x-uuencode')
      Traceback (most recent call last):
        ...
      ValueError: I do not know how to encode x-uuencode

   For that you can implement ``encode_x_uuencode()``
   (for :meth:`set_content` to work) and ``decode_x_uuencode()``
   (for :meth:`get_content` to work)::

      class MyEnhancedContentManager(ContentManager):
          def encode_x_uuencode(body, *, maxlinelen, linesep):
              return encode_uu_somehow(body)
          def decode_x_uuencode(body, *, maxlinelen, linesep):
              return decode_uu_somehow(body)

      msg = EmailMessage(policy=default)
      msg.set_content(b'hello world\n', cte='x-uuencode') # ok!

   .. note: this is also tested, though only decoding :)
      encoding should be somewhat easy too, tho i'm not sure
      if i need a test.....

   But you do that is beyond the scope of this document
   (and my knowledge too, frankly ;P)

   Here are the methods defined by default.  All functions use
   ``canonical_linesep=b'\n'``.

   .. method:: decode_7bit(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.decoders.decode_verbatim` with ``ascii=True``.

   .. method:: decode_8bit(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.decoders.decode_verbatim` with ``ascii=False``.

   .. method:: decode_quoted_printable(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.decoders.decode_qp`.

   .. method:: decode_base64(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.decoders.decode_base64`.

   .. method:: encode_7bit(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.encoders.encode_verbatim` with ``ascii=True``.

   .. method:: encode_8bit(message, body, *, maxlinelen, linesep)

      Delegate to :func:`.encoders.encode_verbatim` with ``ascii=False``.

   .. method:: encode_quoted_printable(message, body, *, maxlinelen, linesep, wrap, embed, protect)

      Delegate to :func:`.encoders.encode_qp`, with the following defaults:

      *  *wrap* is True if *message*'s main type is either *text*
         or *application*.
      *  *embed* is True if and only if *messaeg*'s main type is *text*.
      *  *protect* is always True, meaning any final line which
         does not end with *linesep* is padded with ``"=" linesep``.
         This means that, let's say, the empty body, without *treol*
         or *fixeol*, would look kind of weird:

         .. doctest::

            >>> msg = EmailMessage(policy=default)
            >>> msg.set_content('', 'text/plain', treol=False, cte='quoted-printable')
            >>> print(msg, end='')
            MIME-Version: 1.0
            Content-Type: text/plain; charset="utf-8"
            Content-Transfer-Encoding: quoted-printable
            <BLANKLINE>
            =

         But that's just the way QP encoding works! And you can
         see everyone agreeing this to be the correct representation:

         .. testsetup::

            import email
            import email.contentmanager

         .. doctest::

            >>> msg.get_content(decode=False)
            b''
            >>> email.contentmanager.raw_data_manager.get_content(msg)
            ''
            >>> msg.get_payload(decode=True)
            b''

   .. method:: encode_base64(body, *, maxlinelen, linesep, chomp)

      Delegate to :func:`.encoders.base64`, with *chomp* if and only if
      *chomp* was passed True by the user as an encoding parameter.

