import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import provides
from nti.testing.matchers import verifiably_provides

import fudge

from stripe.util import convert_to_stripe_object

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..billing import MinimalStripeSubscription

from ..interfaces import IStripeCustomer
from ..interfaces import IStripeKey
from ..interfaces import IStripeBillingPortal
from ..interfaces import IStripeBillingPortalSession
from ..interfaces import IStripeInvoice
from ..interfaces import IStripeSubscription
from ..interfaces import IStripeSubscriptionBilling

SESSION_EXAMPLE = {
    "id": "bps_1GkZmRJSl3QXdEfxVVbCVU3I",
    "object": "billing_portal.session",
    "created": 1589911387,
    "customer": "cus_HJCALoxCODL3uv",
    "livemode": True,
    "return_url": "https://example.com/account",
    "url": "https://billing.stripe.com/session/{SESSION_SECRET}"
}

class TestBillingSession(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_session_from_stripe(self):
        session = convert_to_stripe_object(SESSION_EXAMPLE)

        assert_that(session, provides(IStripeBillingPortalSession))

    @fudge.patch('stripe.billing_portal.Session.create')
    def test_generate_session(self, mock_create_session):
        customer = IStripeCustomer('cus_HJCALoxCODL3uv')
        return_url = 'https://example.com/account'

        key = component.getUtility(IStripeKey)

        mock_create_session.expects_call().with_args(customer=customer.customer_id,
                                                     return_url=return_url,
                                                     api_key=key.secret_key).returns_fake()

        portal = IStripeBillingPortal(key)
        session = portal.generate_session(customer, return_url)

SUB_JSON = {
    "application_fee_percent": None,
    "billing_cycle_anchor": 1590187949,
    "billing_thresholds": None,
    "cancel_at": None,
    "cancel_at_period_end": False,
    "canceled_at": None,
    "collection_method": "charge_automatically",
    "created": 1590187949,
    "current_period_end": 1592866349,
    "current_period_start": 1590187949,
    "customer": "cus_H5fik8W6pPm0HB",
    "days_until_due": None,
    "default_payment_method": "pm_1Gljj6JSl3QXdEfxzsJhLaHu",
    "default_source": None,
    "default_tax_rates": [],
    "discount": None,
    "ended_at": None,
    "id": "test_sub_1234",
    "object": "subscription"
}

INVOICE_JSON = {
  "id": "in_G2Y5GBeHnCLKVh",
  "object": "invoice"
}

class TestSubscriptionBilling(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.mock_sub = MinimalStripeSubscription(subscription_id='test_sub_1234')
        self.key = component.getUtility(IStripeKey)
        self.billing = IStripeSubscriptionBilling(self.key)

    def test_adatper(self):
        assert_that(self.billing, verifiably_provides(IStripeSubscriptionBilling))

    @fudge.patch('stripe.Subscription.retrieve')
    def test_get_subscription(self, mock_get_sub):
        sub_resp = convert_to_stripe_object(SUB_JSON)
        mock_get_sub.expects_call().with_args(self.mock_sub.id,
                                              api_key=self.key.secret_key).returns(sub_resp)

        resp = self.billing.get_subscription(self.mock_sub)

        assert_that(resp, verifiably_provides(IStripeSubscription))
        assert_that(resp.id, is_(self.mock_sub.id))
        
    @fudge.patch('stripe.Invoice.upcoming')
    def test_upcoming_invoice(self, mock_get_inv):
        inv_resp = convert_to_stripe_object(INVOICE_JSON)
        mock_get_inv.expects_call().with_args(subscription=self.mock_sub.id,
                                              api_key=self.key.secret_key).returns(inv_resp)

        resp = self.billing.get_upcoming_invoice(self.mock_sub)
        assert_that(resp.id, is_('in_G2Y5GBeHnCLKVh'))

class TestInvoice(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_invoice_provides(self):
        inv_resp = convert_to_stripe_object(INVOICE_JSON)
        assert_that(inv_resp, provides(IStripeInvoice))


