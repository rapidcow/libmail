#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose.py - ethan's non-email client -.-

i'll write about the syntax later but *yawn*
rn i need to send emails with this

copyright (c) 2024  Ethan Meng (rapidcow)
compose.py is part of rdks-mail, licensed under GPLv3+:
<https://git.rapidcow.org/rdks-mail/about/>

compose.py is free software: you may redistribute it and/or
modify it under the terms of GNU GPL version 3 or above.
to get one such license for reference, see
<https://www.gnu.org/licenses/>.
there is NO WARRANTY, to the extent permitted by law.
"""

import email.message
import email.parser
from email.policy import EmailPolicy
import email.generator
import smtplib

import re
import itertools
import string

import argparse
import contextlib
import logging
import io
import os
import sys

import rdks.list
import rdks.mail.content as mime
import rdks.mail.contrib.contentmanager
import rdks.mail.contrib.headerregistry

SHORTNAMES = {
    'NOTSET': 'NULL',
    # 'DEBUG': 'DEBUG',
    # 'INFO': 'INFO'
    'WARNING': 'WARN',
    # 'ERROR': 'ERROR',
    'CRITICAL': 'CRIT',
}

class AbbrevFormatter(logging.Formatter):
    def format(self, record):
        record.levelname = SHORTNAMES.get(record.levelname, record.levelname)
        return super().format(record)

logger = logging.getLogger(__name__)
formatter = AbbrevFormatter('[%(levelname)5s] %(filename)s:%(lineno)03d %(message)s')
console = logging.StreamHandler(sys.stderr)
console.setFormatter(formatter)
logger.addHandler(console)

logger.setLevel(logging.WARNING)
console.setLevel(logging.DEBUG)

class TemperamentalBoolean(object):
    """i might be a bool.... but sometimes i'd FEEL otherwise >:)"""
    def __init_subclass__(cls):
        super().__init_subclass__()
        cls._registry = {}

    def __new__(cls, value):
        truth = bool(value)
        try:
            return cls._registry[truth]
        except KeyError:
            cls._registry[truth] = super().__new__(cls)
            return cls._registry[truth]

    def __init__(self, value):
        self._truth = bool(value)

    def __str__(self):
        return ('no', 'on')[self._truth]

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self._truth)

    def __bool__(self):
        return self._truth

    def __index__(self):
        return self._truth.__index__()

    def __eq__(self, other):
        return other is self._truth or super().__eq__(other)

class Maybe(TemperamentalBoolean):
    """yes, no, maybe so"""

class MustBe(TemperamentalBoolean):
    """must have been the wind"""

__author__ = 'Ethan Y. Meng :3'
__version__ = '0.0'
__all__ = ['main']

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=(
            'create electronic mail, optionally set options '
            'according to ESMTP capabilities'
        )
    )
    parser.add_argument('--version', '-V', action='version',
                        version='%%(prog)s %s' % __version__)
    parser.add_argument('--cwd', '-C', metavar='PATH', default=None,
                        help='base directory (default: $PWD), or '
                        'parent directory of the message config')
    # input/output
    parser.add_argument('message', nargs='?', default='-',
                        help='file to read message config from (default :-)')
    parser.add_argument('--output', '-o', metavar='FILE', default='-',
                        help='file to write the message to (default :-)')
    parser.add_argument('--overwrite', '-y', action='store_true',
                        help='always write to output even if it exists')
    parser.add_argument('--save-options', '-s', metavar='FILE',
                        help='save global options to somewhere (optional)')
    # capabilities
    parser.add_argument('server', nargs='?', help='mail server host '
                        '(optional)')
    parser.add_argument('port', type=int, nargs='?', help='mail server port '
                        '(default: 25 for SMTP, 465 for SMTP SSL,'
                        ' 587 for STARTTLS)')
    parser.add_argument('--protocol', metavar='PROTO',
                        choices=('smtp', 'starttls', 'smtps'),
                        default='smtp', help='transport protocol ("smtp" for '
                        'plain SMTP (default), "smtps" for SSL, '
                        '"starttls" for STARTTLS)')
    # degree of annoyingness
    parser.add_argument('--strict', action='store_true',
                        help='raise error when weird stuff happens')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='disable logging; overrides -v')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='set log level (-v for INFO, -vv for DEBUG)')

    return _dispatch_instream(parser.parse_args(argv))

def _dispatch_instream(args):
    if args.message == '-':
        return _dispatch_outstream(sys.stdin.buffer, args)
    else:
        with open(args.message, 'rb') as infp:
            return _dispatch_outstream(infp, args)

def _dispatch_outstream(source, args):
    if args.output == '-':
        return _main(source, sys.stdout.buffer, args)
    else:
        mode = 'wb' if args.overwrite else 'xb'
        with open(args.output, mode) as outfp:
            return _main(source, outfp, args)

