#!/usr/bin/env python3
# -*- coding: ascii -*-
# oh boy
# this bouta go crazy
"""ethan's non-email client -.-"""

import email.message
import email.parser
import email.policy
import smtplib

import argparse
import contextlib
import io
import itertools
import os
import re
import string
import sys

import rdks.list
from rdks.mail.mime.encoders import encode_qp as body_encode_qp
from rdks.mail.mime.encoders import encode_base64 as body_encode_64

__author__ = 'Ethan Meng <ethan@yizz.me>'
__version__ = '0.0'

def capabilities(server, port, protocol):
    if port is None:
        port = {'smtp': 25, 'starttls': 465, 'smtps': 587}[protocol]

    options = {}
    def _set_features(features):
        for name, arg in features.items():
            if name == 'size':
                options['smtpsize'] = int(arg)
            elif name in {'smtputf8', '8bitmime', 'binarymime'}:
                options[name] = True

    if protocol in ('smtp', 'starttls'):
        with smtplib.SMTP(server, port) as conn:
            if protocol == 'starttls':
                conn.starttls()
            conn.ehlo_or_helo_if_needed()
            _set_features(conn.esmtp_features)
    else:
        with smtplib.SMTP_SSL(server, port) as conn:
            conn.ehlo_or_helo_if_needed()
            _set_features(conn.esmtp_features)

    return options

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description='create electronic mail')
    parser.add_argument('--cwd', '-C', metavar='CWD', default=None)
    parser.add_argument('message')
    parser.add_argument('server', nargs='?')
    parser.add_argument('port', type=int, nargs='?')
    parser.add_argument('--protocol',
                        choices=('smtp', 'smtps', 'starttls'),
                        default='none')
    return _main(parser.parse_args(argv))

def _main(args):
    if args.cwd is None:
        cwd = os.path.dirname(os.path.abspath(args.message))
    else:
        cwd = os.path.abspath(args.cwd)

    seen = set()
    raw_items = {
        'options': {
            # These all involve the word "line"
            'maxlinelen': 998,
            'linesep': '\r\n', # CRLF
            # ESMTP capabilities
            'smtpsize': 0, # unlimited
            'smtputf8': False,
            '8bitmime': False,
            'binarymime': False,
        },
    }
    if args.server:
        options = capabilities(args.server, args.port, args.protocol)
        raw_items['options'].update(options)

    with ConfigReader(args.message, cwd) as reader:
        for x in reader:
            if x.key not in {b'options', b'headers', b'content'}:
                reader.error(x.start.lineno,
                    'unrecognized name: %r', x.key)

            field = x.key.decode()
            if field in seen:
                reader.error(x.start.lineno,
                    '%s may not be specified twice', field)
            seen.add(field)

            if field == 'options':
                _set_options(raw_items['options'], reader, x)
            else:
                raw_items[field] = x

        for field in 'headers', 'content':
            if field not in raw_items:
                raise ValueError('%s field not found' % (field,))

        o = raw_items['options']
        message = _parse_headers(reader.get_content(raw_items['headers']), o)
        print(message)
        done = False
        with contextlib.ExitStack() as s:
            for critter in (
                s.push(reader.inner_data_reader(raw_items['content'])),
                s.push(reader.inner_rest_reader(raw_items['content'])),
            ):
                if not done:
                    done = _set_content(message, critter, o)
                if done:
                    try:
                        x = next(critter)
                    except StopIteration:
                        pass
                    else:
                        critter.error(x.start.lineno, 'trailing content')


# maple <- mapeol <= map EOL
# note: we allow CR simply because that goes with
# python's universal newline; i am personally in no favor
# for it (at least \n moves the cursor down! cr just brings
# it to the beginning and writes over everything!)
MAPLE = {b'lf': '\n', b'crlf': '\r\n', b'cr': '\r'}
# (doesn't have do with mabel o o)
MABLE = {
    b'true': True, b'false': False, b'ok': True,
    b'yes': True, b'no': False, b'maybe': None,
    b'on': True, b'off': False, b"yesn't": False,
    b'enabled': True, b'disabled': False,
    b'\xf0\x9f\x89\x91': True,  # same but emoji
    b'\xf0\x9f\x91\x8c': True,  # OK
    b'\xf0\x9f\x91\x8d': True,  # thumbs up
    b'\xf0\x9f\x91\x8e': False, # thumbs down
}

