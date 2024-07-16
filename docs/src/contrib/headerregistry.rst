
:mod:`.contrib.headerregistry` --- partial implementation of :mod:`email.headerregistry`
----------------------------------------------------------------------------------------

.. module:: rdks.mail.contrib.headerregistry
   :synopsis: this is a genuine bug though

Can you believe that Python's default header registry does *not* have
a special header for In-Reply-To and References??? me neither... =.=

(And it's so trivial to handle! You just have to call the function you
used to parse message id with multiple times + CFWS!)

.. exception:: InvalidHeaderDefect

   Subclass of :exc:`email.errors.HeaderDefect`.

.. class:: HeaderRegistry

   Subclass of :class:`HeaderRegistry` that registers the following:

   *  Message-ID:         :class:`UniqueMessageId`
   *  Resent-Message-ID:  :class:`MessageId`
   *  In-Reply-To:        :class:`UniqueMessageIdList`
   *  References:         :class:`UniqueMessageIdList`

.. class:: ParsedHeader

   Re-implemented header class.  How it works is basically this:

   .. method:: parse_strict(value)

      Return a :class:`list` of tokens that best represents
      *value* or raise a :class:`.ParseError` for any invalid header.

   .. method:: parse_sloppy(value)

      Return a :class:`list` of tokens that represents *value* as
      a last resort.  Anything sensible is fine, though it
      must not fail for any kind of quirky input.
      (It never hurts to return ``[WhiteSpaceToken([Text(value)])]``,
      just saying... we gotta return *something*.)

.. class:: MessageId
           UniqueMessageId

   Wrapper for :func:`.parse_message_id`, though sloppy parsing
   is implemented as a last resort.  I'm not sure how that part
   works, but I think IDs that use :data:`.LANGLE` and
   :data:`.RANGLE` will be fine.  The Unique variant has
   ``max_count`` set to 1.

.. class:: MessageIdList
           UniqueMessageIdList

   Wrapper for :func:`.parse_references`, though sloppy parsing
   is implemented as a last resort.  The Unique variant also has
   ``max_count`` set to 1.