def _main(source, dest, args):
    if args.cwd is None:
        if args.message == '-':
            cwd = os.getcwd()
        else:
            cwd = os.path.dirname(os.path.abspath(args.message))
    else:
        if args.cwd == '.':
            cwd = os.getcwd()
        else:
            cwd = os.path.abspath(args.cwd)

    # logging :)
    if args.quiet:
        logger.disable(logging.CRITICAL)
    elif args.verbose > 1:
        logger.setLevel(logging.DEBUG)
    elif args.verbose > 0:
        logger.setLevel(logging.INFO)

    seen = set()
    raw_items = {
        'options': {
            'linesep': '\r\n', # CRLF. the Internet standard.
            # RFC 5321 2.1.1. RECOMMENDS 78 characters excluding CRLF
            # RFC 5322 4.5.3.1.6. defines a hard limit of 1000 chars
            'maxlinelen': 80,
            # we will set this later; this is indeed 1000 by default,
            # or 0 if we see one or more binary CTE.  if the user
            # sets a value themselves (or a new standard extends
            # this limit with an extension) we won't try to mess
            # with that.
            'smtpline': None,
            # ESMTP features/capabilities
            'smtpsize': 0, # unlimited
            'smtputf8': Maybe(False),
            '8bitmime': Maybe(False),
            'binarymime': Maybe(False),
            # in embedded documents such as multipart/signed we might
            # want to have canonicalizable headers; that is, NO MIME-
            # Version because we already know that!!!  but compose.py
            # doesn't know that, so you have to patiently tell it...
            'embedme': False,
        },
    }

    sourcefile = args.message if args.message != '-' else None
    with ConfigReader(sourcefile, cwd, source) as reader:
        for x in reader:
            if x.key not in {b'options', b'headers', b'content'}:
                raise reader.error(x.start.lineno,
                    'unrecognized name: %r', x.key)

            # oop! almost did this! =u=;
            field = x.key.decode('us-ascii')
            if field in seen:
                raise reader.error(x.start.lineno,
                    '%s may not be specified twice', field)
            seen.add(field)

            if field == 'options':
                _set_options(raw_items['options'], reader, x)
            else:
                raw_items[field] = x

        for field in 'headers', 'content':
            if field not in raw_items:
                raise ValueError('%s field not found' % (field,))

        message = _parse_headers(reader.get_content(
            raw_items['headers'], interpret_input=True),
            raw_items['options'], args.strict)
        done = False
        with contextlib.ExitStack() as s:
            for critter in (
                s.push(reader.inner_data_reader(
                    raw_items['content'], interpret_input=True)),
                s.push(reader.inner_rest_reader(
                    raw_items['content'], interpret_input=True)),
            ):
                if not done:
                    done = _set_content(
                        message, critter, raw_items['options'])
                if done:
                    try:
                        x = next(critter)
                    except StopIteration:
                        pass
                    else:
                        raise critter.error(
                            x.start.lineno, 'trailing content')

    o = raw_items['options']
    if args.server:
        _set_capabilities(o, args.server,
            args.port, args.protocol, args.verbose)
    if o['smtpline'] is None:
        o['smtpline'] = 1000
    if args.save_options:
        # those who use --save-options should know its consequences.
        # i'm just gonna be extra harsh and always overwrite stuff
        with open(args.save_options, 'w', encoding='us-ascii') as fp:
            fp.write('# this file contains options computed ' + (
                     'for %r' % (args.message,)
                     if args.message != '-' else 'from stdin'))
            if args.server:
                fp.write(',\n# catered to the smtp server %s'
                         % (args.server,))
                if args.port:
                    fp.write(' on port %d' % (args.port,))
            fp.write('.\n')
            w = rdks.list.writer(fp, text=True)
            for k, v in o.items():
                if isinstance(v, bool):
                    w.write(k, ('no', 'on')[v])
                else:
                    w.write(k, ELPAM[v] if k == 'linesep' else str(v))

    if message.get_content_type() == 'multipart/signed':
        # Generator uses a special handler for multipart/signed
        # that forcibly unsets any max_line_length.  We made the
        # outer part, so wrap it (as it'd be silly to not wrap
        # something that the user has no control over....)
        payload = message.get_payload()
        # We're a little type agonistic, so make sure we can
        # do this at all first.
        if isinstance(payload, list):
            payload = list(map(_force_wrap_header, payload))
            message.set_payload(payload)

    gen = email.generator.BytesGenerator(
        WatchDog(dest, o, args.strict, args.quiet))
    gen.flatten(message)

def _force_wrap_header(message):
    # Steal the header-value pair from EmailMessage as a multimap.
    # Says that this is internal API, but I don't care :)
    multimap = message.raw_items()
    # Present as in "wrapped", get it?  No... eh whatever >_>
    present = type(message)(policy=message.policy)
    for header, value in multimap:
        headervalue = message.policy.fold(header, value)
        parser = email.parser.HeaderParser(policy=message.policy)
        parsed = parser.parsestr(headervalue)
        # WAIT i've used this before XD never mind
        (_, headervalue), = parsed.raw_items()
        present.set_raw(header, headervalue)
    present.set_payload(message.get_payload())
    return present

def _set_capabilities(options, server, port, protocol, verbose):
    if port is None:
        # wait... is it the other way around?
        # https://serverfault.com/a/1065151
        port = {'smtp': 25, 'smtps': 465, 'starttls': 587}[protocol]

    def _set_features(features):
        if 'size' in features:
            cap = int(features['size'])
            # hard limit always wins, unless the original size
            # is even more restrictive
            if options['smtpsize']:
                options['smtpsize'] = min(options['smtpsize'], cap)
            else:
                options['smtpsize'] = cap
        for name in {'smtputf8', '8bitmime', 'binarymime'}:
            given = options[name]
            if given and given is not MustBe(True):
                options[name] = name in features
            elif not given and given is Maybe(False):
                options[name] = name in features

    if protocol in ('smtp', 'starttls'):
        with smtplib.SMTP(server, port) as conn:
            conn.set_debuglevel(verbose)
            if protocol == 'starttls':
                conn.starttls()
            conn.ehlo_or_helo_if_needed()
            _set_features(conn.esmtp_features)
    else:
        with smtplib.SMTP_SSL(server, port) as conn:
            conn.set_debuglevel(verbose)
            conn.ehlo_or_helo_if_needed()
            _set_features(conn.esmtp_features)

    return options

class ValidationWarning(UserWarning):
    """the emil did not pass da vibe check :("""
    pass