def _set_options(options, r, x):
    valid = {name.encode('ascii') for name in options}
    # mable <- mapble <- map boolean

    seen = set()
    def _check_redundancy(pair):
        key = pair.key.lower()
        if key in seen:
            reader.error(pair.start.lineno,
                         'duplicate key: %r', pair.key)
        seen.add(key)

    with contextlib.ExitStack() as s:
        for reader in (
            s.push(r.inner_data_reader(x)),
            s.push(r.inner_rest_reader(x)),
        ):
            for pair in reader:
                if pair.key.lower() not in valid:
                    reader.error(pair.start.lineno,
                                 'unknown option: %r', pair.key)
                _check_redundancy(pair)
                content = _chomp(pair.content)
                field = pair.key.lower().decode('ascii')
                if field in {'maxlinelen', 'smtpsize'}:
                    value = int(content.decode())
                elif field == 'linesep':
                    name = _chomp(pair.content).lower()
                    try:
                        value = MAPLE[name]
                    except KeyError:
                        reader.error(pair.start.lineno + pair.hanging,
                                     'invalid linesep: %r', name)
                elif field in {'smtputf8', '8bitmime', 'binarymime'}:
                    name = _chomp(pair.content).lower()
                    try:
                        return MABLE[name]
                    except KeyError:
                        reader.error(pair.start.lineno + pair.hanging,
                                     'invalid boolean: %r', name)
                options[field] = value

def _parse_headers(headers, o):
    # XXX: uhm, we should have at least 3 characters per line... right
    policy = email.policy.EmailPolicy(
        max_line_length = (max(1, o['maxlinelen'] - 2)
                            if o['maxlinelen'] else 0),
        linesep         = o['linesep'],
        utf8            = o['smtputf8'],
        cte_type        = ('8bit' if o['8bitmime'] or
                            o['binarymime'] else '7bit'),
    )
    parser = email.parser.BytesHeaderParser(policy=policy)
    return parser.parsebytes(headers)

def _set_content(message, reader, o):
    try:
        root = next(reader)
    except StopIteration:
        return False
    message['MIME-Version'] = '1.0'
    _set_content_from_node(message, reader, root, o)

PARAMHEAD_VERBS = {b'of', b'where'}
BASICPART_VERBS = PARAMHEAD_VERBS | {b'with'}
MULTIPART_VERBS = BASICPART_VERBS | {b'preamble', b'epilogue', b'including'}

def _set_content_from_node(message, reader, root, o):
    mimetype = root.key.decode('ascii')
    multipart = False
    parts = []
    mimetype = None
    charset = None
    encoding = None
    # encoding params
    eparam = {}
    breakpoint()
    reeder = reader.inner_rest_reader(root, interpret_input=True)
    for pair in reeder:
        print(f'{reeder._lineno + 1} {pair.start.lineno:02}-{pair.end.lineno:02}', *pair)
        key = pair.key.lower()
        if key not in MULTIPART_VERBS:
            reeder.error(pair.start.lineno,
                'unrecognized verb: %r', pair.key)
        if key == b'preamble':
            # we actually need to set these to strings...
            message.preamble = pair.content.decode('utf-8')
        elif key == b'epilogue':
            message.epilogue = pair.content.decode('utf-8')
        elif key == b'of':
            _set_param(message, 'Content-Type', 'type', reader, pair)
        elif key == b'with':
            header, value, params = _set_header(message, reader, pair, o)
            hlower = header.lower()
            if hlower == 'content-type':
                mimetype = message.get_content_type()
                charset = message.get_param('charset', None)
            elif hlower == 'content-transfer-encoding':
                encoding = message[header]
                eparam = params
        elif key == b'including':
            multipart = True
            if pair.data is not None:
                reeder.error(pair.start.lineno,
                    'data is invalid in subparts ("including")')
            part = type(message)(message.policy)
            reindeer = reeder.inner_rest_reader(pair, interpret_input=True)
            for pear in reindeer:
                _set_content_from_node(part, reindeer, pear, o)
            part.append()

    return True

def _set_param(message, header, name, reader, pair):
    if header.lower() == 'content-type':
        verb = '"of" for Content-Type'
    else:
        verb = '"of" for %s (%s)' % (header, name)

    # syntactically this makes no sense
    # since we only want one line
    if pair.hanging:
        reader.error(pair.start.lineno + 1,
            'hanging indent is not allowed in a '
            '%s parameter (%s)', header, verb)
    if pair.data is not None:
        reader.error(pair.start.lineno,
            'data is invalid in a %s parameter (%s)',
            header, verb)
    reeder = reader.inner_rest_reader(pair)

    # xxx: i'm too lazy to do this now, let the stop iteration
    # error and stuff propogate...
    pair = next(reeder)
    if not (pair.key and pair.value):
        reader.error(pair.start.lineno,
            'missing param and/or value in %s parameters (%s)',
            header, verb)

    param = pair.key.decode('ascii')
    value = pair.value.decode('utf-8')

    try:
        nextpair = next(reeder)
    except StopIteration:
        message.set_param(param, value, header=header)
    else:
        reeder.error(nextpair.start.lineno, 'extraneous line')

