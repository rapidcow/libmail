#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import email.message
import email.parser
import email.policy

import argparse
import shutil
import sys

try:
    import wcwidth
except ImportError:
    wcwidth = None

import humanize

def main():
    parser = argparse.ArgumentParser(
        description='like tree(1) but for mime, with mutt-like output',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('message', nargs='*', default=(),
                        help='RFC message(s)')
    parser.add_argument('--batch', action='store_true',
                        help='read files from stdin')
    parser.add_argument('--width', '-w', metavar='N', type=int,
                        default=shutil.get_terminal_size().columns,
                        help='width')

    args = parser.parse_args()
    if args.batch:
        assert not args.message, 'incompatible options'
        for line in sys.stdin:
            file = line.rstrip('\r\n')
            print('==>', file, '<==')
            _print_mutt(file, args.width)
    else:
        for file in args.message:
            if len(args.message) > 1:
                print('==>', file, '<==')
            _print_mutt(file, args.width)

def _xlen(s):
    return wcwidth.wcswidth(s) if wcwidth else len(s)

def _print_mutt(file, width):
    with open(file, 'rb') as fp:
        parser = email.parser.BytesParser(policy=email.policy.SMTP)
        message = parser.parse(fp)
    for i, content, dspo, desc in _format_mutt(0, message):
        left = f' {dspo} {i:5} {desc}'
        right = content.rjust(max(0, width - _xlen(left) - 3))
        print(left, right, '')

def _format_mutt(i, msg):
    """
     +--------------------------------------------------------------------+
     |  I     1 <no description>          [multipa/alternativ, 7bit, 37K] |
     |  I     2 ├─><no description>     [text/plain, quoted, utf-8, 9.8K] |
     |  I     3 └─><no description>       [text/html, quoted, utf-8, 26K] |
     +--------------------------------------------------------------------+
    """
    payload = msg.get_payload()
    desc = (msg.get('Content-Description')
            or msg.get_param('filename', header='Content-Disposition')
            or msg.get_param('name') or '<no description>')
    shortdesc = desc.splitlines()[0][:40]
    mimetype = '/'.join([msg.get_content_maintype()[:7],
                         msg.get_content_subtype()[:10]])
    if msg.get_content_type() == 'message/delivery-status':
        payload = b''.join(map(bytes, payload))
    if isinstance(payload, list):
        inner_first, inner_rest = '├─> ', '│   '
        outer_first, outer_rest = '└─> ', '    '
        i += 1
        yield i, f'[{mimetype}]', '-', shortdesc
        for child in payload[:-1]:
            prefix = inner_first
            for i, content, dspo, desc in _format_mutt(i, child):
                yield i, content, dspo, prefix + desc
                prefix = inner_rest
        for child in payload[-1:]:
            prefix = outer_first
            for i, content, dspo, desc in _format_mutt(i, child):
                yield i, content, dspo, prefix + desc
                prefix = outer_rest
    else:
        # QUOTED-PRINTABLE exists, can you believe that *eye roll*
        cte = (msg['Content-Transfer-Encoding'] or '?').lower()
        if cte == 'quoted-printable':
            cte = 'quoted'
        dsps = msg.get('Content-Disposition', 'unknown').partition(';')[0]
        dspo = ('I' if dsps == 'inline' else
                'A' if dsps == 'attachment' else '?')
        size = humanize.naturalsize(len(payload))
        yield i + 1, f'[{mimetype}, {cte}, {size}]', dspo, shortdesc

if __name__ == '__main__':
    sys.exit(main())