class WatchDog:
    """file object wrapper that haunts you at night"""

    def __init__(self, wrappee, options, strict, quiet):
        self._fp = wrappee
        self._eol = options['linesep'].encode('us-ascii')
        self._lineno = 0
        self._lindex = 0
        self._charno = 0
        self._maxlen = options['smtpline']
        self._maxsiz = options['smtpsize']
        self._8bit = options['8bitmime'] or options['binarymime']
        self._strict = strict
        self._quiet = quiet

    def _bad(self, msg, off=0):
        full = 'line %d, char %d (byte %d): %s' % (
            self._lineno + 1, self._lindex + 1 + off,
            self._charno + 1 + off, msg,
        )
        if not self._quiet:
            if self._strict:
                raise ValidationWarning(full)
            import warnings
            warnings.warn(full, ValidationWarning)

    def write(self, value):
        i = 0
        j = 0
        n = len(value)
        while i < n:
            try:
                j = value.index(self._eol, i) + len(self._eol)
                eol = True
            except ValueError:
                j = n
                eol = False
            if self._maxlen and j - i + self._lindex > self._maxlen:
                # XXX: there may be multiple line exceeded warnings
                # if one line is written with multiple calls to write()?
                violation = self._maxlen - self._lindex + 1
                self._bad('line limit exceeded', self._maxlen + 1)
            if self._maxsiz and j - i + self._charno > self._maxsiz:
                violation = self._maxsiz - self._charno + 1
                self._bad('message size limit exceeded', violation)
                self._maxsiz = 0  # total size warning should be issued once
            # XXX XXX: this is probably ridiculously slow
            # but i want accurate char position so :ccccc
            for k, b in enumerate(value[i:j]):
                if not self._8bit and b & 0x80:
                    self._bad('8th bit present when neither 8bitmime '
                              'nor binarymime is set', k)
            self._lineno += 1
            self._charno += j - i
            if eol:
                self._lindex = 0
            else:
                self._lindex += j - i
            self._fp.write(value[i:j])
            i = j
        assert i == n

# maple <- mapeol <= map EOL
# note: we allow CR simply because that goes with
# python's universal newline; i am personally in no favor
# for it (at least \n moves the cursor down! cr just brings
# it to the beginning and writes over everything!)
MAPLE = {b'LF': '\n', b'CRLF': '\r\n', b'CR': '\r'}
ELPAM = {v: k.upper().decode('us-ascii') for k, v in MAPLE.items()}
# mable <- mapble <- map boolean
# (doesn't have do with mabel o o)
MABLE = {
    # note: most of these are jokes, the only sensible ones are
    #   ON: true ok yes on good
    #   NO: false no off bad
    #   ON? true? ok? maybe good? on? hopefully
    #   NO? false? no? maybe... maybe not. bad? off? probably
    #   ON! true! ok! yes! good! on! absolutely! yippee!
    #   NO! false! no! bad! off! absolutely not! never!
    # the rest are for funsies
    b'true': True, b'false': False, b'ok': True,
    b'true!': MustBe(True), b'false!': MustBe(False), b'ok!': MustBe(True),
    b'true?': Maybe(True), b'false?': Maybe(False), b'ok?': Maybe(True),
    b'yes': True, b'no': False, b'maybe': Maybe(True),
    b'yes!': True, b'no!': False, b'maybe...': Maybe(False),
    b'yes?': Maybe(True), b'no?': Maybe(False), b'maybe?': Maybe(True),
    b'good': True, b'bad': False, b'good?': Maybe(True), b'bad?': False,
    b'good!': MustBe(True), b'bad!': MustBe(False),
    b'yes?': Maybe(True), b'no?': Maybe(False), b'maybe?': Maybe(True),
    b'on': True, b'off': False, b'on!': MustBe(True), b'off!': MustBe(False),
    b'on?': Maybe(True), b'off?': Maybe(False), b'maybe not': Maybe(False),
    b'hopefully': Maybe(True), b'probably': Maybe(False),
    b'absolutely!': MustBe(True), b'absolutely not!': MustBe(False),
    b'yippee!': MustBe(True), b'waaaaegh!': MustBe(False),
    b'please': MustBe(True),
    b'please!': MustBe(True), b'never!': MustBe(False),
    # english 2.0 (with an uncapitalized e for jokes)
    b"yesn't": False, b'perchance': Maybe(False), b"s'pose": Maybe(True),
    # you already know this is a joke didn't you
    '🉑'.encode('utf-8'): True,  # permissible
    '👌'.encode('utf-8'): True,  # OK
    '👍'.encode('utf-8'): True,  # thumbs up
    '👎'.encode('utf-8'): False, # thumbs down
    # tip: use the android blob emoji font to tell them apart
    '😆'.encode('utf-8'): MustBe(True),   b':D': MustBe(True),
    '🙂'.encode('utf-8'): True,           b':)': True,
    '😕'.encode('utf-8'): Maybe(True),    b':/': Maybe(True),
    '😐'.encode('utf-8'): Maybe(False),   b':|': Maybe(False),
    '😶'.encode('utf-8'): Maybe(False),   b': ': Maybe(False),
    '🙁'.encode('utf-8'): False,          b':(': False,
    '😡'.encode('utf-8'): MustBe(False), b'>:(': MustBe(False),
    # for no reason whatsoever let's throw in a kaomoji too
    '┐(￣。￣)┌'.encode('utf-8'): Maybe(False),
}

def _set_options(options, r, x):
    valid = {name.encode('us-ascii') for name in options}
    seen = set()
    def _check_redundancy(yippee):
        key = yippee.key.lower()
        if key in seen:
            raise reader.error(_begin_lineno(yippee.start.lineno),
                               'duplicate key: %r', yippee.key)
        seen.add(key)

    with contextlib.ExitStack() as s:
        for reader in (
            s.push(r.inner_data_reader(x)),
            s.push(r.inner_rest_reader(x)),
        ):
            for pair in reader:
                if pair.key.lower() not in valid:
                    raise reader.error(_begin_lineno(pair),
                                       'unknown option: %r', pair.key)
                _check_redundancy(pair)
                content = _chomp(pair.content)
                field = pair.key.lower().decode('us-ascii')
                if field in {'maxlinelen', 'smtpline', 'smtpsize'}:
                    value = int(content.decode())
                elif field == 'linesep':
                    name = _chomp(pair.content).upper()
                    try:
                        value = MAPLE[name]
                    except KeyError:
                        raise reader.error(_begin_lineno(pair),
                            'invalid linesep: %r', name) from None
                elif field in {'smtputf8', '8bitmime', 'binarymime', 'embedme', 'embed'}:
                    name = _chomp(pair.content).lower()
                    try:
                        value = MABLE[name]
                    except KeyError:
                        raise reader.error(_begin_lineno(pair),
                            'invalid boolean: %r', name) from None
                    if field == 'embed':
                        field = 'embedme'
                options[field] = value

