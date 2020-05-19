import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..billing import StripeBillingPortalSession

from ..interfaces import IStripeCustomer
from ..interfaces import IStripeKey
from ..interfaces import IStripeBillingPortal
from ..interfaces import IStripeBillingPortalSession

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
        session = StripeBillingPortalSession(_raw=SESSION_EXAMPLE)

        assert_that(session, verifiably_provides(IStripeBillingPortalSession))

        assert_that(session.id, is_('bps_1GkZmRJSl3QXdEfxVVbCVU3I'))
        assert_that(session.customer.customer_id, is_('cus_HJCALoxCODL3uv'))
        assert_that(session.url, is_('https://billing.stripe.com/session/{SESSION_SECRET}'))

    @fudge.patch('stripe.billing_portal.Session.create')
    def test_generate_session(self, mock_create_session):
        customer = IStripeCustomer('cus_HJCALoxCODL3uv')
        return_url = 'https://example.com/account'

        key = component.getUtility(IStripeKey)

        mock_create_session.expects_call().with_args(customer=customer.customer_id,
                                                     return_url=return_url,
                                                     api_key=key.secret_key).returns(SESSION_EXAMPLE)

        portal = IStripeBillingPortal(key)
        session = portal.generate_session(customer, return_url)

        assert_that(session, verifiably_provides(IStripeBillingPortalSession))
        assert_that(session.id, is_('bps_1GkZmRJSl3QXdEfxVVbCVU3I'))
        assert_that(session.customer.customer_id, is_('cus_HJCALoxCODL3uv'))
        assert_that(session.url, is_('https://billing.stripe.com/session/{SESSION_SECRET}'))
