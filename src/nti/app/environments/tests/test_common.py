import unittest
import datetime
from datetime import timezone

from hamcrest import calling
from hamcrest import raises
from hamcrest import assert_that
from hamcrest import is_

from nti.app.environments.common import convertToUTC
from nti.app.environments.common import parseDate
from nti.app.environments.common import formatDate
from nti.app.environments.common import formatDateToLocal

class TestCommon(unittest.TestCase):

    def testconvertToUTC(self):
        assert_that(convertToUTC(datetime.datetime(2020,1,13,10,0,0), toTimeStamp=True), is_(1578931200))
        assert_that(convertToUTC(datetime.datetime(2020,1,13,10,0,0), toTimeStamp=False).strftime('%Y-%m-%d %H:%M:%S'), is_('2020-01-13 16:00:00'))

    def testparseDate(self):
        assert_that(parseDate('2020-01-13 00:00:00').strftime('%Y-%m-%d %H:%M:%S'), is_('2020-01-13 06:00:00'))
        assert_that(parseDate('2020-01-13T00:00:00Z').strftime('%Y-%m-%d %H:%M:%S'), is_('2020-01-13 06:00:00'))
        assert_that(parseDate('2020-01-13T00:00:00Z', ignoretz=False).strftime('%Y-%m-%d %H:%M:%S'), is_('2020-01-13 00:00:00'))
        assert_that(calling(parseDate).with_args('2020-0d'), raises(Exception, pattern='Unknown string format: 2020-0d'))
        assert_that(parseDate('2020-0d', safe=True), is_(None))

    def testformatDate(self):
        assert_that(formatDate(None), is_(''))
        assert_that(formatDate(None, default=None), is_(None))
        assert_that(formatDate(datetime.datetime(2020,1,13,0,0,1)), is_('2020-01-13T00:00:01Z'))
        assert_that(formatDate(datetime.datetime(2020,1,13,0,0,0), '%Y-%m-%d %H:%M:%S'), is_('2020-01-13 00:00:00'))

    def testformatDateToLocal(self):
        assert_that(formatDateToLocal(None), is_(''))
        assert_that(formatDateToLocal(None, default=None), is_(None))
        assert_that(formatDateToLocal(0), is_('1969-12-31 18:00:00'))
        assert_that(formatDateToLocal(datetime.datetime(2020,1,13,0,0,1)), is_('2020-01-12 18:00:01'))
        assert_that(formatDateToLocal(datetime.datetime(2020,1,13,0,0,0), '%Y-%m-%dT%H:%M:%S'), is_('2020-01-12T18:00:00'))
        assert_that(formatDateToLocal(datetime.datetime(2020,1,13,0,0,1), local_tz="Asia/ShangHai"), is_('2020-01-13 08:00:01'))

    def testformatTZDateToLocal(self):
        tzaware = datetime.datetime(2020,1,13,0,0,1, tzinfo=timezone.utc)
        assert_that(formatDateToLocal(tzaware), is_('2020-01-12 18:00:01'))
