import unittest

from hamcrest import assert_that

from nti.testing.matchers import verifiably_provides

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.stripe.interfaces import IStripeCustomer

class TestCustomerAdapters(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_customer_from_string(self):
        customer = PersistentCustomer()
        stripe = IStripeCustomer(customer)
        stripe.customer_id = 'foo'

        assert_that(stripe, verifiably_provides(IStripeCustomer))
