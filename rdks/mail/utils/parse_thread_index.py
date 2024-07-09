#!/usr/bin/env python3
# -*- coding: ascii -*-

# re-implementation of Jeremy Scott's filetime_converter:
# http://web.archive.org/web/20150112012253/http://www.solutionary.com/_assets/pdf/datasheets/filetime-converter.txt

import argparse
import sys

from rdks.mail.outlook import ThreadIndex

__all__ = ['main']

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="dump info about microsoft exchange's thread index")
    parser.add_argument('--use-old-filetime', action='store_true',
                        help='enable old Exchange FILETIME format')
    parser.add_argument('value', help='base64 string from the header')
    args = parser.parse_args(argv)

    ti = ThreadIndex.from_str(args.value, old_filetime=args.use_old_filetime)
    decoded = bytes(ti)
    print('Decoded:\t', decoded[0:6].hex(), decoded[6:22].hex(),
        ' '.join(
            decoded[22+i:27+i].hex() for i in range(0, len(decoded) - 22, 5)
        ),
    )
    print('FILETIME:\t', ti.header.date.as_datetime())
    # the guid is actually readable from the hexdump :/
    #print('GUID:\t', ti.header.guid)

    filetime = ti.header.date.as_datetime()
    for count, child in enumerate(ti.responses, 1):
        filetime += child.delta.as_timedelta()
        print('\tChild message[%d]: ' % (count,), filetime)

if __name__ == '__main__':
    sys.exit(main())