class MyEmailPolicy(EmailPolicy):
    def header_store_parse(self, name, value):
        # XXX: this is very bad, but I don't want Python
        # to re-encode my already MIME-encoded strings :(
        return (name, value)

def _parse_headers(headers, o, strict):
    policy = MyEmailPolicy(
        # my stuff >:)
        content_manager = rdks.mail.contrib.contentmanager.ContentManager(),
        header_factory  = rdks.mail.contrib.headerregistry.HeaderRegistry(),
        # EmailPolicy stuff
        max_line_length = (max(1, o['maxlinelen'] - len(o['linesep']))
                            if o['maxlinelen'] else 0),
        linesep         = o['linesep'],
        utf8            = o['smtputf8'],
        cte_type        = ('8bit' if o['8bitmime'] or
                            o['binarymime'] else '7bit'),
        raise_on_defect = strict,
        # need this for our new fold function to see the headers :)
        # XXX: turning this off for now...
        refold_source   = 'long',
    )
    parser = email.parser.BytesHeaderParser(policy=policy)
    return parser.parsebytes(headers)

def _set_content(message, reader, o):
    try:
        root = next(reader)
    except StopIteration:
        return False
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            'SET_CONTENT from %s:%02d %+03d-[%02d]-%02d '
            'key=%r data=%s (%s/./%s) rest=[%s line%s]',
            reader._file, reader._lineno + 1,
            root.start.lineno, root.middle.lineno, root.end.lineno,
            root.key, _shorten(root.data, 69),
            root.input_root, root.input_file,
            len(root.rest), 's' * (len(root.rest) != 1),
        )
    # "O, embed me, will you..."
    if not o['embedme']:
        message['MIME-Version'] = '1.0'
    _set_content_from_node(message, reader, root, o, outer=True)

PARAMHEAD_VERBS = {b'with', b'where'}
BASICPART_VERBS = PARAMHEAD_VERBS | {b'of'}
MULTIPART_VERBS = BASICPART_VERBS | {b'preamble', b'epilogue', b'including'}

