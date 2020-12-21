from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length

import fudge
from fudge.inspector import arg

import unittest

import json
import time

from zope import component

from zope.component import eventtesting

from stripe.util import convert_to_stripe_object
from stripe.webhook import WebhookSignature

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn

from nti.app.environments.stripe.interfaces import iface_for_event
from nti.app.environments.stripe.interfaces import IStripeCheckoutSessionCompletedEvent
from nti.app.environments.stripe.interfaces import IStripeInvoicePaidEvent
from nti.app.environments.stripe.interfaces import IStripeEvent
from nti.app.environments.stripe.interfaces import IWebhookSigningSecret

SESSION_COMPLETED_EVENT = {
  "id": "evt_1GlEeIJSl3QXdEfxphYmtYDf",
  "object": "event",
  "api_version": "2020-03-02",
  "created": 1590068486,
  "data": {
    "object": {
      "id": "cs_test_j3JgLowN5RfrGpz0obzxu8Y06jfRDJ1Eg3imkD4fdSVv2l7YA9j9jEAP",
      "object": "checkout.session",
      "billing_address_collection": None,
      "cancel_url": "https://httpbin.org/post",
      "client_reference_id": None,
      "customer": "cus_HJsP73yESBPmmG",
      "customer_email": None,
      "display_items": [
        {
          "amount": 1500,
          "currency": "usd",
          "custom": {
            "description": "comfortable cotton t-shirt",
            "images": None,
            "name": "t-shirt"
          },
          "quantity": 2,
          "type": "custom"
        }
      ],
      "livemode": False,
      "locale": None,
      "metadata": {},
      "mode": "payment",
      "payment_intent": "pi_1GlEeFJSl3QXdEfxeZbG1YCx",
      "payment_method_types": [
        "card"
      ],
      "setup_intent": None,
      "shipping": None,
      "shipping_address_collection": None,
      "submit_type": None,
      "subscription": None,
      "success_url": "https://httpbin.org/post"
    }
  },
  "livemode": False,
  "pending_webhooks": 0,
  "request": {
    "id": None,
    "idempotency_key": None
  },
  "type": "checkout.session.completed"
}

OTHER_EVENT = {
  "id": "evt_1GlEeIJSl3QXdEfxphYmtYDf",
  "object": "event",
  "api_version": "2020-03-02",
  "created": 1590068486,
  "data": {
    "object": {
      "id": "cs_test_j3JgLowN5RfrGpz0obzxu8Y06jfRDJ1Eg3imkD4fdSVv2l7YA9j9jEAP",
      "object": "checkout.session",
      "billing_address_collection": None,
      "cancel_url": "https://httpbin.org/post",
      "client_reference_id": None,
      "customer": "cus_HJsP73yESBPmmG",
      "customer_email": None,
      "display_items": [
        {
          "amount": 1500,
          "currency": "usd",
          "custom": {
            "description": "comfortable cotton t-shirt",
            "images": None,
            "name": "t-shirt"
          },
          "quantity": 2,
          "type": "custom"
        }
      ],
      "livemode": False,
      "locale": None,
      "metadata": {},
      "mode": "payment",
      "payment_intent": "pi_1GlEeFJSl3QXdEfxeZbG1YCx",
      "payment_method_types": [
        "card"
      ],
      "setup_intent": None,
      "shipping": None,
      "shipping_address_collection": None,
      "submit_type": None,
      "subscription": None,
      "success_url": "https://httpbin.org/post"
    }
  },
  "livemode": False,
  "pending_webhooks": 0,
  "request": {
    "id": None,
    "idempotency_key": None
  },
  "type": "checkout.session.started"
}


class TestStripeWebhooks(BaseAppTest):

    def setUp(self):
        super(TestStripeWebhooks, self).setUp()
        eventtesting.setUp()

    @with_test_app()
    def test_hook_no_sig(self):
        # we require signature validation
        self.testapp.post_json('/stripe/hooks',
                               params=OTHER_EVENT,
                               status=400)

    @with_test_app()
    def test_signature_mismatch(self):
        self.testapp.post_json('/stripe/hooks',
                               headers={'STRIPE_SIGNATURE': 'foo'},
                               params=OTHER_EVENT,
                               status=400)

    def _sign_event(self, event, secret):
        timestamp = time.time()
        data = json.dumps(event)
        payload = '%d.%s' % (timestamp, data)
        
        sig = WebhookSignature._compute_signature(payload, secret)
        sig_header = 't=%d,v1=%s' %(timestamp, sig)

        return sig_header, data

    @with_test_app()
    def test_sig_match_returns_200(self):
        root = self._root()
        # XXX We should absolutely not be doing this here, but the test
        # infrastructure is missing some key things to be able to make this pass
        # without large changes in tests right now. Need to come back to that in a different
        # branch
        with ensure_free_txn():
            from nti.app.environments.generations.evolve2 import install_stripe_sessions
            install_stripe_sessions(root)
        event = convert_to_stripe_object(SESSION_COMPLETED_EVENT)

        webhook_secret = component.getUtility(IWebhookSigningSecret, name='default')

        sig_header, body = self._sign_event(event, webhook_secret.secret)
        self.testapp.post('/stripe/hooks',
                          params=body,
                          content_type='application/json',
                          headers={'STRIPE_SIGNATURE': sig_header},
                          status=200)

    @with_test_app()
    def test_notifies(self):
        root = self._root()
        # XXX We should absolutely not be doing this here, but the test
        # infrastructure is missing some key things to be able to make this pass
        # without large changes in tests right now. Need to come back to that in a different
        # branch
        with ensure_free_txn():
            from nti.app.environments.generations.evolve2 import install_stripe_sessions
            install_stripe_sessions(root)
        event = convert_to_stripe_object(SESSION_COMPLETED_EVENT)

        webhook_secret = component.getUtility(IWebhookSigningSecret, name='default')

        sig_header, body = self._sign_event(event, webhook_secret.secret)
        self.testapp.post('/stripe/hooks',
                          params=body,
                          content_type='application/json',
                          headers={'STRIPE_SIGNATURE': sig_header},
                          status=200)

        assert_that(eventtesting.getEvents(IStripeCheckoutSessionCompletedEvent), has_length(1))

INVOICE_PAID_EVENT = {
    "id": "evt_1GlEeIJSl3QXdEfxphYmtYDf",
    "object": "event",
    "api_version": "2020-03-02",
    "created": 1590068486,
    "data": {
        "object": {}
    },
    "livemode": False,
    "pending_webhooks": 0,
    "request": {
        "id": None,
        "idempotency_key": None
    },
    "type": "invoice.paid"
}


class TestEventIface(unittest.TestCase):

    def test_iface_for_event(self):
        assert_that(iface_for_event(convert_to_stripe_object(OTHER_EVENT)),
                    is_(IStripeEvent))
        assert_that(iface_for_event(convert_to_stripe_object(SESSION_COMPLETED_EVENT)),
                    is_(IStripeCheckoutSessionCompletedEvent))

    def test_iface_for_invoice_paid(self):
        assert_that(iface_for_event(convert_to_stripe_object(INVOICE_PAID_EVENT)),
                    is_(IStripeInvoicePaidEvent))
        