NAME2MIME_MAP = {
    'version':     'MIME-Version',
    'type':        'Content-Type',
    'encoding':    'Content-Transfer-Encoding',
    'disposition': 'Content-Disposition',
    'id':          'Content-ID',
    'disposition': 'Content-Disposition',
}

def _set_header(message, reader, pair, o):
    # xxx xxx: same here.
    if pair.hanging:
        reader.error(pair.start.lineno + 1,
            'hanging indent is not allowed in a mime header ("with")')
    if pair.data is not None:
        reader.error(pair.start.lineno,
            'data is invalid in a mime header ("with")')
    reeder = reader.inner_rest_reader(pair)
    pair = next(reeder)
    if not (pair.key and pair.value):
        reeder.error(pair.start.lineno + pair.hanging,
            'missing header and/or value in %s parameters (%s)',
            header, verb)

    name = pair.key.decode('ascii').lower()
    value = pair.value.decode('utf-8')
    try:
        header = NAME2MIME_MAP[name]
    except KeyError:
        reeder.error(pair.start.lineno + pair.hanging,
                     'unknown content header name %r', name)

    try:
        message[header] = value
    except ValueError: # There may be at most x headers...
        message.replace_header(header, value)

    pyparams = {}
    for pear in reeder:
        if pear.key not in PARAMHEAD_VERBS:
            reeder.error(pear.start.lineno,
                 'not a valid verb for parameterized header '
                 '%s: %r', header, pear.key)
            if pear.key == b'of':
                _set_param(message, header, name, reeder, pear)
            else:
                assert pear.key == b'where', pear.key
                _set_py_param(pyparms, name, header, value, reeder, pear, o)

    return header, value, pyparams

def _set_py_param(store, name, header, value, reader, pair, o):
    # XXX XXX: copy and paste for the moment...
    if pair.hanging:
        reader.error(pair.start.lineno + 1,
            'hanging indent is not allowed in a '
            '%s custom parameter ("where" for %s)',
            header, name)

    # NOTE: we are splitting the param ourselves so
    # things may look a bit weird here
    # (i could have added an option that lets you
    #  change the delimiter; but then idk if that'll
    #  make for code any less nightmarish than this)
    key_ws, val_ws = pair.rest.split(b'=', maxsplit=1)
    key = _skipright(key_ws)
    val = _skipleft(val_ws)
    if not (key and val):
        reeder.error(pair.middle.lineno,
            'missing param and/or value in a '
            '%s custom parameter ("where" for %s)',
            header, name)
    if '\n' in val:
        reeder.error(pair.middle.lineno + 1, 'extraneous line')

    klower = key.lower()
    try:
        dupe = next(k for k in store if key == k.encode('ascii'))
    except StopIteration:
        pass
    else:
        reeder.error(pair.start.lineno, 'duplicate key: %r', dupe)

    if name == 'encoding':
        ivalid = {b'maxlinelen'}
        bvalid = set()
        vlower = value.lower()
        if vlower == 'quoted-printable':
            bvalid.add(b'embed')
            bvalid.add(b'wrap')
        elif vlower == 'base64':
            bvalid.add(b'addeol')

        if key not in ivalid | bvalid:
            reeder.error(pair.middle.lineno,
                         '%r is not a valid key (candidates '
                         'for the %s encoding include %r)',
                         key, value, kvalid)

        if key in ivalid:
            number = int(value.strip().decode('ascii'))
            if pair.key == b'maxlinelen':
                if number > o['maxlinelen']:
                    reeder.error(pair.middle.lineno,
                                 'line limit for content encoding '
                                 'exceeds line limit imposed on the '
                                 'whole message (%d > %d)',
                                 number, o['maxlinelen'])
            store[name] = number
        elif key in bvalid:
            # XXX copied again
            name = value.lower()
            try:
                store[key.decode()] = MABLE[name]
            except KeyError:
                reader.error(pair.start.lineno,
                             'invalid boolean: %r', name)

    reeder.error(pair.start.lineno, '%s header does not have any '
                 'configurable options at the moment', name)

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

class Error(ValueError):
    def __str__(self):
        lines = super().__str__().splitlines(keepends=True)
        return '\n' + ''.join('  ' + ln for ln in lines)