def _set_content_from_node(message, reader, root, o, outer=False):
    mimetype = root.key.decode('us-ascii')
    message['Content-Type'] = mimetype
    multipart = False
    parts = []
    charset = None
    encoding = None
    boundary = None
    # encoding params
    eparams = {}
    reeder = reader.inner_rest_reader(root, interpret_input=True)
    for pair in reeder:
        # calling data has side effects so we postpone that
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                'read from %s:%02d %+03d-[%02d]-%02d '
                'key=%r data=%s (%s/./%s) rest=[%s line%s]',
                reader._file, reader._lineno + 1,
                pair.start.lineno, pair.middle.lineno, pair.end.lineno,
                pair.key, _shorten(pair.data, 69),
                pair.input_root, pair.input_file,
                len(pair.rest), 's' * (len(pair.rest) != 1),
            )
        key = pair.key.lower()
        if key not in MULTIPART_VERBS:
            raise reeder.error(_begin_lineno(pair),
                'unrecognized verb: %r', pair.key)
        if key == b'preamble':
            # we actually need to set these to strings...
            message.preamble = pair.content.decode('utf-8')
        elif key == b'epilogue':
            message.epilogue = pair.content.decode('utf-8')
        elif key == b'with':
            param, value = _set_param(message, 'Content-Type', 'type', reeder, pair)
            if param.lower() == 'boundary':
                boundary = value
        elif key == b'of':
            header, value, params = _set_header(message, reeder, pair, o)
            hlower = header.lower()
            if hlower == 'content-transfer-encoding':
                encoding = message[header]
                eparams = params
                logger.debug('got params %r for cte %r', params, encoding)
                # if the user uses the binary CTE, they probably
                # know what they are doing (with BINARYMIME and all)
                if encoding == 'binary' and o['smtpline'] is None:
                    o['smtpline'] = 0
        elif key == b'including':
            multipart = True
            if pair.data is not None:
                raise reeder.error(_begin_lineno(pair),
                    'data is invalid in subparts ("including")')
            reindeer = reeder.inner_rest_reader(pair, interpret_input=True)
            message.set_payload([])
            for pear in reindeer:
                # print('RECURSING!!!!!')
                # print('from', reindeer._lineno + 1, '+', pear.start,
                #       '=', reindeer._lineno + pear.start.lineno + 1)
                # print('pear', pear)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        'SUBPART for %s: %s:%02d %+03d-[%02d]-%02d '
                        'key=%r data=%s (%s/./%s) rest=[%s line%s]',
                        mimetype, reindeer._file, reindeer._lineno,
                        pear.start.lineno,
                        pear.middle.lineno,
                        pear.end.lineno,
                        pear.key, _shorten(pear.data, 69),
                        pear.input_root, pear.input_file,
                        len(pear.rest), 's' * (len(pear.rest) != 1),
                    )
                part = type(message)(message.policy)
                _set_content_from_node(part, reindeer, pear, o)
                message.attach(part)

    truetype = message.get_content_type()
    charset = message.get_param('charset', None)
    if not multipart:
        if root.data is None:
            raise reader.error(root.start.lineno,
                'non-multipart messages must have input data')
        if mimetype.startswith("multipart/") and boundary is None:
            reader.error(_begin_lineno(root),
                "you must know your boundary if you are providing "
                "your own multipart message; i'm not playing dice "
                "game with you today")
        eol = eparams['linesep'] = o['linesep'].encode('ascii')
        eparams.setdefault('maxlinelen', o['maxlinelen'])
        # translate EOL for all inline text strings
        do_treol = eparams.pop('treol', not root.has_input() and
                               truetype.startswith('text/'))
        logger.debug('do_treol = %r for content of type %s',
                     do_treol, truetype)
        data = mime.treol(root.data, eol) if do_treol else root.data
        if mimetype.startswith('multipart/') and encoding is not None:
            raise reader.error(root.start.lineno,
                'encoding is not a thing for multipart messages')

        if encoding == 'quoted-printable':
            # don't set embed and let encode_qp() figure it out
            # it'd be more interesting to pretend that this argument
            # behaves precisely like binary=None in binascii.b2a_qp(),
            # but well.... :)
            eparams.setdefault('wrap', truetype.startswith('text/'))
            eparams.setdefault('protect', outer)
            logger.info('encode %s content with QP using params %r',
                         truetype, eparams)
            try:
                payload = mime.encode_qp(data, **eparams)
            except mime.EncodingError as e:
                raise reader.error(root.start.lineno,
                    'failed to encode QP') from e
        elif encoding == 'base64':
            chunked = o['maxlinelen'] // 4 * 4
            eparams.setdefault('maxlinelen', max(len(eol), chunked))
            # to make implementors' lives easier, tell them where
            # the final line ends by default...
            # ... except in multiparts, that way we "save" two bytes
            # and it makes my ass happy for no reason >:D
            chomp = eparams.pop('chomp', not outer)
            logger.info('encode %s content with base64 using params %r',
                        truetype, eparams)
            try:
                payload = mime.encode_base64(data, **eparams)
            except mime.EncodingError:
                raise reader.error(root.start.lineno,
                    'failed to encode base64') from e
            if not chomp:
                payload += eol
        elif encoding in {'7bit', '8bit'}:
            try:
                payload = mime.encode_verbatim(data, **eparams)
            except mime.EncodingError as e:
                raise reader.error(root.start.lineno,
                    'failed to validate %s', encoding) from e
            errors = 'surrogateescape' if encoding == '8bit' else 'strict'
            try:
                payload = root.data.decode('us-ascii', errors)
            except UnicodeDecodeError as e:
                # surrogateescape should never fail.
                # if it does it probably was something that claimed
                # to be 7bit (ascii) yet contains nonzero 8th bit
                raise reader.error(_begin_lineno(root),
                    'invalid %s content', encoding) from e
        # otherwise we'll just pray that the input HAS been encoded... lol XD
        # (jk i just dont know what to do)
        else:
            if encoding is None:
                reader.error(_begin_lineno(root),
                    "please do not omit content transfer encoding... "
                    "even a 7bit will do if you are just writing ASCII q.q "
                    "(or even \"secretly 7bit\" if you don't want people "
                    "to see the CTE header...)")
            elif encoding != 'binary':
                logger.warning('dunno what CTE %r is. pretending it is '
                               'encoded already and fingers-crossed '
                               'hoping for the best', encoding)
            payload = root.data.decode('us-ascii', 'surrogateescape')
        message.set_payload(payload)

    return True

def _set_param(message, header, name, reader, pair):
    if header.lower() == 'content-type':
        verb = '"with" for Content-Type'
    else:
        verb = '"with" for %s (%s)' % (header, name)

    # syntactically this makes no sense
    # since we only want one line
    if pair.hanging:
        raise reader.error(pair.start.lineno,
            'hanging indent is not allowed in a '
            '%s parameter (%s)', header, verb)
    if pair.data is not None:
        raise reader.error(pair.start.lineno,
            'input string is invalid in a %s parameter (%s)',
            header, verb)
    reeder = reader.inner_rest_reader(pair, interpret_input=True)

    # xxx: i'm too lazy to do this now, let the stop iteration
    # error and stuff propogate...
    pear = next(reeder)
    # allow use of syntax like with creation-date < path/to/btime
    data = pear.content
    if not (pear.key and data):
        raise reader.error(pair.start.lineno,
            'missing param and/or value in %s parameters (%s)',
            header, verb)

    param = pear.key.decode('us-ascii')
    value = data.decode('utf-8')

    try:
        nextpear = next(reeder)
    except StopIteration:
        if param == 'boundary':
            message.set_boundary(value)
        else:
            message.set_param(param, value, header=header)
    else:
        raise reeder.error(nextpear.start.lineno, 'extraneous line')

    return param, value

NAME2MIME_MAP = {
    # RFC 2045 (MIME Part One)
    'version':     'MIME-Version',
    'type':        'Content-Type',
    'encoding':    'Content-Transfer-Encoding',
    'disposition': 'Content-Disposition',
    'id':          'Content-ID',
    'description': 'Content-Description',
    # RFC 3066 + RFC 3282
    'language':    'Content-Language',
    # RFC 2076 (non-standard)
    'base':        'Content-Base',
    'location':    'Content-Location',
}

