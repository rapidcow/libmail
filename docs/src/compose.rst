================================================================
:mod:`compose.py <rdks.mail.compose>` --- mail composer for SMTP
================================================================

.. module:: rdks.mail.compose
   :synopsis: electronic mail composition

.. remembered that i saw this was a thing when writing perspective docs
   and found that this is called the option list:
   https://stackoverflow.com/questions/15258831/how-to-handle-two-dashes-in-rest/62481918#comment21554147_15258831
   https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#option-lists

.. that said, i think i will use directives...
   https://www.sphinx-doc.org/en/master/usage/domains/standard.html

**Note**: depends on `rdks-list`_ for config parsing

.. _rdks-list: https://git.rapidcow.org/rdks-list/about/

a loose demo i came up with a while ago (copied from a discord message
i wrote to a friend): compose.py basically converts something like this
(NOTE: this is just the ":ref:`content <message content>`" part):

.. code-block:: text

   multipart/alternative
     with boundary AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
     epilogue << |
       |
       | lol jk, chat gpt wrote this XD get lost spammer
       |
     including
       text/plain < body.eml
         with charset us-ascii
         of encoding quoted-printable
           where maxlinelen=78
         of disposition inline
           with filename insert cash or select payment type.txt
       text/html < body.html
         with charset us-ascii
         of encoding quoted-printable
           where maxlinelen=78
         of disposition inline
           with filename insert cash or select payment type.html

into these equivalent python calls to the :mod:`email` library
(and a bit of :mod:`.content.encoders`)::

   import rdks.mail.content.encoders as mime

   message['MIME-Version'] = '1.0'
   message['Content-Type'] = 'multipart/alternative'
   message.set_boundary('A' * 57) # with boundary A...[57 times]
   message.epilogue = '\r\nlol jk[...]\r\n' # epilogue << ...

   # including just does the same thing recursively,
   # then appends each part with Message.attach()
   message.set_payload([])
   # clone message
   part_one = type(message)(message.policy)
   part_one['Content-Type'] = 'text/plain'
   data = open('body.eml', 'rb').read() # < body.eml. this gets encoded later
   part_one.set_param('charset', 'us-ascii', replace=True) # with charset ...
   part_one['Content-Transfer-Encoding'] = 'quoted-printable' # of encoding ...
   # where maxlinelen = 78 is passed here:
   part_one.set_payload(mime.encode_qp(data, maxlinelen=78))
   part_one['Content-Disposition'] = 'inline' # of disposition ...
   part_one.set_param('filename', 'insert cash or select payment type.txt',
                      header='Content-Disposition',
                      replace=True) # with ... but nested
   message.attach(part_one)

   part_two = type(message)(message.policy)
   part_two['Content-Type'] = 'text/html'
   # repeated...
   message.attach(part_two)

and finally prints this:

.. code-block:: email

   MIME-Version: 1.0
   Content-Type: multipart/alternative;
    boundary="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

   --AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
   Content-Type: text/plain; charset="us-ascii"
   Content-Transfer-Encoding: quoted-printable
   Content-Disposition: inline; filename="insert cash or select payment type.txt"

   [CONTENT]

   --AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
   Content-Type: text/html; charset="us-ascii"
   Content-Transfer-Encoding: quoted-printable
   Content-Disposition: inline; filename="insert cash or select payment type.html"

   <p style="text-transform: uppercase;"> [CONTENT] </p>

   --AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA--


Python API
----------

The :mod:`~rdks.mail.compose` module exposes one public function at the moment:

.. function:: main([args])

   Run the program with *args*, a list of command-line options
   defaulting to :data:`sys.argv`.
   See :ref:`command-line options` for what you can pass here.


Command-line options
--------------------

.. program:: compose.py

All options are optional.  (That was a terrible sentence, wow.)

Arguments include:

.. option:: message

   File path of the config file to read from, or ``-`` for stdin.
   Defaults to ``-``.

.. option:: -C <path>, --cwd <path>

   Set the base directory for input files to something other than
   the current working directory.  (The default, FYI, is just
   :func:`os.getcwd` and not the root directory of the path
   specified in the :option:`message <compose.py message>` option.)

.. option:: -o <file>, --output <file>

   Output file to write the RFC 822 message to, or ``-`` for stdout.
   Defaults to ``-``.

.. option:: -s <file>, --save-options <file>

   Write the computed options to *file*.  Keys and values are delimited
   by a space, and booleans are normalized to ``on`` and ``no``.

You may optionally specify an SMTP server to override options with.
This uses :mod:`smtplib`.