class NewNode(rdks.list.node):
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
        return b''.join([self.data or b'', self.value or b''])

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
                    'in file %r, line %d:\n'
                        % (curr_file, curr_line)
                    if curr_line == last_line else
                    'in file %r, lines %d-%d:\n'
                        % (curr_file, curr_line, last_line))
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
            last_line = max(curr_line, last_line)
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
                 tb=(), interpret_input=True):
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if self._fp:
            self._fp.close()

    def __iter__(self):
        return self

    def _get_tb(self, lineno):
        this_tb = [(self._cwd, self._file, lineno)]
        return list(itertools.chain(self._tb, this_tb))

    def error(self, lineno, something, *args):
        tb = _format_tb(self._get_tb(self._lineno + lineno))
        somethang = something % args if args else something
        raise Error(''.join([tb, somethang]))

    def inner_reader(self, lines, lineno, *, interpret_input=False):
        tb = self._get_tb(self._lineno + lineno)
        return type(self)(INNER, self._cwd, lines,
                          self._lineno + lineno, tb, interpret_input)

    def outer_reader(self, file, cwd, lineno, *, interpret_input=True):
        tb = self._get_tb(self._lineno + lineno)
        return type(self)(file, cwd, None, 0, tb, interpret_input)

    def __next__(self):
        while True:
            pair = next(self._reader)
            if not (pair.key or pair.value):
                continue
            if not pair.key.startswith(b'#'):
                break
            if pair.value and (pair.hanging or b'\n' in pair.value):
                # we could look for comments chars that don't
                # start from the bottom, but this will do
                # (being stricter doesn't hurt)
                self.error(pair.start.lineno + 1, 'floating field')

        if not pair.key:
            self.error(pair.start.lineno, 'no field found')

        try:
            lines = pair.value.splitlines(keepends=True)
        except AttributeError:
            lines = []

        off_line = self._lineno + pair.start.lineno
        off_char = self._charno + pair.start.charno + len(pair.key)

        if pair.hanging:
            off_line += 1
            off_char += 1 + len(pair.indent)
        else:
            off_char += len(self._reader.delim)

        file = None
        data = None
        rest = lines
        if (pair.key and pair.value and
            pair.value.startswith(b'<') and
            self._do_input):
            tokens = lines[0].split(b' ')
            # for now i guess i will require people to write
            # field < input and not field (LF) (space) < input...
            if not pair.hanging and tokens[0] == b'<':
                file = b' '.join(tokens[1:]).rstrip(b'\r\n').decode('utf-8')
                try:
                    with open(os.path.join(self._cwd, file)):
                        pass
                except OSError as e:
                    self.error(pair.start.lineno,
                        'cannot input file %r\n  (cause: %s: %s)',
                        file, type(e).__name__, e)
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
                if not prefix:
                    value_lines = lines[1:]
                    rel_line = len(lines) - 1
                    off_line, off_char = pair.end
                    # XXX: wrong too; see below
                    off_char += len(pair.indent) * len(value_lines)
                else:
                    value_lines = []
                    for rel_line, ln in enumerate(lines[1:], 1):
                        if not ln.startswith(prefix):
                            break
                        value_lines.append(_skipleft(ln[:len(prefix)]))
                        off_line += 1
                        # XXX: this is wrong because we are ignoring
                        # the outer indent this whole node resides in
                        off_char += len(pair.indent) + len(ln)
                data = b''.join(lines[1:rel_line])
                rest = value_lines

        if file is not None:
            middle = rdks.list.position(off_line, off_char)
        else:
            middle = pair.end

        return NewNode(pair.key, pair.value,
                       hanging=pair.hanging,
                       indent=pair.indent,
                       cwd=self._cwd, file=file,
                       data=data, rest=rest,
                       start=pair.start,
                       middle=middle,
                       end=pair.end)

    def inner_data_reader(self, pair, **kwds):
        if pair.has_input():
            return self.outer_reader(
                pair.input_file, pair.input_root,
                self._lineno + pair.start.lineno, **kwds)
        if pair.data is None:
            lines = []
        else:
            lines = pair.data.splitlines(keepends=True)
        start = self._lineno + pair.start.lineno + pair.hanging
        return self.inner_reader(_patch(lines), start, **kwds)

    def inner_rest_reader(self, pair, **kwds):
        return self.inner_reader(_patch(pair.rest), pair.middle.lineno, **kwds)

    def get_rest(self, pair, **kwds):
        if not pair.rest:
            value = None
        else:
            with io.BytesIO() as tmp:
                writer = rdks.list.writer(tmp, text=False, delim=b' ')
                # name shadowing, pesky... >_>
                for pear in self.inner_rest_reader(pair, **kwds):
                    writer.writepair(pear)
                buff = _chomp(tmp.getvalue())
                value = _subs(buff.decode('utf-8')).encode('utf-8')
        return value

    def get_content(self, pair, **kwds):
        return b''.join([pair.data or b'',
                         self.get_rest(pair, **kwds) or b''])

if __name__ == '__main__':
    main()
