import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import starts_with

from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..interfaces import IStripeKey
from ..interfaces import IWebhookSigningSecret

class TestKeyRegistration(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_keys_for_dev(self):
        key = component.getUtility(IStripeKey)
        assert_that(key, verifiably_provides(IStripeKey))

        assert_that(key.publishable_key, is_('pk_test_gsyBVYVrN6NNdMDxj6rGX3hc'))
        assert_that(key.secret_key, starts_with('sk_test_0EQT0'))

    def test_webhook_secret_for_def(self):
        signing = component.getUtility(IWebhookSigningSecret, name='_testing')
        assert_that(signing.secret, is_('whsec_9QeNmS4DII4h97fv'))
