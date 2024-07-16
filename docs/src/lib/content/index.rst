================================================================
:mod:`rdks.mail.content` --- MIME transfer encoders and decoders
================================================================

.. module:: rdks.mail.content
   :synopsis: pedantic MIME transfer encodings

.. testsetup::

   from rdks.mail.content import *

there is a utility function btw

.. function:: treol(text, linesep=CRLF, fixeol=False)
   :canonical: rdks.mail.content.encoders.treol

   Translate end-of-line (EOL) markers to *linesep*, hence the name
   "Tr-EOL".  By default, this is the Internet standard CRLF sequence,
   or ``b'\r\n'``.

   This is the underlying function that powers many ``treol`` options.
   Note that *text* and *linesep* should be :class:`bytes` or
   :class:`bytearray` instances.

   Without *fixeol*, :func:`.treol` will *not* attempt to ensure that
   the last line ends with a *linesep* if *text* didn't already end
   with one of the EOL markers:

   .. doctest::

      >>> treol(b"'tis the hit game \n among us !")
      b"'tis the hit game \r\n among us !"
      >>> treol(b"'tis the hit game \n among us !", fixeol=True)
      b"'tis the hit game \r\n among us !\r\n"

   (A good way to remember *fixeol* is the `eponymous Vim option
   <https://vimhelp.org/options.txt.html#%27fixeol%27>`_, which
   does the same thing upon writing a file. ;)


(oh wow did it just feel like my whole voice changed when
writing documentations)

anyways here are the real deal (documented separately bc i can't
seem to link to either module separately if they were just in one
giant file? eh whatevs :/)

XXX: maxlinelen is a bit weird, i know. it would probably make sense
30+ years ago (had i been born then?) but now it probably just feels
like confusing math

.. toctree::
   :maxdepth: 1
   :caption: Modules

   encoders.rst
   decoders.rst
