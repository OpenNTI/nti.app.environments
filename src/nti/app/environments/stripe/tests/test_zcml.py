import unittest

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import starts_with

from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from nti.app.environments.tests import BaseConfiguringLayer

from ..interfaces import IStripeKey

class TestKeyRegistration(unittest.TestCase):

    layer = BaseConfiguringLayer

    def test_keys_for_dev(self):
        key = component.getUtility(IStripeKey)
        assert_that(key, verifiably_provides(IStripeKey))

        assert_that(key.publishable_key, is_('pk_test_gsyBVYVrN6NNdMDxj6rGX3hc'))
        assert_that(key.secret_key, starts_with('sk_test_0EQT0'))