def _set_header(message, reader, pair, o):
    # xxx xxx: same here.
    if pair.hanging:
        raise reader.error(pair.start.lineno,
            'hanging indent is not allowed in a mime header ("of")')
    if pair.data is not None:
        raise reader.error(pair.start.lineno,
            'data is invalid in a mime header ("of")')
    reeder = reader.inner_rest_reader(pair, interpret_input=True)
    pear = next(reeder)
    body = pear.data or pear.value
    if not (pear.key and body):
        # breakpoint()
        raise reader.error(pair.start.lineno,
            'missing header and/or value in a mime header ("of"): %r',
            (pear.key, pear.value))

    name = pear.key.decode('us-ascii').lower()
    value = pear.value.decode('utf-8')
    try:
        header = NAME2MIME_MAP[name]
    except KeyError:
        raise reader.error(pair.start.lineno,
            'unknown content header name: %r', name)

    # encoding "secretly-" is a special trick...
    # All options (if any) still apply, but it won't appear
    # in the email itself.  Might be really useful for RFC3156
    # (MIME/OpenPGP)....
    if name == "encoding" and value in {"secretly 7bit", "secretly 8bit"}:
        value = value[9:]  # strip "secretly-" prefix
    else:
        # XXX: do unstructured headers with unicode actually work?
        body_str = body.decode('utf-8')
        # we don't want trailing CR/LF... sorry :(
        body_lines = body_str.rstrip('\r\n').splitlines()
        # continuation character should be CRLF + space...?
        body_text = (o['linesep'] + ' ').join(body_lines)
        if body_lines and body_lines[0]:
            body_text = ' ' + body_text
        parser = email.parser.HeaderParser(policy=message.policy)
        parsed = parser.parsestr(header + ':' + body_text)
        # nasty unpacking o_o;
        (_, headervalue), = parsed.raw_items()
        if name != 'description':
            del message[header]
        message.set_raw(header, headervalue)

    pyparams = {}
    for pear in reeder:
        # logger.debug('ELKY THE MOOSE HAS %s IN HIS EYeS', pear)
        logger.debug('header param for %s (%s): %r', header, name, pear)
        if pear.key not in PARAMHEAD_VERBS:
            raise reeder.error(pear.start.lineno,
                 'not a valid parameter for header '
                 '%s: %r', header, pear.key)
        if pear.key == b'with':
            _set_param(message, header, name, reeder, pear)
        else:
            assert pear.key == b'where', pear.key
            _set_pyparam(pyparams, name, header, value, reeder, pear, o)

    return header, value, pyparams

def _set_pyparam(store, name, header, value, reader, pair, o):
    # XXX XXX: copy and paste for the moment...
    if pair.hanging:
        raise reader.error(pair.start.lineno + 1,
            'hanging indent is not allowed in a '
            '%s custom parameter ("where" for %s)',
            header, name)

    if len(pair.rest) > 1:
        reader.error(pair.middle.lineno + 1, 'extraneous line')
    todo = pair.rest[0].split(b',')

    if name == 'encoding':
        ivalid = {b'maxlinelen'}
        bvalid = {b'treol'}
        special = set()
        vlower = value.lower()

        if vlower == 'quoted-printable':
            bvalid.add(b'wrap')
            special.add(b'embed')
            bvalid.add(b'protect')
        elif vlower == 'base64':
            bvalid.add(b'chomp')

        for item in todo:
            # NOTE: we are splitting the param ourselves so
            # things may look a bit weird here
            # (i could have added an option that lets you
            #  change the delimiter; but then idk if that'll
            #  make for code any less nightmarish than this)
            key_ws, val_ws = item.split(b'=', maxsplit=1)
            key = _skipleft(_skipright(key_ws))
            val = _skipright(_skipleft(val_ws))
            if not (key and val):
                raise reader.error(pair.middle.lineno,
                    'missing param and/or value in a '
                    '%s custom parameter ("where" for %s)',
                    header, name)

            klower = key.lower()
            try:
                dupe = next(k for k in store if key == k.encode('us-ascii'))
            except StopIteration:
                pass
            else:
                raise reader.error(pair.start.lineno,
                    'duplicate key: %r', dupe)

            if klower not in ivalid | bvalid | special:
                raise reader.error(pair.middle.lineno,
                                   '%r is not a valid key (candidates '
                                   'for the %s encoding include %r)',
                                   key, value, ivalid | bvalid | special)

            if klower in ivalid:
                number = int(val.strip().decode('us-ascii'))
                if pair.key == b'maxlinelen':
                    if o['smtpline'] and number > o['smtpline']:
                        raise reader.error(pair.middle.lineno,
                            'line limit for content encoding '
                            'exceeds line limit imposed on the '
                            'whole message (%d > %d)',
                            number, o['smtpline'])
                store[klower.decode('us-ascii')] = number
            elif klower in bvalid:
                # XXX copied again
                try:
                    store[klower.decode('us-ascii')] = MABLE[val.lower()]
                except KeyError as e:
                    raise reader.error(pair.start.lineno,
                        'invalid boolean: %r', val) from e
            elif klower in special:
                assert klower == b'embed'
                # true (all) false (line) (none)
                try:
                    store[klower.decode('us-ascii')] = \
                        ('line', 'all')[MABLE[val.lower()]]
                except KeyError as e:
                    store[klower.decode('us-ascii')] = \
                        val.lower().decode('us-ascii')

    else:
        raise reader.error(pair.start.lineno, '%s header does not have '
            'any configurable options at the moment', name)

def _skipleft(b):
    return b[1:] if b.startswith(b' ') else b

def _skipright(b):
    return b[:-1] if b.endswith(b' ') else b

def _patch(lines):
    copy = list(lines)
    if lines:
        copy[-1] += b'\n'
    return copy

def _chomp(ln):
    return ln[:-1] if ln.endswith(b'\n') else ln

# a DEBUG UTILITY:
def _shorten(b, maxbytes):
    if b is None or len(b) <= maxbytes + 5:
        return repr(b)
    omit = len(b) - maxbytes + 5
    omits = 's' * (omit != 1)
    return '%r [... %d byte%s]' % (b[:maxbytes - 5], omit, omits)

# TODO: deal with the case of bare keys
# this is the only exception to pair.start.lineno +
# pair.hanging, but there are too many places to change...
def _begin_lineno(pair):
    start = pair.start.lineno
    if pair.hanging and pair.value is not None:
        start += 1
    return start

# slightly different; this skips over data
# (the < file line or the << ... block)
def _first_lineno(pair):
    return pair.middle.lineno

class Error(ValueError):
    def __str__(self):
        lines = super().__str__().splitlines(keepends=True)
        return '\n' + ''.join('  ' + ln for ln in lines)

