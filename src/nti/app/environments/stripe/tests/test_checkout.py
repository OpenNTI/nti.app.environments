from collections import namedtuple

import unittest

from hamcrest import assert_that
from hamcrest import is_

from nti.testing.matchers import provides
from nti.testing.matchers import verifiably_provides

import fudge

from stripe.util import convert_to_stripe_object

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..interfaces import IStripeKey
from ..interfaces import IStripeCheckout
from ..interfaces import IStripeCheckoutSession
from ..interfaces import IStripeCustomer

SESSION_JSON = {
    "id": "cs_test_SKyGKH9hY4nW5csGTvkVj5zW4s7bcDqGESQzB2KJpXTjllhNrgko3Iaf",
    "object": "checkout.session",
    "billing_address_collection": None,
    "cancel_url": "http://localhost:6543/onboarding/sites/Sacf3b74fb53749bfabc506291c918b86/stripe_subscription/@@manage",
    "client_reference_id": "80e2dba62a7946a5a963e28a7bf6f371",
    "customer": "cus_H5fik8W6pPm0HB",
    "customer_email": None,
    "display_items": [
        {
            "amount": 23900,
            "currency": "usd",
            "plan": {
                "id": "plan_H0mF4xaJYoOvpz",
                "object": "plan",
                "active": True,
                "aggregate_usage": None,
                "amount": 23900,
                "amount_decimal": "23900",
                "billing_scheme": "per_unit",
                "created": 1585663433,
                "currency": "usd",
                "interval": "month",
                "interval_count": 1,
                "livemode": False,
                "metadata": {
                },
                "nickname": "Monthly",
                "product": "prod_H0SQlxRwqs0BOg",
                "tiers": None,
                "tiers_mode": None,
                "transform_usage": None,
                "trial_period_days": None,
                "usage_type": "licensed"
            },
            "quantity": 10,
            "type": "plan"
        }
    ],
    "livemode": False,
    "locale": None,
    "metadata": {
    },
    "mode": "subscription",
    "payment_intent": None,
    "payment_method_types": [
        "card"
    ],
    "setup_intent": None,
    "shipping": None,
    "shipping_address_collection": None,
    "submit_type": None,
    "subscription": "sub_HMtfhyfX4jq6Nj",
    "success_url": "http://localhost:6543/onboarding/sites/Sacf3b74fb53749bfabc506291c918b86/stripe_subscription/@@manage"
}

SUBSCRIPTION_ITEM = namedtuple('SubscriptionItem', ['plan', 'quantity'])

class TestSubscriptionCheckout(unittest.TestCase):

    layer = BaseConfiguringLayer

    def setUp(self):
        self.session = convert_to_stripe_object(SESSION_JSON)
        self.subitem = SUBSCRIPTION_ITEM(plan='plan_H0mF4xaJYoOvpz', quantity=10)
        self.key = component.getUtility(IStripeKey)
        self.checkout = IStripeCheckout(self.key)

    def test_session_provides(self):
        assert_that(self.session, provides(IStripeCheckoutSession))

    @fudge.patch('stripe.checkout.Session.create')
    def test_generate_session(self, mock_create_session):

        cancel_url = 'https://example.com/cancel'
        success_url = 'https://example.com/success'
        metadata = {'foo': 'bar'}

        expected_subscription_data = {
            'items': [{'plan': self.subitem.plan, 'quantity': self.subitem.quantity}],
            'metadata': metadata
        }

        expected_kwargs = dict(payment_method_types=['card'],
                               mode='subscription',
                               subscription_data=expected_subscription_data,
                               customer=None,
                               customer_email=None,
                               cancel_url=cancel_url,
                               success_url=success_url,
                               client_reference_id='id1234',
                               api_key=self.key.secret_key)
        mock_create_session.expects_call().with_args(**expected_kwargs).returns(self.session)
        
        resp = self.checkout.generate_subscription_session([self.subitem],
                                                           cancel_url,
                                                           success_url,
                                                           client_reference_id='id1234',
                                                           metadata=metadata)

        assert_that(resp, verifiably_provides(IStripeCheckoutSession))

        # If we pass a customer that goes along as well
        customer = IStripeCustomer('cust_1234')
        email = 'cust_1234@test.com'

        expected_kwargs['customer'] = customer.customer_id
        expected_kwargs['customer_email'] = email

        mock_create_session.expects_call().with_args(**expected_kwargs).returns(self.session)

        self.checkout.generate_subscription_session([self.subitem],
                                                    cancel_url,
                                                    success_url,
                                                    client_reference_id='id1234',
                                                    customer=customer,
                                                    customer_email=email,
                                                    metadata=metadata)
        
