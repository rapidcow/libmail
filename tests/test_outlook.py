from rdks.mail.outlook import Header, FileTime
from rdks.mail.outlook import TimeDiff
from rdks.mail.outlook import ThreadIndex
from email.utils import parsedate_to_datetime as parse_rfc_date
from functools import partial

import datetime
import random
import uuid

import unittest

def parse_iso_date(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S%z')

# 1/10^7 - number of seconds per tick
# (IPREC = inverse PREC)
IPREC = 1E-7

# old time truncates 6 bytes out of 8 bytes
# so 2 bytes of accuracy are lost, i.e. 6.5536 ms
# so we allow for a window that is twice this number
old_time_me = (1 << 17) * IPREC
# in addition, since microsoft is definitely not
# computing filetime from the date header, we are
# going to have to be painfully loose with our tests
# for equality.  below the third column also contains
# the error in seconds, adjusted on a per-case basis:
# in other words, cheating >:(

old_cases = [
### CASE #1
    [
      # source: https://stackoverflow.com/q/27374077
      (parse_rfc_date('Tue, 2 Dec 2014 08:21:00 +0000'),
       'AdAOBz5QJ/JuQSJMQTmSQ8+dVs2IDg==', 720), # 12 minutes
      (parse_rfc_date('Mon, 8 Dec 2014 13:12:13 +0000'),
       'AdAOBz5QJ/JuQSJMQTmSQ8+dVs2IDgE4StZw', 75), # 1.25 minutes
    ],
### CASE #2
    [
      # source: https://technical.nttsecurity.com/post/102enx6/outlook-thread-index-value-analysis
      # archives:
      # https://web.archive.org/web/20151225001827/https://www.solutionary.com/resource-center/blog/2014/04/thread-index-value-analysis/
      # https://web.archive.org/web/20190403191505/https://technical.nttsecurity.com/post/102enx6/outlook-thread-index-value-analysis
      # RFC message date is not known, so this is a pretty contrived test
      (parse_rfc_date('Mon, 24 Mar 2014 16:02:21 +0000'),
       'Ac9HenBT+CFEJCaeTk6wMLT54yoyqw==', 1), # 1 second for truncation
    ],
### CASE #3-#5
    # source for the following:
    # https://forum.rebex.net/3841/how-to-interprete-thread-index-header/
    [
      # stub test; OP only showed what they computed for
      # the response's date
      (parse_iso_date('2013-07-01 11:34:32+00:00'),
       'Ac52TvSLqL2n1+xFTLyFv0/vTSUlWg==', 1),
      (parse_iso_date('2013-09-03 07:26:58+02:00'),
       'Ac52TvSLqL2n1+xFTLyFv0/vTSUlWgyF0E9Q', 1),
    ],
    # "invalid date": too old with old format, too new with new format
    [
      (parse_iso_date('1831-11-05 00:06:01+01:00'),
       'AQLNahwAkMF4P9Bl8t7dPDytf5aNnA==', 1),
    ],
    [
      (parse_iso_date('2013-09-03 08:47:37+02:00'),
       'Ac6ocXoGclflrAlgQg2VFL1JFq6hyg==', 1),
    ],
### CASE #6
    # source:
    # https://managing.blue/2007/12/23/more-fun-with-message-threading/
    #   also blog.postmaster.gr/2007/12/23/more-fun-with-message-threading/
    # https://managing.blue/2007/12/11/trying-to-make-use-of-outlooks-thread-index-header/
    #   also http://blog.postmaster.gr/2007/12/11/trying-to-make-use-of-outlooks-thread-index-header/
    # also a stub; OP did not tell us the email's date ;(
    [
      (parse_iso_date('2007-03-30 00:39:40+00:00'),
       'AcdyY+a08VX8xfobTsy61v9NHPZ7QA==', 1),
      (parse_iso_date('2007-03-30 00:55:03+00:00'),
       'AcdyY+a08VX8xfobTsy61v9NHPZ7QAAAiXbA', 1),
      (parse_iso_date('2007-03-30 03:41:28+00:00'),
       'AcdyY+a08VX8xfobTsy61v9NHPZ7QAAAiXbAAAXP5fw=', 1),
      (parse_iso_date('2007-03-30 03:43:26+00:00'),
       'AcdyY+a08VX8xfobTsy61v9NHPZ7QAAAiXbAAAXP5fwAABGXGw==', 1),
    ],
### CASE #7
    # source:
    # https://stackoverflow.com/q/2278314/19411800
    # stub again, except i am only including the third guy
    [ (parse_iso_date('2010-02-17 01:14:56+00:00'),
       'Acqvbp3C811djHLbQ9eTGDmyBL925w==', 1) ],
### CASE #8
    # source:
    # https://www.meridiandiscovery.com/how-to/e-mail-conversation-index-metadata-computer-forensics/
    [
      (parse_iso_date('2013-01-02 17:01:04+00:00'),
       # 01CDE90ABFE0D78F0E4280824120B2F1D0E3C07ED007
       'Ac3pCr/g148OQoCCQSCy8dDjwH7QBw==', 1),
      (parse_iso_date('2013-01-02 17:23:58+00:00'),
       # 01CDE90ABFE0D78F0E4280824120B2F1D0E3C07ED0070000CCBA30
       'Ac3pCr/g148OQoCCQSCy8dDjwH7QBwAAzLow', 1),
      (parse_iso_date('2013-01-02 17:25:53+00:00'),
       # 01CDE90ABFE0D78F0E4280824120B2F1D0E3C07ED0070000CCBA300000114460
       'Ac3pCr/g148OQoCCQSCy8dDjwH7QBwAAzLowAAARRGA=', 1),
    ],
]

# new time is much worse, being 8 times less accurate
### new_time_me = (1 << 20) * IPREC
# (wait no my ass can't math =n= it's 2^8 not 8)
new_time_me = (1 << 25) * IPREC
new_cases = [
    [
      (parse_rfc_date('Sun, 16 Jun 2024 16:47:04 +0800'),
       'AQHav8l4TuPbq+cqj0eS0e2rUJzjEw==', 188), # 3:08
      (parse_rfc_date('Sun, 16 Jun 2024 08:51:55 +0000'),  # i will not
       'AQHav8l4TuPbq+cqj0eS0e2rUJzjE7HKFHH1', 700723058), # explain this
    ],
]

def get_rand_date():
    tzinfo = datetime.timezone(datetime.timedelta(
        seconds=random.randint(-1, 1) * (
            (random.randrange(0, 60, 30)
             + random.randrange(12) * 60)
            * 60
        )
    ))
    return datetime.datetime(
        random.randint(2005, 2018),
        random.randint(1, 12),
        random.randint(1, 28),
        random.randrange(24),
        random.randrange(60),
        random.randrange(60),
        random.randrange(1000),
        tzinfo)

class TestThreadIndex(unittest.TestCase):
    def x_test_filetime(cases, old, x):
        err = old_time_me if old else new_time_me
        case = cases[x]
        def meth(self):
            # check root date
            date, tids, delta = case[0]
            tidx = ThreadIndex.from_str(tids, old_filetime=old)
            self.assertAlmostEqual(
                tidx.header.date.as_unix(100) * IPREC,
                date.timestamp(),
                delta=err + delta,
            )
            # check child date
            for _, tins, _ in case[1:]:
                tinx = ThreadIndex.from_str(tins, old_filetime=old)
                self.assertEqual(tidx.header, tinx.header)
        return meth

    x_test_old_filetime = partial(x_test_filetime, old_cases, True)
    x_test_new_filetime = partial(x_test_filetime, new_cases, False)

    def x_test_roundtrip(old):
        err = old_time_me if old else new_time_me
        def meth(self):
            # do a few tests for good measure
            for _ in range(12):
                date = get_rand_date()
                time = FileTime.from_datetime(date)
                unix = date.timestamp()
                guid = uuid.uuid4()
                tidx = ThreadIndex(Header(time, guid, old_filetime=old))
                dupe = ThreadIndex.from_str(str(tidx), old_filetime=old)
                self.assertAlmostEqual(
                    tidx.header.date.as_unix(100) * IPREC,
                    unix, delta=err,
                    msg='deserialization failed for %r' % (date,),
                )
                self.assertAlmostEqual(
                    dupe.header.date.as_unix(100) * IPREC,
                    unix, delta=err,
                    msg='serialization failed for %r' % (date,),
                )
        return meth

    test_roundtrip_for_old_filetime = x_test_roundtrip(True)
    test_roundtrip_for_new_filetime = x_test_roundtrip(False)

    def x_test_timediff(cases, old, x):
        # we want at least two levels
        if len(cases[x]) < 2:
            return None
        err = old_time_me if old else new_time_me
        case = cases[x]
        def meth(self):
            _, pids, _ = case[0]
            pidx = ThreadIndex.from_str(pids, old_filetime=old)
            dt = pidx.header.date.as_datetime(with_tz=True)
            for date, tids, delta in case[1:]:
                tidx = ThreadIndex.from_str(tids, old_filetime=old)
                #### XXX: this probably shouldn't happen
                ### self.assertEqual(pidx.header, tidx.header)
                ### self.assertEqual(pidx.responses, tidx.responses[:-1])
                self.assertTrue(
                    pidx.header == tidx.header and
                    pidx.responses == tidx.responses[:-1],
                    'new Thread-Index not a reply to the '
                    'last: malformed test cases? %r')
                dt += tidx.responses[-1].delta.as_timedelta()
                self.assertAlmostEqual(
                    dt.timestamp(),
                    date.timestamp(),
                    delta=new_time_me + delta,
                )
                pidx = tidx
        return meth

    x_test_timediff_with_old_filetime = partial(
            x_test_timediff, old_cases, True)
    x_test_timediff_with_new_filetime = partial(
            x_test_timediff, new_cases, False)

for s in 'test_old_filetime', 'test_timediff_with_old_filetime':
    for i, cases in enumerate(old_cases):
        factory = getattr(TestThreadIndex, 'x_%s' % (s,))
        setattr(TestThreadIndex, '%s_%03d' % (s, i + 1), factory(i))

for s in 'test_new_filetime', 'test_timediff_with_new_filetime':
    for i, cases in enumerate(new_cases):
        factory = getattr(TestThreadIndex, 'x_%s' % (s,))
        setattr(TestThreadIndex, '%s_%03d' % (s, i + 1), factory(i))

class TestTimeDiff(unittest.TestCase):
    def test_overflow_error(self):
        with self.assertRaises(ValueError):
            TimeDiff.from_ticks(TimeDiff.MAX_SMALL_TICKS + 1, sig=0)
        with self.assertRaises(ValueError):
            TimeDiff.from_ticks(TimeDiff.MAX_LARGE_TICKS + 1, sig=1)
        with self.assertRaises(ValueError):
            TimeDiff.from_ticks(TimeDiff.MAX_LARGE_TICKS + 1)

if __name__ == '__main__':
    unittest.main()