class ConfigNode(rdks.list.node):
    def __new__(cls, *args, cwd=None, file=None, data=None, rest=None,
                middle=None, **kwds):
        self = super().__new__(cls, *args, **kwds)
        self._input_root = cwd
        self._input_from = file
        self._input_data = data
        self._rest = rest
        self._loaded = False
        self._middle = middle
        return self

    # XXX: hackish? but i wrote the code so :L
    def __repr__(self):
        base = super().__repr__()
        additions = []
        if self._input_root is not None:
            additions.append(('cwd', self._input_root))
        if self._input_from is not None:
            additions.append(('file', self._input_from))
        if not self._loaded and self._input_data is not None:
            additions.append(('data', self._input_data))
        if self._rest is not None:
            additions.append(('rest', self._rest))
        if self._middle is not None:
            additions.append(('middle', self._middle))
        extras = ''.join(', %s=%r' % arg for arg in additions)
        return base[:-1] + extras + base[-1]

    @property
    def input_root(self):
        return self._input_root

    @property
    def input_file(self):
        return self._input_from

    @property
    def input_path(self):
        return os.path.join(self._input_root, self._input_from)

    def has_input(self):
        if self._input_root is None:
            return False
        if self._loaded:
            return True
        return self._input_from is not None

    def input_stream(self):
        if not self.has_input():
            raise ValueError('this node does not input from anywhere')
        if self._input_data is not None:
            return io.BytesIO(self._input_data)
        if self._input_from is not None:
            return open(self.input_path, 'rb')
        assert 0 # this should be unreachable

    @property
    def data(self):
        if self.has_input():
            with self.input_stream() as fp:
                self._input_data = fp.read()
                self._loaded = True
        return self._input_data

    @property
    def content(self):
        return b''.join(itertools.chain([self.data or b''], self.rest))

    @property
    def rest(self):
        return self._rest

    @property
    def middle(self):
        return self._middle

INNER = object()

def _format_tb(info):
    # group inner tracebacks so that we don't look bad
    lines = []
    cwd = os.getcwd()
    sentinel = object()
    curr_root = None
    curr_file = None # probably shouldn't be printed
    curr_line = 0
    last_line = 0
    last = [(None, sentinel, None)]
    for root, file, lineno in itertools.chain(info, last):
        if file is not INNER:
            if curr_line:
                lines.append(
                    ('in file %r, line %d:\n'
                        % (curr_file, curr_line))
                    if curr_line == last_line else
                    ('in file %r, lines %d-%d:\n'
                        % (curr_file, curr_line, last_line))
                )
                try:
                    with open(os.path.join(curr_root, curr_file), 'rb') as fp:
                        for line in b''.join(itertools.islice(
                            fp, curr_line - 1, last_line)).splitlines():
                                trunc = line[:76].decode('utf-8', 'replace')
                                lines.append('  ' + trunc + '\n')
                except Exception:
                    pass
            if file is sentinel:
                break
            file = os.path.relpath(os.path.join(root, file), cwd)
            lines.append('in file %r, line %d:\n' % (file, lineno + 1))
            try:
                with open(os.path.join(root, file), 'rb') as fp:
                    for line in b''.join(itertools.islice(
                        fp, lineno, lineno + 1)).splitlines():
                        trunc = line[:76].decode('utf-8', 'replace')
                        lines.append('  ' + trunc + '\n')
            except Exception:
                pass
            curr_root = root
            curr_file = file
            curr_line = 0
            last_line = 0
        else:
            if not curr_line:
                curr_line = lineno + 1
            last_line = max(last_line, lineno + 1)
    return ''.join(lines)

# you can probably escape specials like ${#}?

class ConfigTemplate(string.Template):
    idpattern = r'(?a:[A-Za-z_][0-9A-Za-z_]*)'
    braceidpattern = r'(?a:[A-Za-z_][0-9A-Za-z_]*|[#<>])'

def _subs(s):
    t = ConfigTemplate(s)
    return t.substitute({
        # escapes in case data input is interpreted
        '#':    '#', '<':    '<', '>':    '>',
        'hash': '#', 'less': '<', 'more': '>',
        'progname': 'compose.py', 'progversion': __version__,
    })

