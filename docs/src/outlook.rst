=============================================================
:mod:`outlook.py <rdks.mail.outlook>` --- Thread-Index parser
=============================================================

.. module:: rdks.mail.outlook
   :synopsis: Thread-Index parser

All objects here are immutable & hashable.
Where modification is common, methods are added to
return a modified copy rather than modifying itself,
e.g. :meth:`ThreadIndex.add_response`.

Equality (``__eq__()``) is only defined to consider another
object of the same class and otherwise falls back to default
equality (which is equivalent to ``self is other``, which is
(hopefully) always False).

.. class:: ThreadIndex(header, responses=())

   The Thread-Index header, as described by the Microsoft
   Exchange protocol.  It consists of two parts: the 22-byte
   Conversation Index Header (not to be confused with a MIME
   header), and zero or more 7-byte Response Levels.
   They are accessible through :attr:`header` as a
   :class:`Header` object and :attr:`responses` as a
   :class:`tuple` of :class:`Response` objects.

   .. classmethod:: from_str(value, *, old_filetime=False)
                    from_bytes(value, *, old_filetime=False)

      These methods parse Thread-Index from a base64 string
      or raw bytes.  *old_filetime* is passed to :class:`Header`
      to indicate how the FILETIME should be interpreted.

   .. method:: __str__()
               __bytes__()

      ``str(self)`` and ``bytes(self)`` reconstruct the
      Thread-Index as either a base64 string or raw bytes.

   Read-only properties:

   .. attribute:: header

      Conversation Index Header as a :class:`Header` object.

   .. attribute:: responses

      A :class:`tuple` of Response Levels, each represented
      as a :class:`Response` object.

   .. method:: __eq__(other)
               __hash__()

      Equality and hashing are both defined in terms of the tuple
      consisting of :attr:`header` and :attr:`responses`.

   .. method:: add_response(response)
               add_responses(responses)

      Return a copy of self with *response* (one response) or
      *responses* (iterable of responses) added.

.. class:: Header(date, guid, *, old_filetime=False)

   Conversation Index Header.

   The constructor arguments are simply exposed
   as read-only attributes:

   .. property:: date

      A :class:`FileTime` object.

   .. property:: guid

      A :class:`uuid.UUID` object.

   .. property:: uses_old_filetime

      True or False.

   .. method:: __eq__(other)
               __hash__()

      Equality and hashing are defined in terms of
      the tuple consisting of
      :attr:`date` and :attr:`guid`.

   Parsing and serialization: (these are used by :class:`ThreadIndex`
   except, well, it strictly deals with the first 22 bytes.)

   .. classmethod:: from_bytes(value, *, old_filetime=False)

      Parse raw bytes of the Header.

   .. method:: __bytes__()

      Construct raw bytes representation.

.. class:: Response(delta, random)

   Response Level.

   .. property:: delta

      A :class:`TimeDiff` object.

   .. property:: random

      An 8-bit :class:`int`.

   Parsing and serialization:

   .. classmethod:: from_bytes(value)

      Parse raw bytes of a Response Level.

   .. method:: __bytes__()

      Construct raw bytes representation.

   .. method:: __eq__(other)
               __hash__()

      Equality and hashing defined in terms of
      the tuple consisting of
      :attr:`delta` and :attr:`random`.

.. class:: FileTime(ticks)

   I don't plan to explain this today.

   All you really need to know is that you can convert from
   sensible time formats (Python :class:`~datetime.datetime`
   or Unix epoch) and back to them.  The public constructor
   is useless in that respect because it uses Microsoft's BS
   way of counting time.

   As BS as it is though, you can still access the *ticks* argument,
   since in essence FILETIME is just a 64-bit :class:`int`:

   .. property:: ticks
                 low_datetime
                 high_datetime

      The full 64-bit integer is accessible through *ticks*.
      For technical reasons not yet known to me, *low_datetime*
      and *high_datetime* also defined for convenience of accessing
      the least and most significant 32 bits.

   .. method:: __eq__(other)
               __hash__()

      Equality and hashing are defined in terms of *ticks*.

   Parsing and serialization:

   .. classmethod:: from_bytes(data)

      Parse FILETIME from bytes

   .. method:: __bytes__()

      Serialize FILETIME as bytes

   Alright. Onto the more sensible constructors...

   .. classmethod:: from_datetime(dt)

      Construct from :class:`~datetime.datetime`.
      Naive datetimes are assumed to represent UTC time.

   .. classmethod:: from_unix(epoch, scale=1_000_000_000)

      Construct from the Unix *epoch* in nanoseconds multiplied by
      *scale*.  By default, *scale* is a billion, making *epoch*
      effectively converted from seconds.  Note that sub-100ns
      precisions are lost, so converting from any *scale* that is
      not a multiple of 100 is lossy.

   Getting out of this hell is just as easy:

   .. method:: as_datetime(with_tz=False)

      Convert to a naive :class:`~datetime.datetime` object,
      approximating the UTC time of self to microsecond precision.
      If *with_tz* is True, the naive datetime is given a time zone
      of :attr:`timezone.utc <datetime.timezone.utc>`.

   .. method:: as_unix(scale=1_000_000_000)

      Convert to Unix epoch in nanoseconds multiplied by *scale*.
      This will give you an :class:`int` rounded towards negative
      infinity, but if you are okay with float, use the native
      100ns unit and do the division yourself, i.e.
      ``self.as_unix(100) * 1e-7``.

      Try to make *scale* a multiple of 100 for reasons explained
      above.  Due to the naive computation of floor division,
      it will need some space if *scale* is not a multiple of 100
      and also very large.

.. class:: TimeDiff(sig, value)

   TimeDiff representation.  (Microsoft is pretty shit at this)

   .. property:: sig

      The signal bit.  This is 0 for 18 bit shift or 1 for 23 bit shift.

   .. property:: value

      The unshifted, 31-bit number.

   .. property:: MAX_SMALL_TICKS

      Largest number representable with :attr:`sig` = 0.

   .. property:: MAX_LARGE_TICKS

      Largest number representable with :attr:`sig` = 1.

   .. method:: __eq__(other)
               __hash__()

      Equality and hashing are defined in terms of the tuple
      consisting of :attr:`sig` and :attr:`value`.

   Parsing and serialization:

   .. classmethod:: from_bytes(diff)

      Parse TimeDiff from bytes

   .. method:: __bytes__()

      Serialize TimeDiff as bytes

   From/to Microsoft's tick unit:

   .. classmethod:: from_ticks(ticks[, sig])

      Represent number of ticks (100ns intervals) as TimeDiff.
      *sig* may be provided to explicitly use a certain shift,
      but otherwise it will be automatically determined.

      :exc:`ValueError` is raised for ticks exceeding the
      maximum representable numbers.

   .. method:: as_ticks()

      Return the number of ticks.

   From/to Python native timedelta:

   .. classmethod:: from_timedelta(delta[, sig])

      Represent :class:`~datetime.timedelta` as TimeDiff.
      *sig* may be provided to explicitly use a certain shift,
      but otherwise it will be automatically determined.

      :exc:`ValueError` is raised for ticks exceeding the
      maximum representable numbers.

   .. classmethod:: as_timedelta()

      Return a :class:`~datetime.timedelta` representation of self.
