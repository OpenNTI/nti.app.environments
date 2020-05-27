import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..interfaces import IStripeCustomer

class TestCustomerAdapters(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_customer_from_string(self):
        key = IStripeCustomer('cus_test1234')
        assert_that(key, verifiably_provides(IStripeCustomer))
        assert_that(key.customer_id, is_('cus_test1234'))