class ConfigReader:
    def __init__(self, file, cwd, lines=None, lineno=0,
                 tb=(), interpret_input=True, inner=False):
        self._file = file
        self._cwd = cwd
        self._lineno = lineno
        self._charno = 0 # XXX: not usable yet
        self._tb = tb
        if lines is not None:
            self._fp = None
        else:
            self._fp = lines = open(file, 'rb')
        self._reader = rdks.list.reader(lines, text=False, delim=b' ')
        self._do_input = interpret_input
        self._inner = inner
        self._lookahead = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if self._fp:
            self._fp.close()

    def __iter__(self):
        return self

    def _get_tb(self, lineno):
        this_tb = (self._cwd, INNER if self._inner else self._file, lineno)
        return list(itertools.chain(self._tb, [this_tb]))

    def error(self, lineno, something, *args):
        tb = _format_tb(self._get_tb(self._lineno + lineno))
        somethang = something % args if args else something
        return Error(''.join([tb, somethang]))

    def inner_reader(self, lines, lineno, *, interpret_input=False):
        tb = self._get_tb(self._lineno + lineno)
        return type(self)(self._file, self._cwd, lines, self._lineno + lineno,
                          tb, interpret_input, inner=True)

    def outer_reader(self, file, cwd, lineno, *, interpret_input=True):
        tb = self._get_tb(self._lineno + lineno)
        return type(self)(file, cwd, None, 0, tb, interpret_input)

    def _next_pair(self):
        if self._lookahead is None:
            return next(self._reader)
        pair = self._lookahead
        self._lookahead = None
        return pair

    def __next__(self):
        while True:
            pair = self._next_pair()
            if not (pair.key or pair.value):
                continue
            if not pair.key.startswith(b'#'):
                break
            if pair.value and (pair.hanging or b'\n' in pair.value):
                # we could look for comments chars that don't
                # start from the bottom, but this will do
                # (being stricter doesn't hurt)
                raise self.error(pair.start.lineno + 1, 'floating field')

        if not pair.key:
            raise self.error(pair.start.lineno, 'no field found')

        try:
            lines = pair.value.splitlines(keepends=True)
        except AttributeError:
            lines = []

        off_line = pair.start.lineno
        off_char = pair.start.charno + len(pair.key)

        if pair.hanging:
            off_line += 1
            if pair.value is not None:
                off_char += 1 + len(pair.indent)
        else:
            off_char += len(self._reader.delim)

        file = None
        data = None
        rest = lines
        # last two are only overridden for the case of
        # flat inline string (for doubly indented lists
        # which we would have no way of "indenting" the
        # first line)
        last = pair
        value = pair.value
        logger.debug('scanning for input in node(%r, %s)',
                     pair.key, _shorten(pair.value, 69))
        if (pair.key and pair.value and
            pair.value.startswith(b'<') and
            self._do_input):
            tokens = _chomp(lines[0]).split(b' ')
            logger.debug('(yep, it made it) %r', tokens)
            # for now i guess i will require people to write
            # field < input and not field (LF) (space) < input...
            if not pair.hanging and tokens[0] == b'<':
                file = b' '.join(tokens[1:]).rstrip(b'\r\n').decode('utf-8')
                try:
                    with open(os.path.join(self._cwd, file)):
                        pass
                except OSError as e:
                    raise self.error(pair.start.lineno,
                        'cannot input file %r', file) from e
                off_line += 1
                off_char += len(lines[0])
                data = None
                rest = lines[1:]
            elif tokens[0] == b'<<':
                file = self._file
                prefix = b' '.join(tokens[1:]).rstrip(b'\r\n')
                off_line += 1
                off_char += len(lines[0])
                rel_line = 1
                value_lines = []

                if len(lines) > 1:
                    # case of
                    #   HEADER << |
                    #     | BODY
                    #     | BODY
                    #     |
                    #     REST
                    #   ANOTHER-HEADER
                    #   ^^^^ (ground)
                    for rel_line, line in enumerate(lines[1:], 1):
                        # this condition is trivially satisfied when
                        # prefix is empty, making this... gobble up
                        # every line yeah
                        #logger.debug('line %d: %r', rel_line, line)
                        if not line.startswith(prefix):
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(
                                    'end of inline string prefixed with %r '
                                    'at on line %d in node(%r, %s)',
                                    prefix, rel_line, pair.key,
                                    _shorten(pair.value, 69))
                            rel_line -= 1
                            break
                        value_lines.append(_skipleft(line[len(prefix):]))
                        off_line += 1
                        # XXX: this is wrong because we are ignoring
                        # the outer indent this whole node resides in
                        off_char += len(pair.indent) + len(line)
                    else:
                        # note that aborting midway gives us a LF while
                        # terminating at the end does not, so if
                        # that's the case, add it back in.
                        value_lines.append(b'\n')
                        off_char += 1 # eol reader chomped off
                else:
                    # case of:
                    #   HEADER << |
                    #   | BODY
                    #   | BODY
                    #   |
                    #   (no rest)
                    #   ANOTHER-HEADER
                    #   ^^^^ (ground)
                    while True:
                        try:
                            peek = self._next_pair()
                        except StopIteration:
                            break
                        #logger.debug('line x: %r', peek)
                        if peek.value is None:
                            line = peek.key or b''
                        else:
                            line = self._reader.delim.join(peek)
                        if not line.startswith(prefix):
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(
                                    'end of inline string prefixed with %r '
                                    'encountered at node(%r, %s)',
                                    prefix, peek.key,
                                    _shorten(peek.value, 69))
                            self._lookahead = peek
                            break
                        # things should always come back to the ground
                        # if not starting with the prefix!
                        if b'\n' in line:
                            raise self.error(peek.start.lineno + 1,
                                'bad indent encountered while '
                                'scanning for inline string')
                        value_lines.append(_skipleft(line[len(prefix):]))
                        value_lines.append(b'\n')
                        value += line
                        last = peek

                data = _chomp(b''.join(value_lines))
                rest = lines[rel_line + 1:]

        return ConfigNode(
            pair.key, value,
            hanging=pair.hanging,
            indent=pair.indent,
            cwd=self._cwd, file=file,
            data=data, rest=rest,
            start=pair.start,
            middle=rdks.list.position(off_line, off_char),
            end=last.end,
        )

    def inner_data_reader(self, pair, **kwds):
        if pair.has_input():
            return self.outer_reader(
                pair.input_file, pair.input_root,
                self._lineno + pair.start.lineno, **kwds)
        if pair.data is None:
            lines = []
        else:
            lines = pair.data.splitlines(keepends=True)
        return self.inner_reader(_patch(lines),
                                 _begin_lineno(pair),
                                 **kwds)

    def inner_rest_reader(self, pair, **kwds):
        return self.inner_reader(_patch(pair.rest),
                                 _first_lineno(pair),
                                 **kwds)

    def get_rest(self, pair, **kwds):
        if not pair.rest:
            value = None
        else:
            with io.BytesIO() as tmp:
                writer = rdks.list.writer(tmp, text=False, delim=b' ')
                # name shadowing, pesky... >_>
                for pear in self.inner_rest_reader(pair, **kwds):
                    writer.writepair(pear.replace(value=pear.content))
                buff = _chomp(tmp.getvalue())
                value = _subs(buff.decode('utf-8')).encode('utf-8')
        return value

    def get_content(self, pair, **kwds):
        return b''.join([pair.data or b'',
                         self.get_rest(pair, **kwds) or b''])

if __name__ == '__main__':
    main()
