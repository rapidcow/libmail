==============================================================
:mod:`rdks.mail.headers` --- RFC 822 header parser & formatter
==============================================================

.. module:: rdks.mail.headers
   :synopsis: RFC 822 header parser & formatter

when people talk about RFC 822 messages (e.g. the MIME media type
``message/rfc822``) they usually mean more than just the RFC itself.
they also mean its successors, RFC 2822, RFC 5322 (with the intention
of updating and replacing it), as well as the extensions specified in
RFC 2045 through 2049, RFC 2183, RFC 2231, ...

the main focus of this package (if it gets to be completed) will be
the 822 lineage, which specifies the overall format and defines several
important headers. (the "container" of email messages, so to speak.)

of course, this is all just theoretical work. in reality, a parser that
fully implements RFC 822 is hardly ever heard of, and more often than not
email clients just flat-out violate it! so, if what you are after is
a robust, well-tested library that.... this is not the place!
(which you can tell, already, from the immaturity of this project,
and i probably didn't have to tell you that...)

.. toctree::
   :maxdepth: 1
   :caption: Modules

   tokens.rst
   parser.rst
   format.rst