.. option:: server, port

   SMTP server host and port number.  This syntax should
   remind you of telnet(1).

   If both are omitted, obviously compose.py won't bother
   connecting to anything.  If port number is omitted,
   the number is selected based on the protocol used:

   *  For SMTP, the default port is 25.
   *  For SMTP SSL, the default port is 465.
   *  For SMTP with STARTTLS, the default port is 587.

.. option:: --protocol <proto>

   How to connect to the server, maybe?  Idk, ask :mod:`smtplib`.

   Here are what each protocol is supposed to mean:

   *  ``smtp`` (default): plain, unencrypted SMTP.
      Uses :class:`smtplib.SMTP` to connect.
   *  ``smtps``: SMTP over SSL.  Uses :class:`smtplib.SMTP_SSL` to connect.
   *  ``starttls``: SMTP with STARTTLS.  Uses :class:`smtplib.SMTP` then
      calls :meth:`smtplib.SMTP.starttls()`.

there are also debug options but i don't want to document those atm

just do ``compose.py -h`` okay


Syntax and structure
--------------------

the syntax for the message config file (the
:option:`message <compose.py message>` option)
is based on rplist, with a few extensions:
comments beginning with the hash sign (``'#'``),
the input directive (``name < file``), and the
inline input directive (``name << ...``).
and one requirement: file is expected to be encoded
with the UTF-8 encoding.

at the moment rplist is not documented, but it's super simple and
i need to explain it to define the quirks, so i will go over it
real quick.  basically rplist is a key-value property list where:

*  keys and values are separated by a space, with each line
   delimited by a LF character.
*  a value may span multiple lines with indentation,
   where the first indent is used to determine where the
   value ends and is removed from the start of each line.

sounds confusing? here is a diagram that might help:

.. code-block:: text

   [hello world]         # key='hello' value='world'
   [hello]               # key='hello'
   [    world]           |             value='world'
   [hello ]              # key='hello' value='\n'
   [    world]           |             value='world'
   [hello  world]        # key='hello' value=' world\n'
   [   a  bc]            |                   'a  bc\n'
   [    defenestration]  |                   ' defenestration'
   [ what world?]        # key=''      value='what world?'

basically, the indent that appeared on the first extended line
must be present on all lines, or else the value terminates.
i need to emphasize this because the entire file is parsed like
this, *including the comments*, which are just key-value pairs
that have a key that begins with ``'#'`` that must span one line
only.  so these are off-limits:

.. code-block:: text

   options
     linesep CRLF
       # comment consumed as part of linesep's value
     maxlinelen 80
   # comment terminates option's value
     8bitmime on

the correct way to comment is to treat ``'#'`` as if it were a key,
either placed outside or inside an ongoing key-value pair:

.. code-block:: text

   # this is fine!
   options
     linesep CRLF
     # also this
     maxlinelen 80
     #   or this
     8bitmime on

note that linesep, maxlinelen, 8bitmime are the keys of the
*embedded* rplist within the "option" key's value.  this will happen
a lot, and the way i implemented it is *not* efficient, but what helps
is that if you understand one layer, you understand everything.

in many places, keys, on top of the basic rplist syntax, supports
the input directives.  the two types are:

*  file input (``<``): reads data from a path to a relative to
   :option:`the current working directory <compose.py -C>`.
   the data is up to the interpretation of the specific key, but
   suffice to say this itself preserves all raw bytes.

   note that different from redirection in POSIX shell, spaces
   around ``<`` are **necessary**.  this means ``text/plain <file``
   *will not* be parsed as a file input, but rather as the string
   ``<file`` [#]_. similarly for ``text/plain< file``, where ``<``
   would be considered a part of the key.

   excess spaces are never stripped either, so ``text/plain.<..file...``
   (where the periods denote spaces) would input a file named
   ``' file   '``.

   .. Note::

      There are no escape mechanisms defined at the moment, so only files
      that do not contain a LF character can be represented (which is the
      case for most operating systems, I think)

      Avoid using dollar signs and backslashes through, since they may be
      used for escapes in a future version.

*  inline string (``<<``): this too preserves all raw bytes (subject
   to the rules explained below), though due to the difficulty of typing
   non-printable characters, its use is generally limited to text.

   unlike Heredoc, inline strings terminate naturally after a certain
   prefix ends.  this is the natural indent parsed according to rplist
   syntax, optionally with an additional prefix specified after ``<<``.
   (again, mandatory spaces, and excess spaces will be preserved.)
   the value would be the concatenation of each line with the prefix
   stripped, and the last LF character removed.

   so here is an example, with the preamble field (periods again
   represent spaces, because Sphinx seems to strip them):

   .. code-block:: text

      multipart/alternative
      ..preamble <<
      ....This is a MIME multi-part message.
      ....# Comments are not interpreted
      ....  Further indents are allowed in subsequent liens
      .... though they must contain than the indent on the
      ....first line (even on completely empty lines...
      ....
      ....^^^ like this.)
      ..# Dedented. Preamble has now ended

   text editors generally don't like lines with whitespace spewing over,
   so adding a non-whitespace prefix is a good way to work around it.
   the way it works is that you specify a prefix in the same way you
   specify a file with ``<``, then use that add prefix to the beginning
   of each line.

   .. code-block:: text


      multipart/alternative
        preamble << |
          |This is a MIME multi-part message.
          |# Comments are still not interpreted
          |
          |And we can do this!
        # Dedented --- again

   For readability, the prefix may be followed by one single space,
   which will be removed.  Additional spaces are preserved:

   .. code-block:: text

      multipart/alternative
        preamble << |
          | This line has no indent
          |Neither does this
          |  This has one space!
          |    Three spaces!
          |     and so "fourth"...
          |
          | And that was an empty line
          | Notice how I didn't have to worry about
          | the trailing space being stripped :)
        # Dedented

   .. note::

      due to the parser's limitations, a "flat" variation of the syntax
      is also supported at the moment:

      .. code-block:: text

         example-1 <<
         Text here
         # Text (not a comment)
         There is no way to end this,
         but let's pretend it did here.

         example-2 << |
         | Text here
         | # Text (not a comment)
         | This ends...
         # as prefix disappears.
         # then normal parsing resumes.

      but this makes very little sense! So do avoid it!

*  some places use substitutions.  that means dollar signs must be
   escaped with ``$$`` but otherwise special characters have cool escapes:

   -  ``#`` can be escaped with ``${hash}``
      (this is likely unnecessary given the strict syntax of
      valid comments, but it is still here in case something
      calls for looser comment syntax :/)
   -  ``<`` and ``>`` can be escaped with ``${less}`` and ``${more}``

   some constants too:

   -  ``${progname}``: always compose.py
   -  ``${progversion}``: current version

   nothing else is defined at the moment.

.. [#] as a result, the ``<`` before a message ID or an addr-spec
   will not be misinterpreted as file input, and need not be escaped ;)


The message config format
-------------------------

Two sections are required:

* headers
* content

*content* will be specified later.  *headers* are just RFC 822 headers.
They can either be input completely verbatim from a file
(or equivalently, an inline string):

.. code-block:: text

   headers < my-rfc-headers.eml
   # OR
   headers << |
     | From: Person A <aip@example.org>
     | To: Person B <bip@example.org>

or written directly, though subject to rplist syntax,
substitution, and inputs (as explained above):

.. hey this syntax highlight is cool

.. code-block:: linuxconfig

   headers
     # reads from a file named now.d/date
     Date: < now.d/date
     From: Curious cow <curious@rapidcow.org>
     To: Math teacher <teach@math.example.org>
     # does not read from anything since < is not lonely
     Message-ID: <a.totally.legit.message.id@rapidcow.org>
     Subject: ${less} 1 implies what about an integer?

