======================
how to get dis package
======================

i didn't put this on pypi, or github, so you will have to
just... clone the Git repo, and install with pip:

.. code-block:: sh

   git clone https://git.rapidcow.org/rdks-mail.git
   python3 -m pip install ./rdks-mail
   # now you can safely delete rdks-mail

and the command you use to uninstall, in case you installed in
a wrong environment or just simply want to uninstall, is:

.. code-block:: sh

   # same name, sans "./"
   python3 -m pip uninstall rdks-mail

pip, being the dastard guy it is, can also do the install step
in one command:

.. code-block:: sh

   python3 -m pip install git+https://git.rapidcow.org/rdks-mail.git

if you are after compose.py there is an additional rdks-list
thingy you have to install, so repeat the whole thing except with
``list`` this time

(more info in the `README`_ file)

.. _`README`: https://git.rapidcow.org/rdks-mail/about/


license for code
----------------

GPLv3+ for everything i wrote. that means it's free though must
not be bought into proprietary hands. see the `LICENSE`_ and `COPYING`_
files in my repo for the, eh, jargon

.. _LICENSE: https://git.rapidcow.org/rdks-mail/tree/LICENSE
.. _COPYING: https://git.rapidcow.org/rdks-mail/tree/COPYING