though not both, as that would be pretty weird :(

.. note::

   For no reason whatsoever, trailing newline is preserved
   even though it doesn't make sense to end with one in an RFC header.
   This means that, say if you use GNU date to generate the Date field,
   your best bet is to brutally chop off that at the end:

   .. code-block:: sh

      # option one: use tr(1) to delete LF
      date --rfc-email | tr -d '\n' > now.d/date
      # option two: use implicit shell uh thingy
      # that strips whitespace (idk what this is called)
      printf %s "$(date --rfc-email)" > now.d/date

   EOL are translated with :func:`.treol` to the designated *linesep*,
   though I can't guarantee Python will like multiline stuff...


Message options
^^^^^^^^^^^^^^^

You may optionally provide options (there goes the pun... again).
Here is a list of each supported option at the moment:

.. program:: compose.py message options

.. option:: linesep "CRLF" | "CR" | "LF"

   End of line (EOL) marker to use.  Defaults to CRLF.

.. option:: maxlinelen <int>

   Suggested maximum line length limit, including the EOL marker.
   Lines may exceed this number if certain headers are impossible
   to be wrapped or a larger maxlinelen is given in any
   subsequent part.  Defaults to 80.

.. option:: smtpline <int>

   Hard maximum line length limit, also including the EOL marker.
   Lines that get longer than this will result in ugly warnings being
   printed all over the place.
   Defaults to 1000 as per `RFC 5322, Section 2.2.1`_.

.. _RFC 5322, Section 2.2.1: https://datatracker.ietf.org/doc/html/rfc5322#section-2.1.1

Next we have some boolean options.  They all share a common syntax:
``on`` for true, and ``no`` for false.  These are unaltered unless
an SMTP server is provided, e.g. ``compose.py message smtp.office365.com
--protocol starttls``.  The rules get a little more complicated,
but basically you can add ``?`` (the "maybe" quantifier) to the end of
either value to ensure that SMTP capabilities always override the options,
or add ``!`` (the final quantifier) to ensure that they are never overridden.
The exact logic can be found in ``_set_capabilities()``.

In addition here are some equivalent forms for each kind of boolean
(case insensitive):

*  ON: ``true`` ``ok`` ``yes`` ``on`` ``good`` ``positive`` ``enabled``
*  NO: ``false`` ``no`` ``off`` ``bad`` ``negative`` ``disabled``
*  ON? ``true?`` ``ok?`` ``maybe`` ``good?`` ``on?`` ``hopefully``
*  NO? ``false?`` ``no?`` ``maybe...`` ``maybe not`` ``bad?`` ``off?`` ``probably``
*  ON! ``true!`` ``ok!`` ``yes!`` ``good!`` ``on!`` ``absolutely!`` ``yippee!``
*  NO! ``false!`` ``no!`` ``bad!`` ``off!`` ``absolutely not!`` ``never!``

There are more unhinged ones but these guys are here to stay :/

.. option:: smtpsize <int>

   Maximum number of bytes in a message.  Corresponds to the
   SMTPSIZE extension (`RFC 1870`_)
   (`references <https://cr.yp.to/smtp/size.html>`_).
   By default, this is 0, or unlimited.

.. option:: smtputf8 <bool>

   Whether internationalized addresses are supported (?)
   Corresponds to the SMTPUTF8 extension (`RFC 6531`_).
   By default, this is ``no?``, meaning that it will always be
   overridden by server capabilities.

.. option:: 8bitmime <bool>

   Whether to allow the 8bit content transfer encoding.  Corresponds
   to the 8BITMIME extension (`RFC 6152`_).
   By default, this is ``no?``.

.. option:: binarymime <bool>

   Whether to allow the binary content transfer encoding.  Corresponds
   to the BINARYMIME extension  (`RFC 3030`_).  This doesn't do anything
   at the moment, since binary encoding is still pretty elusive (and buggy).
   By default, this is ``no?``.

.. _RFC 1870: https://datatracker.ietf.org/doc/html/rfc1870
.. _RFC 3030: https://datatracker.ietf.org/doc/html/rfc3030
.. _RFC 6152: https://datatracker.ietf.org/doc/html/rfc6152
.. _RFC 6531: https://datatracker.ietf.org/doc/html/rfc6531


Message content
^^^^^^^^^^^^^^^

*content* sets the ``MIME-Version`` and ``Content-*`` headers, as well as
the encoded message body according to MIME 1.0 standards.  (This is the
*real* fun part of compose.py... >:)

*content* may also be input from a file, which would still be treated as
a config file subject to the same syntax.  but since this is completely
equivalent to writing directly in the rplist, i will only define the syntax
in that way.

A MIME part is represented by its content type, followed by parameters.
Syntactically, it is precisely one key-value pair, with the content type
being the key, inputting content from a file:

.. code-block:: text

   maintype/subtype < [FILE]
     [CONFIG]
     [CONFIG]
     ...

*content* contains exactly one MIME part, though it may contain other
MIME parts with the
:option:`including <compose.py message content including>` option.
In that case the pair **must not** contain any input directive.
But otherwise, the options are the same.

None of the following options check for valid input
(except :option:`of encoding <compose.py message content of-encoding>`,
which must be something compose.py can handle)

.. program:: compose.py message content

.. option:: including [subpart ...]

   Add subparts to a multipart document.  Each subsequent pair is parsed
   in identically as the sole part below *content*.

   Equivalent API calls with :meth:`~email.message.Message.set_payload`
   and :meth:`~email.message.Message.attach`::

      message.set_payload([])
      for subpart in ...:
          message.attach(subpart)

.. option:: of <header> <value>

   Set a MIME *header* to *value*.  Only the following subset are
   recognized for now:

   *  :option:`of version <compose.py message content of-version>`
      for MIME-Version
   *  :option:`of type <compose.py message content of-type>`
      for Content-Type
   *  :option:`of encoding <compose.py message content of-encoding>`
      for Content-Transfer-Encoding
   *  :option:`of disposition <compose.py message content of-disposition>`
      for Content-Disposition
   *  :option:`of description <compose.py message content of-description>`
      for Content-Disposition
   *  :option:`of id <compose.py message content of-id>`
      for Content-ID
   *  :option:`of language <compose.py message content of-language>`
      for Content-Language

   Equivalent API calls with :meth:`~email.message.EmailMessage.__delitem__`
   and :meth:`~email.message.EmailMessage.__setitem__`::

      if header != 'description':
          del message[header]
      message[header] = value

.. option:: with <param> <value>

   This option can be used in two places:

   *  When nested within a header (an
      :option:`of <compose.py message content of>` construct),
      it sets ``<param> = "<value>"`` for that header.  E.g.
      you can use it to specify the `filename parameter`_:

      .. code-block:: text

         image/png < Spooky.png
           of encoding base64
           of disposition attachment
             with filename Spooky.png

      which produces:

      .. code-block:: email

         Content-Type: image/png
         Content-Transfer-Encoding: base64
         Content-Disposition: attachment; filename="Spooky.png"

      Equivalent API call with :meth:`~email.message.Message.set_param`::

         message.set_param(param, value, header=header)

   *  When not nested within any header, header defaults to
      Content-Type.  This is so that you can write, for instance,

      .. code-block:: text

         text/plain < essay
           with charset utf-8

      when specifying the `charset parameter`_  instead of something
      ugly like this:

      .. code-block:: text

         place/holder < essay
           of type text/plain
             with charset utf-8

.. _filename parameter: https://datatracker.ietf.org/doc/html/rfc2183#section-2.3
.. _charset parameter: https://datatracker.ietf.org/doc/html/rfc2046#section-4.1.2

.. option:: where <comma-delimited-params>

   This is one thing that admittedly feels out of place...
   but it is meant to resemble Python syntax, like:

   .. code-block:: text

      text/plain < essay
        of encoding quoted-printable
          where maxlinelen = 78, treol = on

   Note that parameters here are separated by ``=`` and
   delimited by commas.  These are not supported in most places
   but a handful of content encoders (like the example above).

.. option:: of-version <value>

   Set the MIME-Version header.  Since MIME-Version is only added
   to the top-level message, you can manually add one to subpart
   if you desire. 

.. option:: of-type <value>

   Set the Content-Type header.  This is only here for completeness;
   please don't be tempted to write

   .. code-block:: text

      place/holder < file
        of encoding quoted-printable
        of type foo/bar
          with charset blah-blah

   because, well, it doesn't make sense okay?  (And as documented in
   :option:`with <compose.py message content with>`, you can set
   header parameters for Content-Type without nesting it at all
   since that's the default.

.. option:: of-encoding <value>

   Set Content-Transfer-Encoding and decides what encoder to use.
   Currently accepted encodings and their respective options
   that can be specified with the
   :option:`with <compose.py message content where>` construct
   (along with their encoders used):

   Encoder-specific options:

   *  ``quoted-printable``: :func:`~rdks.mail.content.encoders.encode_qp`

      -  ``wrap = <bool>``: encoder option.
         By default this is True if the MIME type of message
         starts with ``text/``, i.e. a text message.

      -  ``embed = <bool> | all | line | none``: encoder option.
         By default this is unspecified, i.e. default is ``all`` or
         ``line`` depending on the value of *wrap*.

      -  ``protect = <bool>``: encoder option.
         By default this is False *except* when message is top-level.

   *  ``base64``: :func:`~rdks.mail.content.encoders.encode_base64`

      -  ``chomp = <bool>``: the logic is rather reversed.
         It assumes that each line ends with
         :option:`linesep <compose.py message options linesep>`,
         and asks if you want to chomp the last one off.
         (What actually happens is the opposite since
         :func:`~rdks.mail.content.encoders.encode_base64`
         doesn't really include that last linesep.)

         By default this is true *except* when message is top-level.

   Common options (except for ``binary``, if that will ever get
   to be supported):

   *  ``maxlinelen = <int>``: Passed to the encoder as a keyword
      parameter.  Defaults to
      :option:`maxlinelen <compose.py message options maxlinelen>`
      in the :ref:`global options <message options>`.

   *  ``treol = <bool>``: Whether to transform the inputted data
      with :func:`~rdks.mail.content.treol`.  Does not transform
      by default.

.. option:: of-disposition <value>

   Set the Content-Disposition header.

.. option:: of-description <value>

   Set the Content-Description header.  May be specified multiple times.

.. option:: of-id <value>

   Set the Content-ID header.

.. option:: of-language <value>

   Set the Content-Language header, as per `RFC 3282`_.

.. _RFC 3282: https://datatracker.ietf.org/doc/html/rfc3282
